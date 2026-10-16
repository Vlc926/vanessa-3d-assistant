"""
AnimeTTS - High-performance Anime Voice Synthesizer for Vanessa.
Multi-tier Architecture:
- Tier 1: Kokoro-82M ONNX (Local, ultra-fast ~40ms, Spanish ef_dora + Japanese jf_alpha anime blend)
- Tier 2: Edge-TTS Anime Prosody (es-MX-DaliaNeural with +25Hz pitch, +8% rate)
- Tier 3: Hugging Face Inference API (facebook/mms-tts-spa)
- Independent digital gain volume control (PipeWire/paplay / ffplay / digital scaling)
"""
import os
import json
import re
import asyncio
import subprocess
import tempfile
import threading
from typing import Optional, Callable, Tuple, Dict, Any
from core.action_parser import parse_actions_and_clean_speech

try:
    import numpy as np
    import soundfile as sf
except ImportError:
    np = None
    sf = None

try:
    from kokoro_onnx import Kokoro
except ImportError:
    Kokoro = None

try:
    import edge_tts
except ImportError:
    edge_tts = None

try:
    from huggingface_hub import AsyncInferenceClient
except ImportError:
    AsyncInferenceClient = None


# Master Voice & Natural Anime Presets
MASTER_VOICE_ID = "es-MX-DaliaNeural"

EMOJI_PATTERN = re.compile(
    "["
    "\U00010000-\U0010FFFF"  # Supplementary Multilingual Plane (all emojis, symbols, pictographs)
    "\u2600-\u27BF"          # Misc symbols & dingbats (sparkles, hearts, etc.)
    "\u2300-\u23FF"          # Misc technical (stopwatch, etc.)
    "\u2B50-\u2B55"          # Stars, circles
    "\uFE00-\uFE0F"          # Variation selectors
    "\u200D"                 # Zero-width joiner
    "]+",
    flags=re.UNICODE
)

def strip_emojis(text: str) -> str:
    """Removes emoji glyphs and unicode symbols so TTS engines never speak them aloud."""
    if not text:
        return ""
    cleaned = EMOJI_PATTERN.sub(" ", text)
    return re.sub(r"\s+", " ", cleaned).strip()

ANIME_VOICE_PRESETS = {
    "dalia_anime": {
        "voice": "es-MX-DaliaNeural",
        "pitch_offset": 0,
        "rate_offset": 0,
        "label": "🌸 Vanessa Dalia (Dulce, Cálida y Ultra-Natural - Flagship)"
    },
    "paloma_anime": {
        "voice": "es-US-PalomaNeural",
        "pitch_offset": 0,
        "rate_offset": 0,
        "label": "✨ Paloma Anime (Alegre, Chispeante y Juvenil)"
    },
    "salome_anime": {
        "voice": "es-CO-SalomeNeural",
        "pitch_offset": 0,
        "rate_offset": 0,
        "label": "🎀 Salomé Maid (Suave, Atenta y Melódica)"
    },
    "elvira_anime": {
        "voice": "es-ES-ElviraNeural",
        "pitch_offset": 0,
        "rate_offset": 0,
        "label": "👑 Elvira Noble (Elegante, Serena y Expresiva)"
    },
    "catalina_anime": {
        "voice": "es-CL-CatalinaNeural",
        "pitch_offset": 0,
        "rate_offset": 0,
        "label": "💫 Catalina Dulce (Tierno Tono Anime Juvenil)"
    }
}


class AnimeTTS:
    def __init__(self, voice: str = MASTER_VOICE_ID, volume: int = 80, mode: str = "cloud"):
        if voice in ANIME_VOICE_PRESETS:
            self.voice = ANIME_VOICE_PRESETS[voice]["voice"]
        else:
            self.voice = voice if voice else MASTER_VOICE_ID
        self.volume = max(0, min(100, int(volume)))
        self.mode = mode  # "cloud" (preferred for ultra-natural neural audio), "local" fallback
        self.provider = "edge_tts"
        self.is_playing = False
        self.current_process: Optional[subprocess.Popen] = None
        
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.models_dir = os.path.join(self.base_dir, "models", "tts")
        self.settings_path = os.path.join(self.base_dir, "config", "settings.json")
        
        self.kokoro = None
        self.kokoro_voice_embed = None
        self._init_kokoro()

    def _init_kokoro(self):
        """Initializes Kokoro ONNX as offline fallback using clean single voice (no synthetic robotic blending)."""
        if not Kokoro or not np:
            return

        model_candidates = [
            os.path.join(self.models_dir, "kokoro-v1.0.onnx"),
            os.path.join(self.models_dir, "kokoro-v0_19.onnx"),
        ]
        voice_candidates = [
            os.path.join(self.models_dir, "voices-v1.0.bin"),
            os.path.join(self.models_dir, "voices.bin"),
        ]

        model_path = next((m for m in model_candidates if os.path.exists(m)), None)
        voices_path = next((v for v in voice_candidates if os.path.exists(v)), None)

        if model_path and voices_path:
            try:
                self.kokoro = Kokoro(model_path, voices_path)
                voices = self.kokoro.get_voices()

                # Clean single natural voice without multi-language blending to prevent metallic artifacts
                if "ef_dora" in voices:
                    self.kokoro_voice_embed = self.kokoro.get_voice_style("ef_dora")
                elif "af_bella" in voices:
                    self.kokoro_voice_embed = self.kokoro.get_voice_style("af_bella")
                elif len(voices) > 0:
                    self.kokoro_voice_embed = self.kokoro.get_voice_style(voices[0])

                print(f"[AnimeTTS] Kokoro-82M listo como respaldo offline ({model_path}).")
            except Exception as e:
                print(f"[AnimeTTS] Error inicializando Kokoro offline fallback: {e}")
                self.kokoro = None

    def _get_hf_token(self) -> str:
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    return settings.get("hf_token", "")
        except Exception:
            pass
        return os.environ.get("HF_TOKEN", "")

    def set_voice(self, voice: str):
        if voice in ANIME_VOICE_PRESETS:
            self.voice = ANIME_VOICE_PRESETS[voice]["voice"]
        elif voice:
            self.voice = voice
        self.provider = "edge_tts"

    def set_preset(self, preset_key: str):
        if preset_key in ANIME_VOICE_PRESETS:
            self.voice = ANIME_VOICE_PRESETS[preset_key]["voice"]
            self.provider = "edge_tts"
        elif preset_key == "kokoro_anime":
            self.provider = "kokoro"
        elif preset_key == "hf_anime":
            self.provider = "hf"
        elif preset_key:
            self.voice = preset_key
            self.provider = "edge_tts"

    def set_volume(self, volume: int):
        """Sets independent digital gain volume (0-100) without modifying master OS sink."""
        self.volume = max(0, min(100, int(volume)))

    @property
    def is_speaking(self) -> bool:
        if self.current_process:
            return self.current_process.poll() is None
        return self.is_playing

    def stop(self):
        """Immediately halts current audio playback."""
        if self.current_process and self.current_process.poll() is None:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=0.3)
            except Exception:
                try:
                    self.current_process.kill()
                except Exception:
                    pass
        self.is_playing = False
        self.current_process = None

    def get_adaptive_prosody(self, mood: Optional[str] = None, tone: Optional[str] = None) -> Tuple[str, str]:
        """Calculates natural, smooth human prosody without robotic pitch-shifting artifacts."""
        mood_str = (mood or "").lower()
        tone_str = (tone or "").lower()

        base_pitch = 0  # 0Hz preserves pure natural acoustic formants of human voice
        base_rate = 0   # 0% natural human speech speed

        pitch_delta = 0
        rate_delta = 0

        if "mischievous" in mood_str or "traviesa" in mood_str:
            rate_delta = +2
            pitch_delta = +2
        elif "happy" in mood_str or "happy" in tone_str:
            rate_delta = +1
            pitch_delta = +2
        elif "shh" in mood_str or "whisper" in mood_str or "quiet" in mood_str:
            rate_delta = -2
            pitch_delta = -1
        elif "caring" in mood_str:
            rate_delta = -1
            pitch_delta = +1
        elif "surprised" in mood_str:
            rate_delta = +3
            pitch_delta = +3
        elif "thinking" in mood_str:
            rate_delta = -2
            pitch_delta = 0

        total_pitch = base_pitch + pitch_delta
        total_rate = base_rate + rate_delta

        rate_sign = "+" if total_rate >= 0 else ""
        pitch_sign = "+" if total_pitch >= 0 else ""

        return f"{rate_sign}{total_rate}%", f"{pitch_sign}{total_pitch}Hz"

    async def speak(
        self,
        text: str,
        mood: Optional[str] = None,
        tone: Optional[str] = None,
        on_start: Optional[Callable[[], None]] = None,
        on_done: Optional[Callable[[], None]] = None
    ) -> str:
        """Synthesizes and plays audio with anime prosody through independent sound output."""
        return await self._speak_pipeline(text, mood=mood, tone=tone, on_start=on_start, on_done=on_done)

    async def speak_without_balloon(
        self,
        text: str,
        mood: Optional[str] = None,
        tone: Optional[str] = None
    ) -> str:
        """Speaks aloud WITHOUT showing any dialogue balloon (ambient conversational chatter)."""
        return await self._speak_pipeline(text, mood=mood, tone=tone)

    async def _speak_pipeline(
        self,
        text: str,
        mood: Optional[str] = None,
        tone: Optional[str] = None,
        on_start: Optional[Callable[[], None]] = None,
        on_done: Optional[Callable[[], None]] = None
    ) -> str:
        self.stop()
        self.is_playing = True

        audio_file = None
        # Clean asterisks, stage actions, and self-narrating action verbs
        clean_text, _, _ = parse_actions_and_clean_speech(text)
        # Strip all emojis so TTS never speaks names of icons
        clean_text = strip_emojis(clean_text)

        if not clean_text:
            self.is_playing = False
            if on_done:
                on_done()
            return ""

        # 1. Primary Master Voice: Edge-TTS Neural (es-MX-DaliaNeural) - 100% human, zero robotic distortion
        if edge_tts:
            try:
                audio_file = await self._generate_edge_tts(clean_text, mood, tone)
            except Exception as e:
                print(f"[AnimeTTS] Error en generación de voz principal Edge-TTS: {e}")
                audio_file = None

        # 2. Clean Offline Fallback: Kokoro-82M Local Single Voice
        if not audio_file and self.kokoro and self.kokoro_voice_embed is not None:
            try:
                audio_file = await asyncio.to_thread(self._generate_kokoro, clean_text, mood)
            except Exception as e:
                print(f"[AnimeTTS] Error en generación Kokoro fallback: {e}")
                audio_file = None

        # 3. Tertiary Fallback: Hugging Face API
        if not audio_file and AsyncInferenceClient and self._get_hf_token():
            try:
                audio_file = await self._generate_hf(clean_text)
            except Exception as e:
                print(f"[AnimeTTS] Error en generación HuggingFace API: {e}")
                audio_file = None


        if not audio_file:
            self.is_playing = False
            if on_done:
                on_done()
            return ""

        # Play audio asynchronously with independent digital volume and exact on_start trigger
        await asyncio.to_thread(self._play_audio, audio_file, on_start)

        self.is_playing = False
        if on_done:
            on_done()

        # Clean up temporary audio file
        try:
            if audio_file and os.path.exists(audio_file):
                os.remove(audio_file)
        except OSError:
            pass

        return audio_file

    def _generate_kokoro(self, text: str, mood: Optional[str] = None) -> str:
        speed = 1.05
        if mood and "mischievous" in mood.lower():
            speed = 1.12
        elif mood and "shh" in mood.lower():
            speed = 0.95

        samples, sample_rate = self.kokoro.create(
            text,
            voice=self.kokoro_voice_embed,
            speed=speed,
            lang="es"
        )
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_file.close()
        sf.write(temp_file.name, samples, sample_rate)
        return temp_file.name

    async def _generate_edge_tts(self, text: str, mood: Optional[str] = None, tone: Optional[str] = None) -> str:
        rate, pitch = self.get_adaptive_prosody(mood, tone)
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        temp_file.close()

        voice_name = MASTER_VOICE_ID
        if self.voice in ANIME_VOICE_PRESETS:
            voice_name = ANIME_VOICE_PRESETS[self.voice]["voice"]
        elif self.voice:
            voice_name = self.voice

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice_name,
            rate=rate,
            pitch=pitch
        )
        await communicate.save(temp_file.name)
        return temp_file.name

    async def _generate_hf(self, text: str) -> str:
        token = self._get_hf_token()
        client = AsyncInferenceClient(token=token)
        audio = await client.text_to_speech(text, model="facebook/mms-tts-spa")
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_file.write(audio)
        temp_file.close()
        return temp_file.name

    def _play_audio(self, filepath: str, on_playback_start: Optional[Callable[[], None]] = None):
        """Plays the audio using pipewire/paplay with independent volume, falling back to ffplay or mpv."""
        # PulseAudio volume range is 0 to 65536
        pa_volume = int((self.volume / 100.0) * 65536)

        def _notify_started():
            if on_playback_start:
                try:
                    on_playback_start()
                except Exception as ex:
                    print(f"[AnimeTTS] Error en on_playback_start: {ex}")

        # Try paplay (PipeWire/PulseAudio)
        try:
            self.current_process = subprocess.Popen(
                ["paplay", f"--volume={pa_volume}", filepath],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            _notify_started()
            self.current_process.wait()
            return
        except FileNotFoundError:
            pass

        # Try mpv with independent volume
        try:
            self.current_process = subprocess.Popen(
                ["mpv", "--no-video", "--really-quiet", f"--volume={self.volume}", filepath],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            _notify_started()
            self.current_process.wait()
            return
        except FileNotFoundError:
            pass

        # Fallback: ffplay
        try:
            self.current_process = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", "-volume", str(self.volume), filepath],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            _notify_started()
            self.current_process.wait()
        except FileNotFoundError:
            pass

    def speak_async(self, text: str, mood: str = "happy", on_start: Optional[Callable] = None, on_done: Optional[Callable] = None):
        """Asynchronously triggers voice synthesis in background thread."""
        threading.Thread(
            target=lambda: asyncio.run(self.speak(text, mood=mood, on_start=on_start, on_done=on_done)),
            daemon=True
        ).start()

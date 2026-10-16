import os
import json
import re
import asyncio
import subprocess
import tempfile
import threading
import urllib.request
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

ELEVENLABS_VOICE_ID = "n4GNpJP6Y2Nd09pDtetA"
MASTER_VOICE_ID = ELEVENLABS_VOICE_ID
FALLBACK_EDGE_VOICE = "es-MX-DaliaNeural"

EMOJI_PATTERN = re.compile(
    "["
    "\U00010000-\U0010FFFF"
    "\u2600-\u27BF"
    "\u2300-\u23FF"
    "\u2B50-\u2B55"
    "\uFE00-\uFE0F"
    "\u200D"
    "]+",
    flags=re.UNICODE
)

def strip_emojis(text: str) -> str:
    if not text:
        return ""
    cleaned = EMOJI_PATTERN.sub(" ", text)
    return re.sub(r"\s+", " ", cleaned).strip()

ANIME_VOICE_PRESETS = {
    "gaby_elevenlabs": {
        "voice": "n4GNpJP6Y2Nd09pDtetA",
        "pitch_offset": 38,
        "rate_offset": 3,
        "label": "💖 Gaby AI Conversational (ElevenLabs Oficial - Dulce y Juvenil)",
        "provider": "elevenlabs"
    },
    "dalia_anime": {
        "voice": "es-MX-DaliaNeural",
        "pitch_offset": 0,
        "rate_offset": 0,
        "label": "🌸 Vanessa Dalia (Dulce, Cálida y Ultra-Natural - Flagship)",
        "provider": "edge_tts"
    },
    "paloma_anime": {
        "voice": "es-US-PalomaNeural",
        "pitch_offset": 0,
        "rate_offset": 0,
        "label": "✨ Paloma Anime (Alegre, Chispeante y Juvenil)",
        "provider": "edge_tts"
    },
    "salome_anime": {
        "voice": "es-CO-SalomeNeural",
        "pitch_offset": 0,
        "rate_offset": 0,
        "label": "🎀 Salomé Maid (Suave, Atenta y Melódica)",
        "provider": "edge_tts"
    },
    "elvira_anime": {
        "voice": "es-ES-ElviraNeural",
        "pitch_offset": 0,
        "rate_offset": 0,
        "label": "👑 Elvira Noble (Elegante, Serena y Expresiva)",
        "provider": "edge_tts"
    },
    "catalina_anime": {
        "voice": "es-CL-CatalinaNeural",
        "pitch_offset": 0,
        "rate_offset": 0,
        "label": "💫 Catalina Dulce (Tierno Tono Anime Juvenil)",
        "provider": "edge_tts"
    }
}

class AnimeTTS:
    def __init__(self, voice: str = MASTER_VOICE_ID, volume: int = 80, mode: str = "cloud"):
        if voice in ANIME_VOICE_PRESETS:
            self.voice = ANIME_VOICE_PRESETS[voice]["voice"]
            self.provider = ANIME_VOICE_PRESETS[voice].get("provider", "elevenlabs")
        else:
            self.voice = voice if voice else MASTER_VOICE_ID
            self.provider = "elevenlabs" if self.voice == ELEVENLABS_VOICE_ID else "edge_tts"

        self.volume = max(0, min(100, int(volume)))
        self.mode = mode
        self.is_playing = False
        self.current_process: Optional[subprocess.Popen] = None
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.models_dir = os.path.join(self.base_dir, "models", "tts")
        self.settings_path = os.path.join(self.base_dir, "config", "settings.json")
        self.kokoro = None
        self.kokoro_voice_embed = None
        self._cached_eleven_token = None
        self._eleven_token_expiry = 0.0
        self._init_kokoro()

    def _init_kokoro(self):
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
                if "ef_dora" in voices:
                    self.kokoro_voice_embed = self.kokoro.get_voice_style("ef_dora")
                elif "af_bella" in voices:
                    self.kokoro_voice_embed = self.kokoro.get_voice_style("af_bella")
                elif len(voices) > 0:
                    self.kokoro_voice_embed = self.kokoro.get_voice_style(voices[0])
            except Exception:
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

    def _get_elevenlabs_token(self) -> str:
        env_key = os.environ.get("ELEVENLABS_API_KEY", "")
        if env_key:
            return env_key
        settings = {}
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    k = settings.get("elevenlabs_api_key", "")
                    if k:
                        return k
                    v_set = settings.get("voice_settings", {})
                    if isinstance(v_set, dict):
                        k = v_set.get("elevenlabs_api_key", "")
                        if k:
                            return k
        except Exception:
            pass

        import time
        now = time.time()
        if self._cached_eleven_token and now < self._eleven_token_expiry:
            return self._cached_eleven_token

        v_set = settings.get("voice_settings", {}) if isinstance(settings, dict) else {}
        r_token = ""
        if isinstance(v_set, dict):
            r_token = v_set.get("elevenlabs_refresh_token", "")
        if not r_token and isinstance(settings, dict):
            r_token = settings.get("elevenlabs_refresh_token", "")

        if not r_token:
            r_token = os.environ.get("ELEVENLABS_REFRESH_TOKEN", "")

        fb_key = v_set.get("elevenlabs_firebase_key", "") if isinstance(v_set, dict) else ""
        if not fb_key:
            fb_key = os.environ.get("ELEVENLABS_FIREBASE_KEY", "")

        if r_token and fb_key:
            try:
                import urllib.parse
                url = f"https://securetoken.googleapis.com/v1/token?key={fb_key}"
                data = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": r_token}).encode("utf-8")
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded", "Referer": "https://elevenlabs.io/", "Origin": "https://elevenlabs.io"})
                res = json.loads(urllib.request.urlopen(req, timeout=8).read().decode("utf-8"))
                tok = res.get("id_token")
                if tok:
                    self._cached_eleven_token = tok
                    self._eleven_token_expiry = now + 3000
                    return tok
            except Exception:
                pass
        return ""

    def set_voice(self, voice: str):
        if voice in ANIME_VOICE_PRESETS:
            self.voice = ANIME_VOICE_PRESETS[voice]["voice"]
            self.provider = ANIME_VOICE_PRESETS[voice].get("provider", "edge_tts")
        elif voice:
            self.voice = voice
            self.provider = "elevenlabs" if voice == ELEVENLABS_VOICE_ID else "edge_tts"

    def set_preset(self, preset_key: str):
        if preset_key in ANIME_VOICE_PRESETS:
            self.voice = ANIME_VOICE_PRESETS[preset_key]["voice"]
            self.provider = ANIME_VOICE_PRESETS[preset_key].get("provider", "edge_tts")
        elif preset_key == "kokoro_anime":
            self.provider = "kokoro"
        elif preset_key == "hf_anime":
            self.provider = "hf"
        elif preset_key:
            self.voice = preset_key
            self.provider = "elevenlabs" if preset_key == ELEVENLABS_VOICE_ID else "edge_tts"

    def set_volume(self, volume: int):
        self.volume = max(0, min(100, int(volume)))

    @property
    def is_speaking(self) -> bool:
        if self.current_process:
            return self.current_process.poll() is None
        return self.is_playing

    def stop(self):
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
        mood_str = (mood or "").lower()
        tone_str = (tone or "").lower()

        base_pitch = 0
        base_rate = 0
        is_gaby = (self.voice == ELEVENLABS_VOICE_ID or self.voice == "gaby_elevenlabs" or
                   (self.voice in ANIME_VOICE_PRESETS and ANIME_VOICE_PRESETS[self.voice].get("provider") == "elevenlabs"))
        if is_gaby:
            base_pitch = 38
            base_rate = 3
        elif self.voice in ANIME_VOICE_PRESETS:
            base_pitch = ANIME_VOICE_PRESETS[self.voice].get("pitch_offset", 0)
            base_rate = ANIME_VOICE_PRESETS[self.voice].get("rate_offset", 0)

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
        return await self._speak_pipeline(text, mood=mood, tone=tone, on_start=on_start, on_done=on_done)

    async def speak_without_balloon(
        self,
        text: str,
        mood: Optional[str] = None,
        tone: Optional[str] = None
    ) -> str:
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
        clean_text, _, _ = parse_actions_and_clean_speech(text)
        clean_text = strip_emojis(clean_text)

        if not clean_text:
            self.is_playing = False
            if on_done:
                on_done()
            return ""

        if self.provider == "elevenlabs" or self.voice == ELEVENLABS_VOICE_ID:
            eleven_token = self._get_elevenlabs_token()
            if eleven_token:
                try:
                    audio_file = await self._generate_elevenlabs(clean_text, mood, tone)
                except Exception:
                    audio_file = None

        if not audio_file and edge_tts:
            try:
                audio_file = await self._generate_edge_tts(clean_text, mood, tone)
            except Exception:
                audio_file = None

        if not audio_file and self.kokoro and self.kokoro_voice_embed is not None:
            try:
                audio_file = await asyncio.to_thread(self._generate_kokoro, clean_text, mood)
            except Exception:
                audio_file = None

        if not audio_file and AsyncInferenceClient and self._get_hf_token():
            try:
                audio_file = await self._generate_hf(clean_text)
            except Exception:
                audio_file = None

        if not audio_file:
            self.is_playing = False
            if on_done:
                on_done()
            return ""

        await asyncio.to_thread(self._play_audio, audio_file, on_start)

        self.is_playing = False
        if on_done:
            on_done()

        try:
            if audio_file and os.path.exists(audio_file):
                os.remove(audio_file)
        except OSError:
            pass

        return audio_file

    async def _generate_elevenlabs(self, text: str, mood: Optional[str] = None, tone: Optional[str] = None) -> Optional[str]:
        token = self._get_elevenlabs_token()
        if not token:
            return None

        voice_id = ELEVENLABS_VOICE_ID if (self.voice == ELEVENLABS_VOICE_ID or not self.voice) else self.voice
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

        stability = 0.45
        similarity_boost = 0.85
        style = 0.20

        if mood and "mischievous" in mood.lower():
            style = 0.35
            stability = 0.40
        elif mood and "caring" in mood.lower():
            stability = 0.55
            similarity_boost = 0.90

        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": style,
                "use_speaker_boost": True
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
            "User-Agent": "Mozilla/5.0"
        }
        if token.startswith("eyJ"):
            headers["Authorization"] = f"Bearer {token}"
            headers["Referer"] = "https://elevenlabs.io/"
            headers["Origin"] = "https://elevenlabs.io"
        else:
            headers["xi-api-key"] = token

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method="POST"
        )

        def _fetch():
            with urllib.request.urlopen(req, timeout=12) as response:
                if response.status == 200:
                    temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                    temp_file.write(response.read())
                    temp_file.close()
                    return temp_file.name
            return None

        return await asyncio.to_thread(_fetch)

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

        is_gaby = (self.voice == ELEVENLABS_VOICE_ID or self.voice == "gaby_elevenlabs" or
                   (self.voice in ANIME_VOICE_PRESETS and ANIME_VOICE_PRESETS[self.voice].get("provider") == "elevenlabs"))
        if is_gaby:
            voice_name = "es-UY-ValentinaNeural"
        elif self.voice in ANIME_VOICE_PRESETS and ANIME_VOICE_PRESETS[self.voice].get("provider") == "edge_tts":
            voice_name = ANIME_VOICE_PRESETS[self.voice]["voice"]
        elif self.voice and not self.voice.startswith("n4GNpJP"):
            voice_name = self.voice
        else:
            voice_name = FALLBACK_EDGE_VOICE

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
        pa_volume = int((self.volume / 100.0) * 65536)

        def _notify_started():
            if on_playback_start:
                try:
                    on_playback_start()
                except Exception:
                    pass

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

        try:
            self.current_process = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", "-volume", str(self.volume), filepath],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            _notify_started()
            self.current_process.wait()
            return
        except FileNotFoundError:
            pass

    def speak_async(self, text: str, mood: str = "happy", on_start: Optional[Callable] = None, on_done: Optional[Callable] = None):
        threading.Thread(
            target=lambda: asyncio.run(self.speak(text, mood=mood, on_start=on_start, on_done=on_done)),
            daemon=True
        ).start()

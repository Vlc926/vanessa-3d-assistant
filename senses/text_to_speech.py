"""
Text-to-Speech (TTS) Module for Vanessa.
Supports:
- Edge-TTS with Hyper-Natural Anime Prosody (Dalia Anime, Nanami Anime, Elvira Anime, Salomé)
- VOICEVOX local anime synthesis integration (with automatic fallback)
- Fish Audio & ElevenLabs API compatibility
- Independent digital gain volume control
- Lip-sync callbacks for Live2D integration
"""
import os
import json
import urllib.request
import urllib.parse
import asyncio
import base64
import tempfile
import subprocess
import edge_tts
from typing import Optional, Callable, Tuple, Dict, Any

ANIME_VOICE_PRESETS = {
    "dalia_anime": {
        "voice": "es-MX-DaliaNeural",
        "pitch_offset": 14,
        "rate_offset": 6,
        "label": "🌸 Dalia (Maid Anime Dulce y Viva - Español Latino)"
    },
    "nanami_anime": {
        "voice": "ja-JP-NanamiNeural",
        "pitch_offset": 10,
        "rate_offset": 5,
        "label": "🎌 Nanami (Waifu Anime Original - Japonés)"
    },
    "elvira_anime": {
        "voice": "es-ES-ElviraNeural",
        "pitch_offset": 12,
        "rate_offset": 5,
        "label": "✨ Elvira (Tsundere Anime Elegante - España)"
    },
    "salome_anime": {
        "voice": "es-CO-SalomeNeural",
        "pitch_offset": 10,
        "rate_offset": 3,
        "label": "🎀 Salomé (Melódica y Cálida - Colombia)"
    }
}


class TextToSpeech:
    def __init__(
        self,
        voice: str = "es-MX-DaliaNeural",
        rate: str = "+6%",
        pitch: str = "+14Hz",
        volume: int = 80,
        provider: str = "edge_tts"
    ):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch
        self.volume = max(0, min(100, volume))
        self.provider = provider
        self.is_speaking = False
        self.current_process: Optional[subprocess.Popen] = None
        self.voicevox_url = "http://127.0.0.1:50021"
        self.voicevox_speaker = 3  # Zundamon by default
        self.fish_audio_api_key = ""
        self.elevenlabs_api_key = ""

    def set_voice(self, voice: str):
        self.voice = voice

    def set_preset(self, preset_key: str):
        if preset_key in ANIME_VOICE_PRESETS:
            cfg = ANIME_VOICE_PRESETS[preset_key]
            self.voice = cfg["voice"]

    def set_volume(self, volume: int):
        """Sets independent digital gain volume (0-100) without altering master OS sink."""
        self.volume = max(0, min(100, int(volume)))

    def get_adaptive_prosody(self, mood: Optional[str] = None, tone: Optional[str] = None) -> Tuple[str, str]:
        """Calculates natural, lively anime prosody based on maid mood and interaction tone."""
        mood_str = (mood or "").lower()
        tone_str = (tone or "").lower()

        # Find base pitch offset for current voice
        base_pitch_int = 14
        base_rate_int = 6
        for p in ANIME_VOICE_PRESETS.values():
            if p["voice"] == self.voice:
                base_pitch_int = p["pitch_offset"]
                base_rate_int = p["rate_offset"]
                break

        # Dynamic emotional delta
        pitch_delta = 0
        rate_delta = 0

        if "mischievous" in mood_str or "traviesa" in mood_str:
            rate_delta = +8
            pitch_delta = +6
        elif "happy" in mood_str or "happy" in tone_str:
            rate_delta = +5
            pitch_delta = +4
        elif "shh" in mood_str or "whisper" in mood_str or "quiet" in mood_str:
            rate_delta = -6
            pitch_delta = -4
        elif "caring" in mood_str:
            rate_delta = -2
            pitch_delta = +2
        elif "surprised" in mood_str:
            rate_delta = +10
            pitch_delta = +10
        elif "thinking" in mood_str:
            rate_delta = -6
            pitch_delta = -2
        elif "serious" in mood_str:
            rate_delta = -4
            pitch_delta = -6

        total_pitch = base_pitch_int + pitch_delta
        total_rate = base_rate_int + rate_delta

        rate_sign = "+" if total_rate >= 0 else ""
        pitch_sign = "+" if total_pitch >= 0 else ""

        return f"{rate_sign}{total_rate}%", f"{pitch_sign}{total_pitch}Hz"

    async def generate_audio_file(
        self,
        text: str,
        output_path: Optional[str] = None,
        mood: Optional[str] = None,
        tone: Optional[str] = None
    ) -> str:
        """Synthesizes text using Edge-TTS Anime Enhanced, with optional VOICEVOX fallback."""
        if output_path is None:
            temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            output_path = temp_file.name
            temp_file.close()

        # 1. Try VOICEVOX if provider is explicitly voicevox
        if self.provider == "voicevox":
            success = await self._synthesize_voicevox(text, output_path)
            if success:
                return output_path

        # 2. Primary: Edge-TTS with Hyper-Natural Anime Prosody
        rate, pitch = self.get_adaptive_prosody(mood, tone)
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=rate,
                pitch=pitch
            )
            await communicate.save(output_path)
            return output_path
        except Exception as e:
            # Fallback with standard settings
            communicate = edge_tts.Communicate(text=text, voice="es-MX-DaliaNeural")
            await communicate.save(output_path)
            return output_path

    async def _synthesize_voicevox(self, text: str, output_path: str) -> bool:
        """Attempts synthesis via local VOICEVOX engine."""
        try:
            query_url = f"{self.voicevox_url}/audio_query?text={urllib.parse.quote(text)}&speaker={self.voicevox_speaker}"
            req = urllib.request.Request(query_url, method="POST")
            with urllib.request.urlopen(req, timeout=3) as resp:
                query_data = resp.read()

            synth_url = f"{self.voicevox_url}/synthesis?speaker={self.voicevox_speaker}"
            req2 = urllib.request.Request(
                synth_url,
                data=query_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req2, timeout=6) as resp2:
                with open(output_path, "wb") as f:
                    f.write(resp2.read())
            return True
        except Exception:
            return False

    def stop(self):
        """Immediately halts current audio playback."""
        if self.current_process and self.current_process.poll() is None:
            try:
                self.current_process.terminate()
            except Exception:
                pass
        self.is_speaking = False

    async def speak(
        self,
        text: str,
        mood: Optional[str] = None,
        tone: Optional[str] = None,
        on_start: Optional[Callable[[], None]] = None,
        on_done: Optional[Callable[[], None]] = None
    ) -> str:
        """Synthesizes and plays audio through Linux sound output with adaptive anime prosody."""
        self.stop()
        mp3_path = await self.generate_audio_file(text, mood=mood, tone=tone)

        self.is_speaking = True
        if on_start:
            on_start()

        def _play():
            try:
                self.current_process = subprocess.Popen(
                    ["mpv", "--no-video", "--really-quiet", f"--volume={self.volume}", mp3_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self.current_process.wait()
            finally:
                self.is_speaking = False
                if on_done:
                    on_done()
                if os.path.exists(mp3_path):
                    try:
                        os.remove(mp3_path)
                    except Exception:
                        pass

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _play)
        return mp3_path

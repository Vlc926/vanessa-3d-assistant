"""
Music Recognition Module using Shazamio.
Captures audio from microphone / system audio and identifies the track.
"""
import os
import asyncio
import tempfile
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as write_wav
from shazamio import Shazam
from typing import Dict, Any, Optional

class MusicDetector:
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.shazam = Shazam()

    def record_sample(self, duration_seconds: int = 5) -> str:
        """Records a short audio clip and saves it to a temporary WAV file."""
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_path = temp_file.name
        temp_file.close()

        recording = sd.rec(
            int(duration_seconds * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype='int16'
        )
        sd.wait()
        write_wav(temp_path, self.sample_rate, recording)
        return temp_path

    async def identify_music(self, duration_seconds: int = 5) -> Dict[str, Any]:
        """Listens to ambient audio and identifies the song."""
        wav_path = None
        try:
            # Record in thread pool so it doesn't block async loop
            loop = asyncio.get_event_loop()
            wav_path = await loop.run_in_executor(None, self.record_sample, duration_seconds)

            # Recognize with Shazam
            out = await self.shazam.recognize(wav_path)
            
            track = out.get("track")
            if not track:
                return {
                    "found": False,
                    "message": "No logré reconocer la música que suena. Intenta acercar la fuente de sonido."
                }

            title = track.get("title", "Desconocido")
            subtitle = track.get("subtitle", "Artista desconocido")
            genres = track.get("genres", {}).get("primary", "")
            images = track.get("images", {})
            cover_url = images.get("coverart") or images.get("background")

            return {
                "found": True,
                "title": title,
                "artist": subtitle,
                "genre": genres,
                "cover_url": cover_url,
                "message": f"¡Reconocí la canción! Es '{title}' de {subtitle}."
            }
        except Exception as e:
            return {
                "found": False,
                "error": str(e),
                "message": f"Ocurrió un error al intentar identificar la música: {str(e)}"
            }
        finally:
            if wav_path and os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                except Exception:
                    pass

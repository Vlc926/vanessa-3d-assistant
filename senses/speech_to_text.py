"""
Speech to Text (STT) Module using Faster-Whisper.
Lightweight CPU-quantized (int8) inference for offline transcription.
"""
import os
import time
import tempfile
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as write_wav
from faster_whisper import WhisperModel
from typing import Optional

class SpeechToText:
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "es"
    ):
        self.model_size = model_size
        self.language = language
        self.model: Optional[WhisperModel] = None
        self.device = device
        self.compute_type = compute_type
        self._load_model()

    def _load_model(self):
        try:
            print(f"[STT] Cargando modelo Whisper ({self.model_size}, {self.compute_type})...")
            try:
                self.model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type,
                    local_files_only=True
                )
            except Exception:
                self.model = WhisperModel(
                    self.model_size,
                    device=self.device,
                    compute_type=self.compute_type
                )
            print("[STT] Modelo Whisper cargado correctamente.")
        except Exception as e:
            print(f"[STT] Error cargando Faster-Whisper: {e}")

    def record_until_silence(
        self,
        sample_rate: int = 16000,
        max_duration: float = 10.0,
        silence_threshold: float = 500.0,
        silence_duration: float = 1.5
    ) -> np.ndarray:
        """
        Records from microphone until silence is sustained for silence_duration
        or max_duration is reached.
        """
        chunk_size = 1024
        audio_chunks = []
        silent_chunks = 0
        chunks_per_second = sample_rate / chunk_size
        silence_chunks_needed = int(silence_duration * chunks_per_second)
        max_chunks = int(max_duration * chunks_per_second)

        has_spoken = False

        with sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16') as stream:
            for _ in range(max_chunks):
                data, _ = stream.read(chunk_size)
                audio_chunks.append(data)
                
                # Check root-mean-square energy
                rms = np.sqrt(np.mean(data.astype(np.float32)**2))
                if rms > silence_threshold:
                    has_spoken = True
                    silent_chunks = 0
                else:
                    if has_spoken:
                        silent_chunks += 1
                        if silent_chunks >= silence_chunks_needed:
                            break

        if audio_chunks:
            return np.concatenate(audio_chunks, axis=0).flatten()
        return np.array([], dtype=np.int16)

    def transcribe_audio_array(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribes raw numpy int16 array using Faster-Whisper."""
        if len(audio_data) == 0:
            return ""

        try:
            if self.model is None:
                self._load_model()

            # Pass float32 normalized array directly to Faster-Whisper to bypass PyAV av.open bug
            if audio_data.dtype == np.int16:
                audio_float = audio_data.astype(np.float32) / 32768.0
            elif audio_data.dtype != np.float32:
                audio_float = audio_data.astype(np.float32)
            else:
                audio_float = audio_data.copy()

            # Normalize peak amplitude to 0.85 for optimal Whisper sensitivity
            peak = float(np.max(np.abs(audio_float)))
            if peak > 0.005:
                audio_float = (audio_float / peak) * 0.85

            segments, info = self.model.transcribe(
                audio_float,
                language=self.language,
                beam_size=1,
                temperature=0.0,
                without_timestamps=True,
                condition_on_previous_text=False,
                vad_filter=False,
                repetition_penalty=1.2,
                no_speech_threshold=0.6,
                compression_ratio_threshold=2.4,
                initial_prompt="Vanessa, Amo Víctor, asistente, por favor, claro, sí."
            )
            text = " ".join([segment.text for segment in segments]).strip()

            # Hallucination filter: detect and discard repetitive phrase loops (e.g. repeated 6+ times)
            words = text.lower().split()
            if len(words) >= 6 and (len(set(words)) / len(words)) < 0.4:
                print(f"[STT] Alucinación repetitiva descartada: {text[:60]}...")
                return ""

            return text
        except Exception as e:
            print(f"[STT] Error en transcripción: {e}")
            return ""

    def listen_and_transcribe(self) -> str:
        """Helper to record phrase and return text."""
        audio = self.record_until_silence()
        return self.transcribe_audio_array(audio)

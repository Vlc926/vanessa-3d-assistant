"""
Voice Biometrics & Emotion/Tone Detection Module for Vanessa.
Analyzes voice pitch, cadence, and energy to detect seriousness vs playfulness,
and checks speaker characteristics.
"""
import numpy as np
from typing import Dict, Any, Tuple

class VoiceAnalyzer:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate

    def analyze_tone_and_emotion(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """
        Analyzes audio array to determine user's tone:
        - 'serious': low pitch modulation, firm, steady cadence -> Vanessa responds formally and diligently.
        - 'playful': higher variation, casual energy -> Vanessa uses her playful, sarcastic maid persona.
        """
        audio_data = np.asarray(audio_data).flatten()
        if len(audio_data) < self.sample_rate * 0.4:
            return {"tone": "playful", "pitch_hz": 120.0, "energy": 0.05, "confidence": 0.5}

        # Convert to float32
        signal = audio_data.astype(np.float32)
        if np.max(np.abs(signal)) > 0:
            signal = signal / np.max(np.abs(signal))

        # 1. Energy (RMS)
        rms = float(np.sqrt(np.mean(signal**2)))

        # 2. Zero Crossing Rate (ZCR) - indicates fricatives / excitement
        zcr = float(np.mean(np.diff(np.sign(signal)) != 0))

        # 3. Fundamental frequency estimation via windowed FFT autocorrelation
        center = len(signal) // 2
        window_size = min(2048, len(signal))
        start_idx = max(0, center - (window_size // 2))
        frame = signal[start_idx:start_idx + window_size]

        pitch_hz = 120.0
        if len(frame) >= 512:
            n = len(frame)
            f = np.fft.rfft(frame, n=2*n)
            corr = np.fft.irfft(f * np.conj(f))[:n]
            min_lag = int(self.sample_rate / 350)
            max_lag = int(self.sample_rate / 70)
            if max_lag < len(corr):
                peak_lag = int(np.argmax(corr[min_lag:max_lag])) + min_lag
                if peak_lag > 0:
                    pitch_hz = float(self.sample_rate / peak_lag)

        # 4. Tone Classification Logic
        # A serious/authoritative voice typically exhibits lower pitch jitter, stable energy, and firmer delivery.
        # A playful voice has higher pitch variations or higher ZCR.
        is_serious = (pitch_hz < 135.0 and rms > 0.08 and zcr < 0.15)

        detected_tone = "serious" if is_serious else "playful"

        return {
            "tone": detected_tone,
            "pitch_hz": round(pitch_hz, 1),
            "energy": round(rms, 3),
            "zcr": round(zcr, 3)
        }

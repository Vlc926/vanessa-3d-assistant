"""
Continuous Wake Word & Biometric Voice Reactivity Engine for Vanessa.
Listens passively in background without keypress.
Triggers callback when:
1. "Vanessa", "Hola Vanessa" or "Hey Jarvis" is spoken.
2. The user's biometric voice matches the Amo Víctor dataset profile (Pitch F0 ~132Hz).
"""
import time
import threading
import numpy as np
import sounddevice as sd
from typing import Callable, Optional, List
import openwakeword
from openwakeword.model import Model

class WakeWordDetector:
    def __init__(
        self,
        wake_word: str = "hey_jarvis",
        threshold: float = 0.40,
        on_wake: Optional[Callable[[], None]] = None,
        voice_mgr = None,
        stt = None,
        on_voice_match: Optional[Callable[[str, float], None]] = None
    ):
        self.wake_word = wake_word
        self.threshold = threshold
        self.on_wake = on_wake
        self.voice_mgr = voice_mgr
        self.stt = stt
        self.on_voice_match = on_voice_match

        self.is_running = False
        self.is_active = True
        self.stream: Optional[sd.InputStream] = None
        self.thread: Optional[threading.Thread] = None

        # VAD & Utterance Collection Buffer
        self.speech_chunks: List[np.ndarray] = []
        self.is_speech_active = False
        self.silence_chunk_count = 0
        self.energy_threshold = 420.0
        self.last_trigger_time = 0.0

        all_models = openwakeword.get_pretrained_model_paths()
        target_path = [p for p in all_models if self.wake_word in p]
        if not target_path:
            target_path = [p for p in all_models if "jarvis" in p]

        self.model = Model(wakeword_model_paths=target_path)
        self.model_key = list(self.model.models.keys())[0] if self.model.models else "hey_jarvis_v0.1"

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()

    def pause(self):
        self.is_active = False
        self.speech_chunks.clear()

    def resume(self):
        self.speech_chunks.clear()
        self.is_active = True

    def stop(self):
        self.is_running = False
        self.is_active = False
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass

    def trigger_manual_wake(self):
        """Allows UI button or external script to wake Vanessa."""
        if self.on_wake and self.is_active:
            self.on_wake()

    def _process_utterance(self, audio_data: np.ndarray):
        """Asynchronously checks voice biometrics and keyword in speech utterance."""
        now = time.time()
        if now - self.last_trigger_time < 3.0:
            return

        # 1. Biometric check against trained Amo Víctor dataset
        if self.voice_mgr:
            try:
                is_master, sim, msg, feat = self.voice_mgr.verify_speaker(audio_data, name="Amo Víctor")
                if is_master and sim >= 45.0:
                    self.last_trigger_time = now
                    print(f"[WakeWord] 🎙️ ¡Voz del Amo Víctor confirmada biométricamente! ({sim}%, Pitch: {feat.get('pitch_hz')}Hz)")
                    if self.on_voice_match:
                        self.on_voice_match("Amo Víctor", sim)
                    if self.on_wake:
                        self.on_wake()
                    return
            except Exception as e:
                print(f"[WakeWord] Error en verificación biométrica: {e}")

        # 2. Keyword transcription check
        if self.stt:
            try:
                text = self.stt.transcribe_audio_array(audio_data).lower()
                keywords = ["vanessa", "banessa", "hola", "oye", "amo", "victor", "hey"]
                if any(kw in text for kw in keywords):
                    self.last_trigger_time = now
                    print(f"[WakeWord] 📢 Palabra de activación detectada: '{text}'")
                    if self.on_wake:
                        self.on_wake()
                    return
            except Exception as e:
                print(f"[WakeWord] Error en transcripción VAD: {e}")

    def _listen_loop(self):
        CHUNK = 1280
        SAMPLE_RATE = 16000

        def audio_callback(indata, frames, time_info, status):
            if not self.is_active:
                return

            audio_data = np.frombuffer(indata, dtype=np.int16)

            # 1. OpenWakeWord Model check (Hey Jarvis fallback)
            prediction = self.model.predict(audio_data)
            score = prediction.get(self.model_key, 0.0)
            if score >= self.threshold:
                self.model.reset()
                self.speech_chunks.clear()
                self.last_trigger_time = time.time()
                print("[WakeWord] Trigger por OpenWakeWord detectado.")
                if self.on_wake:
                    self.on_wake()
                return

            # 2. Voice Activity Detection & Biometric Accumulator
            raw_floats = audio_data.astype(np.float32)
            rms = float(np.sqrt(np.mean(raw_floats**2)))

            if rms > self.energy_threshold:
                self.is_speech_active = True
                self.silence_chunk_count = 0
                self.speech_chunks.append(audio_data.copy())
                # Cap max 3.5 seconds
                if len(self.speech_chunks) > int(3.5 * SAMPLE_RATE / CHUNK):
                    utterance = np.concatenate(self.speech_chunks)
                    self.speech_chunks.clear()
                    self.is_speech_active = False
                    threading.Thread(target=self._process_utterance, args=(utterance,), daemon=True).start()
            else:
                if self.is_speech_active:
                    self.silence_chunk_count += 1
                    self.speech_chunks.append(audio_data.copy())
                    # If 0.4s of silence elapsed after speaking
                    if self.silence_chunk_count >= 5:
                        self.is_speech_active = False
                        if len(self.speech_chunks) >= 8:  # At least 0.6s total
                            utterance = np.concatenate(self.speech_chunks)
                            self.speech_chunks.clear()
                            threading.Thread(target=self._process_utterance, args=(utterance,), daemon=True).start()
                        else:
                            self.speech_chunks.clear()

        while self.is_running:
            try:
                with sd.RawInputStream(
                    samplerate=SAMPLE_RATE,
                    blocksize=CHUNK,
                    channels=1,
                    dtype='int16',
                    callback=audio_callback
                ) as stream:
                    self.stream = stream
                    while self.is_running and self.is_active:
                        time.sleep(0.1)
            except Exception as e:
                print(f"[WakeWord] Stream reconectando: {e}")
                time.sleep(1.0)

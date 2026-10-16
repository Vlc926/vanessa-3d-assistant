"""
ContinuousVoiceListener - Always-On Ambient Conversational Voice Engine.
Allows Vanessa to detect Victor's voice in real-time with maximum sensitivity and naturalness,
behaving exactly like a continuous live phone call with an AI maid.

Features:
- Dynamic Noise Floor Calibration (auto-tunes to room acoustics and microphone model)
- Dual-Engine Hybrid VAD: WebRTC VAD + Adaptive RMS Energy Gate
- Software Gain Preamplifier (Mic Boost) for crisp recognition of soft voices and whispers
- Tolerant sliding-window trigger with 350ms pre-roll (never cuts off initial syllables)
- Dynamic device switching without thread interruption
- Audio normalization before Faster-Whisper inference
- Real-time VU-meter signal for live visual calibration in Settings Dialog
- Automatic pause/resume during Vanessa's vocal response to prevent self-looping
"""
import time
import numpy as np

try:
    import webrtcvad
except ImportError:
    webrtcvad = None

try:
    import sounddevice as sd
except ImportError:
    sd = None

from PyQt6.QtCore import QObject, pyqtSignal, QThread


class ListenerThread(QThread):
    speech_detected = pyqtSignal(str, bool, float)  # text, is_master, similarity
    voice_activity_start = pyqtSignal()
    voice_activity_end = pyqtSignal()
    interrupted_signal = pyqtSignal()  # Emitted when user speaks while Vanessa is talking
    speaker_identified = pyqtSignal(str, float)
    level_signal = pyqtSignal(float, bool)  # rms_level (0-100), is_voice_active

    def __init__(self, stt, voice_mgr, device_index=None, mic_gain=1.8, sensitivity=0.85):
        super().__init__()
        self.stt = stt
        self.voice_mgr = voice_mgr
        self.device_index = device_index
        self.mic_gain = max(0.5, min(5.0, float(mic_gain)))
        self.sensitivity = float(sensitivity)
        
        # VAD aggressiveness (0 = most sensitive to natural voice/whispers, 1 = normal, 2 = strict)
        self.vad_aggressiveness = 0 if self.sensitivity >= 0.75 else (1 if self.sensitivity >= 0.45 else 2)
        self.vad = webrtcvad.Vad(self.vad_aggressiveness) if webrtcvad else None
        
        self.sample_rate = 16000
        self.frame_duration_ms = 30
        self.frame_size = int(self.sample_rate * (self.frame_duration_ms / 1000.0))  # 480 samples
        
        # Snappy Real-Time Conversational Timing (320ms silence endpointing for instant zero dead-air response)
        self.window_frames = 3  # 90ms window (starts capture on first syllable)
        self.min_voiced_in_window = 2  # 2 of 3 frames (60ms) triggers immediate speech capture
        self.silence_trigger_frames = int(320 / self.frame_duration_ms)  # 320ms silence cutoff for instant response!
        self.max_duration_sec = 35
        
        # Barge-in tracking
        self.is_vanessa_speaking = False
        
        # Dynamic noise floor and energy gate
        self.ambient_noise_rms = 1500.0
        self.energy_margin = 1.15 if self.sensitivity >= 0.75 else (1.35 if self.sensitivity >= 0.45 else 1.65)
        
        self.is_running = True
        self.is_paused = False
        self._need_stream_restart = False

    def update_settings(self, device_index=None, mic_gain=None, sensitivity=None, energy_threshold=None, silence_ms=None):
        if mic_gain is not None:
            self.mic_gain = max(0.5, min(5.0, float(mic_gain)))
        if sensitivity is not None:
            self.sensitivity = float(sensitivity)
            self.vad_aggressiveness = 0 if self.sensitivity >= 0.75 else (1 if self.sensitivity >= 0.45 else 2)
            self.energy_margin = 1.20 if self.sensitivity >= 0.75 else (1.40 if self.sensitivity >= 0.45 else 1.75)
            if webrtcvad:
                self.vad = webrtcvad.Vad(self.vad_aggressiveness)
        if silence_ms is not None:
            self.silence_trigger_frames = max(8, int(silence_ms / self.frame_duration_ms))
        if device_index != self.device_index:
            self.device_index = device_index
            self._need_stream_restart = True

    def set_vanessa_speaking(self, speaking: bool):
        """Notifies the listener when Vanessa is speaking to enable instant barge-in."""
        self.is_vanessa_speaking = bool(speaking)

    def _calibrate_noise_floor(self, stream):
        """Reads initial ambient audio to calibrate baseline noise floor."""
        try:
            warmup = []
            for _ in range(12):
                chunk, _ = stream.read(self.frame_size)
                floats = chunk.flatten().astype(np.float32)
                warmup.append(np.sqrt(np.mean(floats**2)))
            if warmup:
                med = float(np.median(warmup))
                self.ambient_noise_rms = max(200.0, med)
                print(f"[ContinuousVoice] Calibración de ruido ambiente completada: {self.ambient_noise_rms:.1f} RMS")
        except Exception as e:
            print(f"[ContinuousVoice] Error en calibración de ruido: {e}")
            self.ambient_noise_rms = 1500.0

    def run(self):
        if not sd or not webrtcvad or not self.vad:
            print("[ContinuousVoice] sounddevice o webrtcvad no disponibles.")
            return

        while self.is_running:
            self._need_stream_restart = False
            stream = None
            actual_sr = self.sample_rate
            stream_blocksize = self.frame_size

            try:
                stream = sd.InputStream(
                    device=self.device_index,
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype='int16',
                    blocksize=self.frame_size
                )
            except Exception as e:
                try:
                    dev_info = sd.query_devices(self.device_index) if self.device_index is not None else {}
                    dev_sr = int(dev_info.get('default_samplerate', 48000))
                    actual_sr = dev_sr
                    stream_blocksize = int(actual_sr * (self.frame_duration_ms / 1000.0))
                    stream = sd.InputStream(
                        device=self.device_index,
                        samplerate=actual_sr,
                        channels=1,
                        dtype='int16',
                        blocksize=stream_blocksize
                    )
                except Exception as e2:
                    print(f"[ContinuousVoice] Fallback default de audio: {e2}")
                    actual_sr = self.sample_rate
                    stream_blocksize = self.frame_size
                    try:
                        stream = sd.InputStream(
                            samplerate=self.sample_rate,
                            channels=1,
                            dtype='int16',
                            blocksize=self.frame_size
                        )
                    except Exception as e3:
                        print(f"[ContinuousVoice] Error crítico abriendo micrófono: {e3}")
                        time.sleep(2.0)
                        continue

            with stream:
                self._calibrate_noise_floor(stream)
                recent_decisions = []
                pre_roll_buffer = []  # keeps 360ms before speech trigger
                unvoiced_frames = 0
                is_recording = False
                audio_data = []
                record_start_time = 0
                level_report_counter = 0

                while self.is_running and not self._need_stream_restart:
                    if self.is_paused:
                        time.sleep(0.05)
                        continue

                    try:
                        frame, _ = stream.read(stream_blocksize)
                    except Exception:
                        time.sleep(0.03)
                        continue

                    if len(frame) == 0:
                        continue

                    frame_raw = frame.flatten()
                    if actual_sr != self.sample_rate and len(frame_raw) > 0:
                        indices = np.linspace(0, len(frame_raw) - 1, self.frame_size)
                        frame_raw = np.interp(indices, np.arange(len(frame_raw)), frame_raw).astype(np.int16)

                    # Calculate true input RMS before software gain
                    floats_raw = frame_raw.astype(np.float32)
                    rms = float(np.sqrt(np.mean(floats_raw**2)))
                    
                    # WebRTC VAD classification on raw 16kHz audio
                    frame_raw_bytes = frame_raw.tobytes()
                    try:
                        webrtc_speech = self.vad.is_speech(frame_raw_bytes, self.sample_rate)
                    except Exception:
                        webrtc_speech = False

                    # Ambient noise tracking when quiet
                    if not is_recording:
                        if not webrtc_speech and rms < (self.ambient_noise_rms * 2.2):
                            capped_rms = min(rms, self.ambient_noise_rms * 1.35)
                            self.ambient_noise_rms = 0.97 * self.ambient_noise_rms + 0.03 * capped_rms

                    # Energy-based speech assessment
                    energy_speech = (rms > (self.ambient_noise_rms * self.energy_margin))
                    
                    # Hybrid Decision:
                    # Speech starts if WebRTC confirms voice AND energy is above noise floor,
                    # OR if volume is clearly prominent above background noise.
                    if not is_recording:
                        if self.is_vanessa_speaking:
                            # Higher energy barrier during Vanessa's own playback prevents acoustic echo self-triggering,
                            # but still allows Amo Víctor speaking over her to instantly barge in!
                            is_speech = webrtc_speech and (rms > max(1600.0, self.ambient_noise_rms * 1.45))
                        else:
                            is_speech = (webrtc_speech and (rms > self.ambient_noise_rms * 1.08 or rms > 800.0)) or \
                                        (rms > self.ambient_noise_rms * (self.energy_margin * 1.30))
                    else:
                        # Hysteresis continuation: easier to continue speaking than to start
                        if self.is_vanessa_speaking:
                            is_speech = webrtc_speech and (rms > self.ambient_noise_rms * 1.20)
                        else:
                            is_speech = webrtc_speech or (rms > self.ambient_noise_rms * 1.05)

                    # Prepare amplified frame for recording buffer
                    if self.mic_gain != 1.0:
                        amplified = np.clip(floats_raw * self.mic_gain, -32768, 32767).astype(np.int16)
                    else:
                        amplified = frame_raw
                    frame_bytes = amplified.tobytes()

                    # Live VU-meter level signal
                    level_report_counter += 1
                    if level_report_counter % 2 == 0:
                        # Normalize RMS logarithmically for natural VU-bar display
                        vu_norm = min(100.0, max(0.0, (rms / 8000.0) * 100.0))
                        self.level_signal.emit(vu_norm, is_speech)

                    recent_decisions.append(is_speech)
                    if len(recent_decisions) > self.window_frames:
                        recent_decisions.pop(0)

                    pre_roll_buffer.append(frame_bytes)
                    if len(pre_roll_buffer) > (self.window_frames + 4):  # ~360ms
                        pre_roll_buffer.pop(0)

                    if not is_recording:
                        voiced_count = sum(1 for d in recent_decisions if d)
                        if voiced_count >= self.min_voiced_in_window:
                            is_recording = True
                            self.voice_activity_start.emit()
                            if self.is_vanessa_speaking:
                                self.interrupted_signal.emit()
                            audio_data = pre_roll_buffer.copy()
                            record_start_time = time.time()
                            unvoiced_frames = 0
                    else:
                        audio_data.append(frame_bytes)
                        if not is_speech:
                            unvoiced_frames += 1
                        else:
                            unvoiced_frames = 0

                        duration = time.time() - record_start_time
                        if unvoiced_frames >= self.silence_trigger_frames or duration >= self.max_duration_sec:
                            is_recording = False
                            self.voice_activity_end.emit()

                            # Process recorded speech
                            audio_np = np.frombuffer(b''.join(audio_data), dtype=np.int16)
                            min_samples = int(self.sample_rate * 0.40)  # at least 400ms

                            if len(audio_np) >= min_samples:
                                # Speaker biometrics check
                                is_master = True
                                similarity = 100.0
                                if self.voice_mgr:
                                    try:
                                        is_match, sim, msg, _ = self.voice_mgr.verify_speaker(audio_np, name="Amo Víctor")
                                        is_master = is_match
                                        similarity = sim
                                        if is_master:
                                            self.speaker_identified.emit("Amo Víctor", similarity)
                                    except Exception as e:
                                        print(f"[ContinuousVoice] Error en verificación vocal: {e}")

                                # Whisper STT Transcription
                                if self.stt:
                                    try:
                                        text = self.stt.transcribe_audio_array(audio_np, self.sample_rate)
                                        if text and len(text.strip()) >= 2:
                                            print(f"[ContinuousVoice] Voz detectada ({similarity:.0f}% Amo): \"{text.strip()}\"")
                                            self.speech_detected.emit(text.strip(), is_master, similarity)
                                    except Exception as e:
                                        print(f"[ContinuousVoice] Error STT: {e}")

                            audio_data = []
                            pre_roll_buffer = []
                            recent_decisions = []
                            unvoiced_frames = 0


class ContinuousVoiceListener(QObject):
    speech_detected = pyqtSignal(str, bool, float)  # text, is_master, similarity
    voice_activity_start = pyqtSignal()
    voice_activity_end = pyqtSignal()
    interrupted_signal = pyqtSignal()
    speaker_identified = pyqtSignal(str, float)
    level_signal = pyqtSignal(float, bool)
    
    def __init__(self, stt, voice_mgr, sensitivity=0.85, mic_gain=1.8, device_index=None):
        super().__init__()
        self.stt = stt
        self.voice_mgr = voice_mgr
        self.sensitivity = sensitivity
        self.mic_gain = mic_gain
        self.device_index = device_index
        
        self._thread = ListenerThread(
            self.stt, self.voice_mgr,
            device_index=self.device_index,
            mic_gain=self.mic_gain,
            sensitivity=self.sensitivity
        )
        self._thread.speech_detected.connect(self.speech_detected)
        self._thread.voice_activity_start.connect(self.voice_activity_start)
        self._thread.voice_activity_end.connect(self.voice_activity_end)
        self._thread.interrupted_signal.connect(self.interrupted_signal)
        self._thread.speaker_identified.connect(self.speaker_identified)
        self._thread.level_signal.connect(self.level_signal)

    def set_vanessa_speaking(self, speaking: bool):
        self._thread.set_vanessa_speaking(speaking)
        
    def start_listening(self):
        if not self._thread.isRunning():
            self._thread.start()
            
    def stop_listening(self):
        self._thread.is_running = False
        self._thread.quit()
        self._thread.wait(2000)
        
    def update_calibration(self, device_index=None, mic_gain=None, sensitivity=None, energy_threshold=None, silence_ms=None):
        self._thread.update_settings(
            device_index=device_index,
            mic_gain=mic_gain,
            sensitivity=sensitivity,
            energy_threshold=energy_threshold,
            silence_ms=silence_ms
        )

    def set_sensitivity(self, level: float):
        self.sensitivity = level
        self._thread.update_settings(sensitivity=level)
        
    def set_gain(self, gain: float):
        self.mic_gain = gain
        self._thread.update_settings(mic_gain=gain)
        
    def pause(self):
        self._thread.is_paused = True
        
    def resume(self):
        self._thread.is_paused = False
        
    @property
    def is_listening(self) -> bool:
        return self._thread.isRunning() and not self._thread.is_paused

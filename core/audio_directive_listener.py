import os
import threading
import collections
from typing import Optional, Callable
import numpy as np
import sounddevice as sd
import onnxruntime as ort
import openwakeword
from openwakeword.model import Model

class AudioDirectiveListener:
    def __init__(
        self,
        on_wake: Optional[Callable[[], None]] = None,
        on_speech_active: Optional[Callable[[bool], None]] = None,
        sample_rate: int = 16000,
        vad_model_path: str = "models/vad/silero_vad.onnx",
        wake_threshold: float = 0.35,
        vad_threshold: float = 0.50
    ):
        self.sample_rate = sample_rate
        self.chunk_size = 512
        self.on_wake = on_wake
        self.on_speech_active = on_speech_active
        self.wake_threshold = wake_threshold
        self.vad_threshold = vad_threshold
        self.is_running = False
        self.is_muted = False

        self.buffer_len = int(sample_rate * 5.0)
        self.circular_buffer = collections.deque(maxlen=self.buffer_len)

        self.stream: Optional[sd.InputStream] = None
        self.thread: Optional[threading.Thread] = None

        self.vad_session = None
        if os.path.exists(vad_model_path):
            try:
                opts = ort.SessionOptions()
                opts.inter_op_num_threads = 1
                opts.intra_op_num_threads = 1
                self.vad_session = ort.InferenceSession(vad_model_path, sess_options=opts)
            except Exception:
                self.vad_session = None
        self.vad_state = np.zeros((2, 1, 128), dtype=np.float32)
        self.sr_tensor = np.array(self.sample_rate, dtype=np.int64)

        all_models = openwakeword.get_pretrained_model_paths()
        selected_models = []
        for kw in ["alexa", "jarvis", "mycroft"]:
            matched = [p for p in all_models if kw in p]
            selected_models.extend(matched)
        if not selected_models:
            selected_models = all_models[:2]

        self.oww_model = Model(wakeword_model_paths=selected_models)
        self.was_voice_active = False

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._audio_loop, daemon=True)
        self.thread.start()

    def set_muted(self, muted: bool):
        self.is_muted = bool(muted)

    def _audio_loop(self):
        def callback(indata, frames, time_info, status):
            if not self.is_running or self.is_muted:
                return
            pcm_data = indata[:, 0].copy()
            self.circular_buffer.extend(pcm_data.tolist())

            is_voice = False
            if self.vad_session:
                try:
                    tensor_chunk = np.expand_dims(pcm_data[:512], axis=0).astype(np.float32)
                    out, self.vad_state = self.vad_session.run(
                        None,
                        {'input': tensor_chunk, 'state': self.vad_state, 'sr': self.sr_tensor}
                    )
                    prob = float(out[0][0])
                    is_voice = prob >= self.vad_threshold
                except Exception:
                    is_voice = float(np.sqrt(np.mean(pcm_data**2))) > 0.02
            else:
                is_voice = float(np.sqrt(np.mean(pcm_data**2))) > 0.02

            if is_voice != self.was_voice_active:
                self.was_voice_active = is_voice
                if self.on_speech_active:
                    self.on_speech_active(is_voice)

            if is_voice:
                int16_samples = (pcm_data * 32767).astype(np.int16)
                preds = self.oww_model.predict(int16_samples)
                for model_name, score in preds.items():
                    if score >= self.wake_threshold:
                        if self.on_wake:
                            self.on_wake()
                        self.oww_model.reset()
                        break
            else:
                self.oww_model.reset()

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                blocksize=self.chunk_size,
                callback=callback
            ):
                while self.is_running:
                    sd.sleep(50)
        except Exception:
            pass

    def stop(self):
        self.is_running = False

"""
Background Voice Worker for Vanessa.
Manages continuous voice detection, speaker biometrics verification,
intent generation via AssistantBrain, speech sanitization, and frame-synced TTS playback.
"""
import threading
import asyncio
from typing import Optional
from PyQt6.QtCore import pyqtSignal, QObject

from core.brain import AssistantBrain
from senses.speech_to_text import SpeechToText
from core.anime_tts import AnimeTTS
from senses.voice_biometrics import VoiceAnalyzer
from core.voice_enrollment import VoiceEnrollmentManager
from core.continuous_voice import ContinuousVoiceListener
from core.action_parser import parse_actions_and_clean_speech


class BackgroundVoiceWorker(QObject):
    wake_signal = pyqtSignal()
    voice_match_signal = pyqtSignal(str, float)
    speech_start_signal = pyqtSignal(str)
    speech_done_signal = pyqtSignal()
    chat_message_signal = pyqtSignal(str, str)
    action_signal = pyqtSignal(dict)
    vrm_action_signal = pyqtSignal(str, str)  # (motion_name, expression_name)
    interrupted_signal = pyqtSignal()

    def __init__(
        self,
        brain: AssistantBrain,
        stt: SpeechToText,
        tts: AnimeTTS,
        voice_analyzer: VoiceAnalyzer,
        voice_mgr: VoiceEnrollmentManager
    ):
        super().__init__()
        self.brain = brain
        self.stt = stt
        self.tts = tts
        self.voice_analyzer = voice_analyzer
        self.voice_mgr = voice_mgr
        self.listener: Optional[ContinuousVoiceListener] = None
        self.interaction_id = 0

    def start_listening(self):
        """Starts continuous always-on voice activity detection (like a live call)."""
        calib = self.brain.personality.get("audio_calibration", {})
        gain = float(calib.get("mic_gain", 1.8))
        sens = float(calib.get("vad_sensitivity", 0.85))
        dev_idx = calib.get("device_index", None)
        self.listener = ContinuousVoiceListener(
            self.stt, self.voice_mgr, sensitivity=sens, mic_gain=gain, device_index=dev_idx
        )
        self.listener.voice_activity_start.connect(self.wake_signal.emit)
        self.listener.speaker_identified.connect(self.voice_match_signal.emit)
        self.listener.speech_detected.connect(self.on_continuous_speech)
        self.listener.interrupted_signal.connect(self.on_user_interrupt)
        self.listener.start_listening()

    def on_user_interrupt(self):
        """Called immediately when user speaks while Vanessa is talking."""
        print("[VoiceWorker] ¡Amo Víctor interrumpió mid-speech! Frenando audio y cambiando a pose de alerta.")
        self.interaction_id += 1
        if self.tts:
            self.tts.stop()
        if self.listener:
            self.listener.set_vanessa_speaking(False)
        self.speech_done_signal.emit()
        self.vrm_action_signal.emit("listen", "surprised")
        self.interrupted_signal.emit()

    def on_continuous_speech(self, user_text: str, is_master: bool, sim: float):
        if not user_text or len(user_text.strip()) < 2:
            return

        # Echo Cancellation: discard self-generated audio when Vanessa is actively speaking
        if self.tts and getattr(self.tts, "is_playing", False):
            print(f"[VoiceGating] 🔇 Audio ignorado por eco de reproducción propia TTS: \"{user_text}\"")
            return

        lower_text = user_text.lower()
        has_wake = any(w in lower_text for w in ["vanessa", "banessa", "vanesa", "banesa", "oye", "hola"])
        min_threshold = 42.0 if has_wake else 48.0

        # Calibrated Amo Víctor Voice Verification:
        is_amo = (is_master or has_wake) and (sim >= min_threshold)
        if not is_amo:
            print(f"[VoiceGating] 🔒 Voz no autorizada descartada ({sim:.1f}% coincidencia < {min_threshold}% Amo Víctor): \"{user_text}\"")
            return

        # Immediate visual feedback (<10ms): Vanessa tilts head and looks attentive
        self.vrm_action_signal.emit("look_around", "neutral")

        threading.Thread(
            target=self._process_speech_interaction,
            args=(user_text, is_master, sim),
            daemon=True
        ).start()

    def _process_speech_interaction(self, user_text: str, is_master: bool, sim: float):
        self.interaction_id += 1
        current_id = self.interaction_id

        try:
            # If Vanessa was speaking, ensure prior audio is halted immediately
            if self.tts:
                self.tts.stop()

            speaker_tag = f"Amo Víctor ({sim:.0f}%)"
            self.chat_message_signal.emit(speaker_tag, user_text)
            self.voice_match_signal.emit("Amo Víctor", sim)

            detected_tone = "playful"
            env_snap = self.brain.get_environmental_snapshot() if hasattr(self.brain, "get_environmental_snapshot") else {}
            win_title = env_snap.get("active_window", {}).get("title", "")
            media_st = env_snap.get("media_status", "")
            vis_ctx = f"Amo Víctor interactuando en llamada continua. Ventana actual en pantalla: '{win_title}'. Multimedia: {media_st}." if win_title else "Amo Víctor interactuando en llamada continua con Vanessa."

            reply, mood, extra = asyncio.run(
                self.brain.generate_response(
                    user_text,
                    visual_context=vis_ctx,
                    detected_tone=detected_tone,
                    recognized_user="Amo Víctor" if is_master else "Usuario"
                )
            )

            # If user spoke again while generating response, discard stale generation
            if current_id != self.interaction_id:
                return

            # 1. Parse physical actions and clean dialogue of all asterisks and stage directions
            clean_reply, motion, expression = parse_actions_and_clean_speech(reply)
            backend_tag = extra.get("backend", "local") if isinstance(extra, dict) else "local"

            # Trigger action on GUI thread if requested (OS actions like open app, volume, etc.)
            if extra and isinstance(extra, dict) and "action" in extra:
                self.action_signal.emit(extra)

            # If response had only a physical action without spoken dialogue, execute it in complete silence!
            if not clean_reply:
                if motion or expression:
                    self.vrm_action_signal.emit(motion or "", expression or "")
                return

            # Callbacks for 100% exact frame-level audio synchronization:
            def on_playback_start():
                if current_id != self.interaction_id:
                    if self.tts:
                        self.tts.stop()
                    return
                if self.listener:
                    self.listener.set_vanessa_speaking(True)
                # Speech started playing sound right NOW -> pop balloon, start lip sync and motions!
                self.chat_message_signal.emit(f"Vanessa [{backend_tag}]", clean_reply)
                # Emit custom physical gesture & anime expression FIRST so flags are set
                if motion or expression:
                    self.vrm_action_signal.emit(motion or "", expression or "")
                self.speech_start_signal.emit(mood)

            def on_playback_done():
                if self.listener:
                    self.listener.set_vanessa_speaking(False)
                # Speech ended -> stop lip sync and return to natural relaxed posture
                self.speech_done_signal.emit()

            # Adaptive Speech Prosody with Kokoro Anime / Edge TTS:
            # Balloon, mouth movement, and audio play at the EXACT same millisecond!
            asyncio.run(
                self.tts.speak(
                    clean_reply,
                    mood=mood,
                    tone=detected_tone,
                    on_start=on_playback_start,
                    on_done=on_playback_done
                )
            )

        except Exception as e:
            print(f"[Worker] Error en llamada continua de voz: {e}")
            self.speech_done_signal.emit()
        finally:
            if self.listener:
                self.listener.set_vanessa_speaking(False)

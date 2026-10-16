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
from core.avatar_directive_server import AvatarDirectiveServer


class BackgroundVoiceWorker(QObject):
    wake_signal = pyqtSignal()
    voice_match_signal = pyqtSignal(str, float)
    speech_start_signal = pyqtSignal(str)
    speech_done_signal = pyqtSignal()
    chat_message_signal = pyqtSignal(str, str)
    action_signal = pyqtSignal(dict)
    vrm_action_signal = pyqtSignal(str, str)
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
        print("[VoiceWorker] ¡Amo Víctor interrumpió mid-speech! Frenando audio y cambiando a pose de alerta.")
        self.interaction_id += 1
        AvatarDirectiveServer.get_instance().set_state("LISTENING")
        if self.tts:
            self.tts.stop()
        if self.listener:
            self.listener.set_vanessa_speaking(False)
        self.speech_done_signal.emit()
        self.vrm_action_signal.emit("listen_attentive", "surprised")
        self.interrupted_signal.emit()

    def on_continuous_speech(self, user_text: str, is_master: bool, sim: float):
        if not user_text or len(user_text.strip()) < 2:
            return

        if self.tts and getattr(self.tts, "is_playing", False):
            print(f"[VoiceGating] 🔇 Audio ignorado por eco de reproducción propia TTS: \"{user_text}\"")
            return

        lower_text = user_text.lower().strip()
        wake_patterns = ["vanessa", "banessa", "vanesa", "banesa", "oye vanessa", "oye banessa", "oye vanesa", "oye banesa"]
        has_wake = any(w in lower_text for w in wake_patterns)
        min_threshold = 42.0 if has_wake else 48.0

        is_amo = has_wake and (is_master or sim >= min_threshold)
        if not is_amo:
            print(f"[VoiceGating] 🔒 Voz no autorizada o sin palabra clave 'Vanessa' / 'Oye Vanessa': \"{user_text}\"")
            return

        AvatarDirectiveServer.get_instance().set_state("LISTENING")

        is_question = any(q in lower_text for q in ["¿", "?", "qué", "que", "cómo", "como", "cuál", "cual", "por qué", "porque", "dónde", "donde", "quién", "quien", "cuándo", "cuando", "puedes", "podrías"])
        is_cheerful = any(c in lower_text for c in ["¡", "!", "jaja", "jeje", "gracias", "genial", "excelente", "bien", "hola", "saludos"])
        is_serious = any(s in lower_text for s in ["silencio", "detén", "para", "apaga", "ejecuta", "cierra", "alerta", "urgente", "rápido"])

        if is_question:
            detected_tone = "inquisitive"
            immediate_gesture = "question"
            immediate_expr = "thinking"
        elif is_cheerful:
            detected_tone = "playful"
            immediate_gesture = "wave"
            immediate_expr = "happy"
        elif is_serious:
            detected_tone = "serious"
            immediate_gesture = "listen_attentive"
            immediate_expr = "neutral"
        else:
            detected_tone = "playful"
            immediate_gesture = "curiosity"
            immediate_expr = "curious"

        self.vrm_action_signal.emit(immediate_gesture, immediate_expr)

        threading.Thread(
            target=self._process_speech_interaction,
            args=(user_text, is_master, sim, detected_tone, is_question),
            daemon=True
        ).start()

    def _process_speech_interaction(self, user_text: str, is_master: bool, sim: float, detected_tone: str, is_question: bool):
        self.interaction_id += 1
        current_id = self.interaction_id

        try:
            if self.tts:
                self.tts.stop()

            speaker_tag = f"Amo Víctor ({sim:.0f}%)"
            self.chat_message_signal.emit(speaker_tag, user_text)
            self.voice_match_signal.emit("Amo Víctor", sim)

            env_snap = self.brain.get_environmental_snapshot() if hasattr(self.brain, "get_environmental_snapshot") else {}
            win_title = env_snap.get("active_window", {}).get("title", "")
            media_st = env_snap.get("media_status", "")
            vis_ctx = f"Amo Víctor interactuando en llamada continua. Ventana actual en pantalla: '{win_title}'. Multimedia: {media_st}." if win_title else "Amo Víctor interactuando en llamada continua con Vanessa."

            AvatarDirectiveServer.get_instance().set_state("THINKING")
            reply, mood, extra = asyncio.run(
                self.brain.generate_response(
                    user_text,
                    visual_context=vis_ctx,
                    detected_tone=detected_tone,
                    recognized_user="Amo Víctor" if is_master else "Usuario"
                )
            )

            if current_id != self.interaction_id:
                return

            clean_reply, motion, expression = parse_actions_and_clean_speech(reply)
            backend_tag = extra.get("backend", "local") if isinstance(extra, dict) else "local"

            if extra and isinstance(extra, dict) and "action" in extra:
                self.action_signal.emit(extra)

            if not clean_reply:
                if motion or expression:
                    self.vrm_action_signal.emit(motion or "curiosity", expression or "curious")
                return

            if not motion:
                lower_reply = clean_reply.lower()
                if any(k in lower_reply for k in ["aquí tienes", "en pantalla", "encontré", "mira esto", "te muestro"]):
                    motion = "pointing"
                elif any(k in lower_reply for k in ["por supuesto", "entendido", "a la orden", "claro", "sí, amo"]):
                    motion = "salute" if detected_tone == "serious" else "nod"
                elif any(k in lower_reply for k in ["¡genial!", "¡excelente!", "¡listo!", "¡completado!"]):
                    motion = "cheer"
                elif any(k in lower_reply for k in ["déjame ver", "revisando", "analizando", "me pregunto"]):
                    motion = "question"
                elif any(k in lower_reply for k in ["con gusto", "a su servicio", "siempre"]):
                    motion = "bow_polite"
                else:
                    motion = "nod" if is_question else "characteristic"

            if not expression:
                expression = "happy" if detected_tone == "playful" else ("neutral" if detected_tone == "serious" else "thinking")

            def on_playback_start():
                if current_id != self.interaction_id:
                    if self.tts:
                        self.tts.stop()
                    return
                if self.listener:
                    self.listener.set_vanessa_speaking(True)
                joy_val = 0.85 if detected_tone == "playful" else (0.15 if detected_tone == "serious" else 0.45)
                curiosity_val = 0.80 if is_question else (0.40 if detected_tone == "inquisitive" else 0.15)
                surprise_val = 0.70 if expression == "surprised" else (0.25 if is_question else 0.05)
                tension_val = 0.60 if detected_tone == "serious" else 0.0
                confidence_val = 0.85 if detected_tone == "serious" else 0.75
                shyness_val = 0.65 if expression == "shy" else 0.10
                emotion_vec = {
                    "joy": round(joy_val, 2),
                    "curiosity": round(curiosity_val, 2),
                    "surprise": round(surprise_val, 2),
                    "tension": round(tension_val, 2),
                    "confidence": round(confidence_val, 2),
                    "shyness": round(shyness_val, 2)
                }
                AvatarDirectiveServer.get_instance().emit_directive(
                    state="SPEAKING",
                    emotion_vector=emotion_vec,
                    body_gesture=motion or "nod",
                    look_target="user_camera",
                    dialogue_text=clean_reply
                )
                self.chat_message_signal.emit(f"Vanessa [{backend_tag}]", clean_reply)
                self.vrm_action_signal.emit(motion or "nod", expression or "happy")
                self.speech_start_signal.emit(mood)

            def on_playback_done():
                if self.listener:
                    self.listener.set_vanessa_speaking(False)
                AvatarDirectiveServer.get_instance().set_state("IDLE")
                self.speech_done_signal.emit()

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

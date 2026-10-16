import time
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

class ProtectionProtocolManager(QObject):
    activated_signal = pyqtSignal(str)
    deactivated_signal = pyqtSignal(str)
    tick_signal = pyqtSignal(int, str)
    status_changed_signal = pyqtSignal(bool)

    def __init__(self, overlay=None, parent=None):
        super().__init__(parent)
        self.overlay = overlay
        self.is_active = False
        self.total_duration_seconds = 300
        self.remaining_seconds = 0
        self.cooldown_duration = 120
        self.cooldown_remaining = 0
        self.activation_count = 0
        self.active_reason = ""

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._on_tick)

        self.cooldown_timer = QTimer(self)
        self.cooldown_timer.setInterval(1000)
        self.cooldown_timer.timeout.connect(self._on_cooldown_tick)

    def formatted_remaining_time(self) -> str:
        mins = max(0, self.remaining_seconds) // 60
        secs = max(0, self.remaining_seconds) % 60
        return f"{mins:02d}:{secs:02d}"

    def can_activate(self) -> tuple[bool, str]:
        if self.is_active:
            return False, f"El protocolo ya está activo ({self.formatted_remaining_time()} restante)."
        if self.cooldown_remaining > 0:
            return False, f"Vanessa está recuperando su estabilidad mental. Enfriamiento: {self.cooldown_remaining}s."
        return True, "Listo para activar."

    def activate_protocol_demo(self, reason: str = "manual") -> tuple[bool, str]:
        can_run, msg = self.can_activate()
        if not can_run:
            if self.overlay and hasattr(self.overlay, "show_balloon"):
                self.overlay.show_balloon(f"⚠️ {msg}", duration_ms=3500)
            return False, msg

        self.is_active = True
        self.remaining_seconds = self.total_duration_seconds
        self.active_reason = reason
        self.activation_count += 1

        self.timer.start()
        self.status_changed_signal.emit(True)
        self.activated_signal.emit(reason)

        if self.overlay:
            ov = self.overlay
            if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget") and ov.vrm_widget:
                try:
                    if hasattr(ov.vrm_widget, "set_expression"):
                        ov.vrm_widget.set_expression("serious", 0.95)
                    if hasattr(ov.vrm_widget, "send_motor_intent"):
                        ov.vrm_widget.send_motor_intent("inspect", 0.0, 0.0, 1.2, "serious", "guard")
                    elif hasattr(ov.vrm_widget, "play_gesture"):
                        ov.vrm_widget.play_gesture("cheer_fist")
                except Exception:
                    pass

            dialogue = (
                "🛡️ [PROTOCOLO DE PROTECCIÓN: DEMO 5 MIN ACTIVADO]\n"
                "Núcleo cognitivo en sobremarcha táctica para proteger su entorno digital.\n"
                "Amo Víctor, sus procesos y seguridad están bajo mi resguardo."
            )
            if hasattr(ov, "show_balloon"):
                ov.show_balloon(dialogue, duration_ms=5500)
            if hasattr(ov, "tts") and ov.tts and hasattr(ov.tts, "speak_async") and getattr(ov, "ambient_voice_only", False):
                try:
                    ov.tts.speak_async("Protocolo de protección activado en modo demo de cinco minutos. Estoy a su lado, Amo Víctor.")
                except Exception:
                    pass

        return True, "Protocolo de protección demo (5 min) activado exitosamente."

    def deactivate_protocol(self, completed_naturally: bool = False) -> tuple[bool, str]:
        if not self.is_active:
            return False, "El protocolo no se encuentra activo."

        self.timer.stop()
        self.is_active = False
        self.remaining_seconds = 0
        self.cooldown_remaining = self.cooldown_duration
        self.cooldown_timer.start()

        self.status_changed_signal.emit(False)
        reason_text = "completado_5min" if completed_naturally else "cancelado_usuario"
        self.deactivated_signal.emit(reason_text)

        if self.overlay:
            ov = self.overlay
            if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget") and ov.vrm_widget:
                try:
                    if hasattr(ov.vrm_widget, "set_expression"):
                        ov.vrm_widget.set_expression("happy", 0.8)
                    if hasattr(ov.vrm_widget, "send_motor_intent"):
                        ov.vrm_widget.send_motor_intent("idle", 0.0, 0.0, 1.0, "gentle", "standby")
                    elif hasattr(ov.vrm_widget, "play_gesture"):
                        ov.vrm_widget.play_gesture("relax")
                except Exception:
                    pass

            if completed_naturally:
                conclusion_msg = (
                    "🛡️ [PROTOCOLO DE PROTECCIÓN CONCLUIDO CON ÉXITO]\n"
                    "Desactivando sobremarcha para descansar el núcleo mental de Vanessa.\n"
                    "Su entorno está a salvo. Gracias por confiar en mí, Amo Víctor 🌸"
                )
            else:
                conclusion_msg = (
                    "🛡️ [PROTOCOLO DE PROTECCIÓN DESACTIVADO]\n"
                    "Regresando al modo de asistencia estándar para mantener un equilibrio sereno."
                )

            if hasattr(ov, "show_balloon"):
                ov.show_balloon(conclusion_msg, duration_ms=5000)

        return True, "Protocolo desactivado con éxito."

    def _on_tick(self):
        if not self.is_active:
            return

        self.remaining_seconds -= 1
        time_str = self.formatted_remaining_time()
        self.tick_signal.emit(self.remaining_seconds, time_str)

        if self.remaining_seconds <= 0:
            self.deactivate_protocol(completed_naturally=True)

    def _on_cooldown_tick(self):
        if self.cooldown_remaining > 0:
            self.cooldown_remaining -= 1
        else:
            self.cooldown_timer.stop()

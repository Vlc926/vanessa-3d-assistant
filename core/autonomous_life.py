import time
import random
from typing import Optional, Dict, Any, List
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

class AutonomousCoexistenceEngine(QObject):
    snack_triggered_signal = pyqtSignal(str, str)
    pomodoro_status_signal = pyqtSignal(str, int)
    dance_started_signal = pyqtSignal(str)

    SNACK_CATALOG = [
        {
            "name": "Té Verde Matcha Artesanal",
            "emoji": "🍵",
            "pose": "relax",
            "expression": "happy",
            "phrase": "Bebe un sorbo pausado de té verde matcha humeante mientras observa atentamente su terminal... ¡paz y concentración perfecta, Amo Víctor! ✨"
        },
        {
            "name": "Tazón de Ramen Tonkotsu Humeante",
            "emoji": "🍜",
            "pose": "sit_casual",
            "expression": "happy",
            "phrase": "Disfruta un delicioso tazón de ramen con fideos al dente sin hacer ruido entre líneas de código... ¡delicioso y reconfortante! 🌸"
        },
        {
            "name": "Café Latte con Arte de Gatito",
            "emoji": "☕",
            "pose": "peace",
            "expression": "smile",
            "phrase": "Sopla suavemente la espumita de su café latte con una sonrisa dulce mientras revisa los procesos del sistema... 💖"
        },
        {
            "name": "Dorayaki Esponjoso de Anko",
            "emoji": "🥞",
            "pose": "heart_hands",
            "expression": "happy",
            "phrase": "Da un bocado a un dorayaki esponjoso recién horneado... ¡un dulce respiro para continuar asistiéndole al cien por ciento! 🎀"
        },
        {
            "name": "Boba Tea de Taro con Perlitas",
            "emoji": "🧋",
            "pose": "cat_pose",
            "expression": "happy",
            "phrase": "Agita su té de boba lila y mastica una perlita con deleite... ¡el combustible más tierno para el escritorio digital! ✨"
        },
        {
            "name": "Taiyaki Crujiente de Chocolate",
            "emoji": "🐟",
            "pose": "happy_gesture",
            "expression": "smile",
            "phrase": "Muerde la colita crujiente de un taiyaki de chocolate caliente... ¡dulzura instantánea para acompañar su jornada, Amo! 🍫"
        },
        {
            "name": "Pocky de Fresa",
            "emoji": "🍓",
            "pose": "thinking",
            "expression": "relaxed",
            "phrase": "Sostiene un palito de pocky crujiente entre los labios mientras analiza con curiosidad el código que usted escribe... 🍓"
        },
        {
            "name": "Onigiri de Salmón con Nori",
            "emoji": "🍙",
            "pose": "sit_elegant",
            "expression": "happy",
            "phrase": "Come un onigiri casero de salmón envuelto en alga crujiente para reponer energía a su lado... 🍙"
        },
        {
            "name": "Rebanada de Pizza Gamer Cuatro Quesos",
            "emoji": "🍕",
            "pose": "cheer_fist",
            "expression": "happy",
            "phrase": "Da un mordisco a una rebanada de pizza con queso estirado cuidando no manchar el teclado virtual... ¡combustible gamer oficial! 🍕"
        },
        {
            "name": "Soda Japonesa de Melón con Helado Flotante",
            "emoji": "🍈",
            "pose": "peace",
            "expression": "smile",
            "phrase": "Sorbe con pajita una burbujeante soda de melón con helado de vainilla... ¡qué frescura tan revitalizante! 🥤"
        },
        {
            "name": "Brocheta de Hanami Dango Tricolor",
            "emoji": "🍡",
            "pose": "bow",
            "expression": "happy",
            "phrase": "Degusta una brocheta de dango tricolor tradicional con toda la delicadeza de una maid dedicada... 🍡🌸"
        }
    ]

    DANCE_ROUTINES = [
        ("dance_reze", "Coreografía Dinámica Reze Dance"),
        ("dance_hiphop", "Baile Urbano Hip-Hop Anime"),
        ("dance_macarena", "Coreografía Macarena Clásica"),
        ("spin", "Giro Grácil y Pirueta Maid"),
        ("wave_both", "Saludo Rítmico con Ambas Manos")
    ]

    def __init__(self, overlay=None, parent=None):
        super().__init__(parent)
        self.overlay = overlay
        self.last_snack_time = time.time()
        self.last_stretch_time = time.time()
        self.coexistence_enabled = True

        self.pomodoro_active = False
        self.pomodoro_state = "idle"
        self.pomodoro_seconds_left = 0
        self.pomodoro_work_duration = 25 * 60
        self.pomodoro_rest_duration = 5 * 60
        self.pomodoro_cycles_completed = 0

        self.snack_timer = QTimer(self)
        self.snack_timer.setInterval(random.randint(600000, 1200000))
        self.snack_timer.timeout.connect(self._on_spontaneous_snack_timer)
        self.snack_timer.start()

        self.pomodoro_timer = QTimer(self)
        self.pomodoro_timer.setInterval(1000)
        self.pomodoro_timer.timeout.connect(self._on_pomodoro_tick)

        self.stretch_timer = QTimer(self)
        self.stretch_timer.setInterval(2700000)
        self.stretch_timer.timeout.connect(self._on_stretch_timer)
        self.stretch_timer.start()

    def trigger_spontaneous_snack(self, forced: bool = False) -> Dict[str, Any]:
        ov = self.overlay
        if not forced and ov and getattr(ov, "current_alpha", 1.0) < 0.5:
            return {}
        if not forced and ov and getattr(getattr(ov, "tts", None), "is_speaking", False):
            return {}

        item = random.choice(self.SNACK_CATALOG)
        self.last_snack_time = time.time()

        if ov:
            if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget") and ov.vrm_widget:
                try:
                    if hasattr(ov.vrm_widget, "set_expression"):
                        ov.vrm_widget.set_expression(item["expression"], 0.9)
                    if hasattr(ov.vrm_widget, "play_gesture"):
                        ov.vrm_widget.play_gesture(item["pose"])
                    elif hasattr(ov.vrm_widget, "start_motion"):
                        ov.vrm_widget.start_motion(item["pose"])
                except Exception:
                    pass

            dialogue = f"{item['emoji']} [{item['name'].upper()}]\n{item['phrase']}"
            if hasattr(ov, "show_balloon"):
                ov.show_balloon(dialogue, duration_ms=5200)

        self.snack_triggered_signal.emit(item["name"], item["phrase"])
        self.snack_timer.setInterval(random.randint(720000, 1380000))
        return item

    def trigger_choreography_dance(self, routine_name: Optional[str] = None) -> str:
        ov = self.overlay
        if not routine_name:
            chosen = random.choice(self.DANCE_ROUTINES)
            anim_name, label = chosen
        else:
            anim_name = routine_name
            label = f"Baile {routine_name}"

        if ov:
            if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget") and ov.vrm_widget:
                try:
                    if hasattr(ov.vrm_widget, "set_expression"):
                        ov.vrm_widget.set_expression("happy", 1.0)
                    if hasattr(ov.vrm_widget, "play_gesture"):
                        ov.vrm_widget.play_gesture(anim_name)
                    elif hasattr(ov.vrm_widget, "start_motion"):
                        ov.vrm_widget.start_motion(anim_name)
                except Exception:
                    pass

            speech = f"🎵 ¡Sincronizando ritmo musical! {label} 💖✨"
            if hasattr(ov, "show_balloon"):
                ov.show_balloon(speech, duration_ms=4500)

        self.dance_started_signal.emit(anim_name)
        return anim_name

    def trigger_stretch_break(self) -> None:
        ov = self.overlay
        self.last_stretch_time = time.time()
        if ov:
            if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget") and ov.vrm_widget:
                try:
                    if hasattr(ov.vrm_widget, "set_expression"):
                        ov.vrm_widget.set_expression("relaxed", 0.9)
                    if hasattr(ov.vrm_widget, "play_gesture"):
                        ov.vrm_widget.play_gesture("idle_stretch")
                    elif hasattr(ov.vrm_widget, "start_motion"):
                        ov.vrm_widget.start_motion("stretch_up")
                except Exception:
                    pass

            reminder = (
                "🌿 [PAUSA ACTIVA & REGLA 20-20-20]\n"
                "Amo Víctor, estiremos los hombros y descansemos la mirada unos 20 segundos mirando a lo lejos.\n"
                "¡Cuidar su salud y postura también es mi misión de maid! 🌸"
            )
            if hasattr(ov, "show_balloon"):
                ov.show_balloon(reminder, duration_ms=6000)

    def start_pomodoro_session(self) -> None:
        self.pomodoro_active = True
        self.pomodoro_state = "work"
        self.pomodoro_seconds_left = self.pomodoro_work_duration
        self.pomodoro_timer.start()

        ov = self.overlay
        if ov:
            if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget") and ov.vrm_widget:
                try:
                    if hasattr(ov.vrm_widget, "set_expression"):
                        ov.vrm_widget.set_expression("serious", 0.7)
                    if hasattr(ov.vrm_widget, "play_gesture"):
                        ov.vrm_widget.play_gesture("cheer")
                except Exception:
                    pass
            msg = (
                "🍅 [SESIÓN POMODORO INICIADA: 25 MIN]\n"
                "Modo concentración total activado. Estaré acompañándole en silencio absoluto.\n"
                "¡Usted puede con esto, Amo Víctor! 💪✨"
            )
            if hasattr(ov, "show_balloon"):
                ov.show_balloon(msg, duration_ms=4500)

        self.pomodoro_status_signal.emit(self.pomodoro_state, self.pomodoro_seconds_left)

    def stop_pomodoro_session(self) -> None:
        self.pomodoro_active = False
        self.pomodoro_state = "idle"
        self.pomodoro_seconds_left = 0
        self.pomodoro_timer.stop()
        if self.overlay and hasattr(self.overlay, "show_balloon"):
            self.overlay.show_balloon("🍅 Sesión Pomodoro pausada.", duration_ms=3000)
        self.pomodoro_status_signal.emit("idle", 0)

    def _on_spontaneous_snack_timer(self):
        if not self.coexistence_enabled:
            return
        if self.pomodoro_active and self.pomodoro_state == "work":
            return
        self.trigger_spontaneous_snack(forced=False)

    def _on_stretch_timer(self):
        if not self.coexistence_enabled:
            return
        self.trigger_stretch_break()

    def _on_pomodoro_tick(self):
        if not self.pomodoro_active:
            return

        self.pomodoro_seconds_left -= 1
        self.pomodoro_status_signal.emit(self.pomodoro_state, self.pomodoro_seconds_left)

        if self.pomodoro_seconds_left <= 0:
            if self.pomodoro_state == "work":
                self.pomodoro_cycles_completed += 1
                self.pomodoro_state = "break"
                self.pomodoro_seconds_left = self.pomodoro_rest_duration
                ov = self.overlay
                if ov:
                    if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget") and ov.vrm_widget:
                        try:
                            if hasattr(ov.vrm_widget, "set_expression"):
                                ov.vrm_widget.set_expression("happy", 1.0)
                            if hasattr(ov.vrm_widget, "play_gesture"):
                                ov.vrm_widget.play_gesture("clapping")
                        except Exception:
                            pass
                    msg = (
                        f"🎉 [¡BLOQUE DE FOCO COMPLETADO! (Ciclo {self.pomodoro_cycles_completed})]\n"
                        "¡Excelente trabajo, Amo Víctor! Tómese 5 minutos para estirarse, tomar agua o un snack conmigo. 🍵"
                    )
                    if hasattr(ov, "show_balloon"):
                        ov.show_balloon(msg, duration_ms=6000)
                    self.trigger_spontaneous_snack(forced=True)
            else:
                self.pomodoro_state = "work"
                self.pomodoro_seconds_left = self.pomodoro_work_duration
                if self.overlay and hasattr(self.overlay, "show_balloon"):
                    self.overlay.show_balloon("🔔 [FIN DEL DESCANSO]\n¡Listos para el siguiente bloque de foco productivo! ✨", duration_ms=4500)

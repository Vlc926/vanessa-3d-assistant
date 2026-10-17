import math
import random
from typing import Optional, Callable
from PyQt6.QtCore import QObject, QTimer, QPoint, QRect
from PyQt6.QtWidgets import QApplication
from core.avatar_directive_server import SmartLocomotionRouter
from src.visual.foot_lock import FootLockController

class RoamingController(QObject):
    def __init__(self, overlay):
        super().__init__(overlay)
        self.overlay = overlay

        self.is_roaming = False
        self.autonomous_roaming_enabled = True

        self.roam_timer = QTimer(self)
        self.roam_timer.timeout.connect(self._step_roam)
        self.roam_steps_total = 0
        self.roam_current_step = 0
        self.roam_start = QPoint()
        self.roam_target = QPoint()
        self.roam_prev_pos = QPoint()
        self.roam_final_comment = ""
        self.roam_on_arrived: Optional[Callable[[], None]] = None
        self.stride_phase = 0.0
        self.stride_length_px = 68.0
        self.foot_lock = FootLockController()
        self.last_route = {}

    def smooth_roam_to(
        self,
        target_x: int,
        target_y: int,
        duration_ms: Optional[int] = None,
        mode: str = "auto",
        comment: Optional[str] = None,
        on_arrived: Optional[Callable[[], None]] = None,
        urgency: float = 0.2,
        tone: str = "calm"
    ):
        ov = self.overlay

        if hasattr(ov, "screen_interact") and getattr(ov.screen_interact, "is_currently_perched", False):
            ov.screen_interact.is_currently_perched = False
            ov.screen_interact.current_perched_window = None
            if hasattr(ov, "vrm_widget") and hasattr(ov.vrm_widget, "set_perched"):
                ov.vrm_widget.set_perched(False)
        elif hasattr(ov, "vrm_widget") and hasattr(ov.vrm_widget, "set_perched"):
            ov.vrm_widget.set_perched(False)

        if hasattr(ov, "vrm_widget") and hasattr(ov.vrm_widget, "set_physical_state"):
            ov.vrm_widget.set_physical_state("GROUNDED")

        if mode in ("urgent", "media", "action", "button"):
            urgency = max(urgency, 0.85)
            tone = "urgent"
        elif mode in ("immediate", "teleport"):
            urgency = 1.0
            tone = "immediate"

        screens = QApplication.screens()
        screen_geom = screens[0].geometry() if screens else QRect(0, 0, 1920, 1200)
        sw = screen_geom.width()
        sh = screen_geom.height()

        target_x = max(20, min(sw - ov.width() - 35, int(target_x)))
        target_y = max(70, min(sh - ov.height() - 35, int(target_y)))

        actual_start = ov.get_current_screen_pos() if hasattr(ov, "get_current_screen_pos") else ov.pos()
        self.roam_start = actual_start
        self.roam_prev_pos = QPoint(actual_start.x(), actual_start.y())
        self.roam_target = QPoint(target_x, target_y)
        self.roam_final_comment = comment or ""
        self.roam_on_arrived = on_arrived

        dist = math.hypot(target_x - self.roam_start.x(), target_y - self.roam_start.y())
        is_urgent = (urgency >= 0.6) or (tone in ("urgent", "immediate"))
        needs_teleport = (is_urgent or dist >= 650.0) and (duration_ms is None)

        if needs_teleport:
            self._execute_teleport_transition(target_x, target_y)
            return

        speed_px_per_sec = 160.0
        if duration_ms is None or duration_ms <= 0:
            duration_ms = max(800, min(4500, int((dist / speed_px_per_sec) * 1000)))
        else:
            speed_px_per_sec = max(90.0, (dist / max(1, duration_ms)) * 1000.0)

        interval_ms = 33
        self.roam_steps_total = max(15, duration_ms // interval_ms)
        self.roam_current_step = 0
        self.is_roaming = True
        self.foot_lock.plant_foot([0.0, 0.0, 0.0], [float(self.roam_start.x()) / 1000.0, 0.0, 0.0])

        dx = 1 if target_x >= self.roam_start.x() else -1
        if hasattr(ov, "vrm_widget"):
            if hasattr(ov.vrm_widget, "set_body_facing"):
                ov.vrm_widget.set_body_facing(dx * 0.35, turn_speed=4.0)
            if hasattr(ov.vrm_widget, "send_motor_intent"):
                speed_ratio = max(0.8, min(1.3, speed_px_per_sec / 160.0))
                ov.vrm_widget.send_motor_intent("walk", vx=float(dx), vy=0.0, speed=speed_ratio, mood="happy", posture="locomotion")

        if getattr(ov, "using_live2d", True) and hasattr(ov, "live2d_widget"):
            ov.live2d_widget.start_motion("TapBody")

        ov.anim_state = "walking"
        ov.wake_up()
        self.roam_timer.start(interval_ms)

    def _execute_teleport_transition(self, target_x: int, target_y: int):
        ov = self.overlay
        self.is_roaming = True
        ov.anim_state = "walking"
        ov.wake_up()
        if hasattr(ov, "vrm_widget"):
            if hasattr(ov.vrm_widget, "set_physical_state"):
                ov.vrm_widget.set_physical_state("FREE_FALL", vy=-280.0)
            if hasattr(ov.vrm_widget, "apply_external_physics_impulse"):
                ov.vrm_widget.apply_external_physics_impulse(0.0, -18.0, 0.016)

        def _do_jump():
            ov.move(target_x, target_y)
            ov.sync_hyprland_position(target_x, target_y)
            ov.anchor_bottom_right = QPoint(target_x + ov.width(), target_y + ov.height())
            if hasattr(ov, "vrm_widget"):
                if hasattr(ov.vrm_widget, "set_physical_state"):
                    ov.vrm_widget.set_physical_state("GROUNDED", landing_compression=1.25)
                if hasattr(ov.vrm_widget, "sync_locomotion_step"):
                    ov.vrm_widget.sync_locomotion_step(40.0, 0.0, 0.3)

        def _do_settle():
            if hasattr(ov, "vrm_widget"):
                if hasattr(ov.vrm_widget, "sync_locomotion_step"):
                    ov.vrm_widget.sync_locomotion_step(0.0, 0.0, 0.0)
                if hasattr(ov.vrm_widget, "send_motor_intent"):
                    ov.vrm_widget.send_motor_intent("idle", vx=0.0, vy=0.0, speed=0.0, mood="happy", posture="standby")
            self.is_roaming = False
            ov.anim_state = "idle"
            if self.roam_final_comment:
                ov.show_balloon(self.roam_final_comment, duration_ms=4000)
            cb = self.roam_on_arrived
            self.roam_on_arrived = None
            if callable(cb):
                cb()

        QTimer.singleShot(120, _do_jump)
        QTimer.singleShot(300, _do_settle)

    def _step_roam(self):
        ov = self.overlay
        self.roam_current_step += 1
        t = self.roam_current_step / float(self.roam_steps_total)

        ease = 0.5 - 0.5 * math.cos(t * math.pi)
        cur_x = int(self.roam_start.x() + (self.roam_target.x() - self.roam_start.x()) * ease)
        cur_y = int(self.roam_start.y() + (self.roam_target.y() - self.roam_start.y()) * ease)

        step_dx = float(cur_x - self.roam_prev_pos.x())
        step_dy = float(cur_y - self.roam_prev_pos.y())
        step_dist = math.hypot(step_dx, step_dy)
        self.roam_prev_pos = QPoint(cur_x, cur_y)

        self.stride_phase = (self.stride_phase + (step_dist / self.stride_length_px) * math.pi) % (math.pi * 2.0)
        win_metric_x = float(cur_x) / 1000.0
        if self.foot_lock.check_liftoff([win_metric_x, 0.0, 0.0], step_distance_threshold=0.068):
            self.foot_lock.plant_foot([win_metric_x, 0.0, 0.0], [win_metric_x, 0.0, 0.0])

        ov.move(cur_x, cur_y)
        ov.sync_hyprland_position(cur_x, cur_y)
        ov.anchor_bottom_right = QPoint(cur_x + ov.width(), cur_y + ov.height())

        if hasattr(ov, "vrm_widget") and hasattr(ov.vrm_widget, "sync_locomotion_step"):
            vx_px = step_dx / 0.033
            vy_px = step_dy / 0.033
            ov.vrm_widget.sync_locomotion_step(vx_px, vy_px, self.stride_phase)

        if self.roam_current_step >= self.roam_steps_total:
            self.roam_timer.stop()
            self.is_roaming = False
            ov.anim_state = "idle"
            ov.move(self.roam_target.x(), self.roam_target.y())
            ov.sync_hyprland_position(self.roam_target.x(), self.roam_target.y())
            ov.anchor_bottom_right = QPoint(self.roam_target.x() + ov.width(), self.roam_target.y() + ov.height())

            if hasattr(ov, "vrm_widget"):
                if hasattr(ov.vrm_widget, "sync_locomotion_step"):
                    ov.vrm_widget.sync_locomotion_step(0.0, 0.0, self.stride_phase)
                if hasattr(ov.vrm_widget, "send_motor_intent"):
                    ov.vrm_widget.send_motor_intent("idle", vx=0.0, vy=0.0, speed=0.0, mood="relaxed", posture="standby")
                if hasattr(ov.vrm_widget, "set_body_facing"):
                    QTimer.singleShot(180, lambda: ov.vrm_widget.set_body_facing(0.0, turn_speed=2.6))
                if hasattr(ov.vrm_widget, "look_at"):
                    ov.vrm_widget.look_at(0.0, 0.0)

            if self.roam_final_comment:
                ov.show_balloon(self.roam_final_comment, duration_ms=4000)

            cb = self.roam_on_arrived
            self.roam_on_arrived = None
            if callable(cb):
                QTimer.singleShot(90, cb)

    def roam_home(self):
        ov = self.overlay
        geom = QApplication.primaryScreen().geometry()
        self.smooth_roam_to(
            geom.width() - ov.width() - 40,
            geom.height() - ov.height() - 45,
            duration_ms=1300,
            comment="¡De vuelta en mi esquinita favorita, Amo Víctor!"
        )

    def roam_bottom_left(self):
        ov = self.overlay
        geom = QApplication.primaryScreen().geometry()
        self.smooth_roam_to(
            35,
            geom.height() - ov.height() - 45,
            duration_ms=1600,
            comment="¡Aquí en la izquierda para acompañarte, Amo!"
        )

    def roam_top_right(self):
        ov = self.overlay
        geom = QApplication.primaryScreen().geometry()
        self.smooth_roam_to(
            geom.width() - ov.width() - 40,
            75,
            duration_ms=1500,
            comment="¡Qué linda vista panorámica desde aquí arriba, Amo Víctor! ✨"
        )

    def roam_follow_active_window(self):
        ov = self.overlay
        win = ov.os_interact.get_active_window()
        geom = QApplication.primaryScreen().geometry()
        sw = geom.width()
        sh = geom.height()

        if win and win.get("at") and win.get("size") and win["size"][0] > 100:
            wx, wy = win["at"]
            ww, wh = win["size"]
            tx = wx + ww + 15
            if tx + ov.width() > sw - 30:
                tx = max(25, wx - ov.width() - 15)
            ty = min(max(75, wy + 20), sh - ov.height() - 35)
            title = win.get("title") or win.get("class") or "tu trabajo"
            self.smooth_roam_to(
                int(tx), int(ty),
                duration_ms=1500,
                comment=f"¡Aquí pegadita a '{title[:22]}' cuidando de ti, Amo! ✨"
            )
        else:
            self.roam_stroll()

    def roam_stroll(self):
        ov = self.overlay
        geom = QApplication.primaryScreen().geometry()
        sw = geom.width()
        sh = geom.height()
        rx = random.randint(int(sw * 0.2), int(sw * 0.7))
        ry = sh - ov.height() - 45
        cute_comments = [
            "¡Dando un lindo paseíto por tu pantalla, Amo Víctor! 🌸",
            "Paseando un poquito para que el escritorio no esté aburrido, Amo~",
            "¡Estirando las piernitas! Siempre atenta a tus órdenes, Amo Víctor."
        ]
        self.smooth_roam_to(rx, ry, duration_ms=1500, comment=random.choice(cute_comments))

    def toggle_autonomous_roaming(self):
        ov = self.overlay
        self.autonomous_roaming_enabled = not self.autonomous_roaming_enabled
        if hasattr(ov, "proactive_engine"):
            ov.proactive_engine.autonomous_roaming_enabled = self.autonomous_roaming_enabled
        st = "activado" if self.autonomous_roaming_enabled else "desactivado"
        ov.show_balloon(f"🚶 Paseo autónomo {st}", duration_ms=3000)

    def on_proactive_roam(self, phrase: str, tx: int, ty: int):
        if self.autonomous_roaming_enabled and not self.is_roaming:
            self.smooth_roam_to(tx, ty, duration_ms=1600, comment=phrase)

"""
Autonomous Roaming & Screen Navigation Controller for Vanessa.
Handles smooth adaptive-speed roaming, cubic easing, and waypoint navigation
across Hyprland workspaces.
"""
import math
import random
from typing import Optional, Callable
from PyQt6.QtCore import QObject, QTimer, QPoint, QRect
from PyQt6.QtWidgets import QApplication


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
        self.roam_final_comment = ""
        self.roam_on_arrived: Optional[Callable[[], None]] = None

    def smooth_roam_to(
        self,
        target_x: int,
        target_y: int,
        duration_ms: Optional[int] = None,
        mode: str = "auto",
        comment: Optional[str] = None,
        on_arrived: Optional[Callable[[], None]] = None
    ):
        """Smoothly walks Vanessa to (target_x, target_y) across Hyprland using adaptive speeds."""
        ov = self.overlay
        screens = QApplication.screens()
        screen_geom = screens[0].geometry() if screens else QRect(0, 0, 1920, 1200)
        sw = screen_geom.width()
        sh = screen_geom.height()

        # Clamp destination within safe margins
        target_x = max(20, min(sw - ov.width() - 35, int(target_x)))
        target_y = max(70, min(sh - ov.height() - 35, int(target_y)))

        actual_start = ov.get_current_screen_pos() if hasattr(ov, "get_current_screen_pos") else ov.pos()
        self.roam_start = actual_start
        self.roam_target = QPoint(target_x, target_y)
        self.roam_final_comment = comment or ""
        self.roam_on_arrived = on_arrived

        dist = math.hypot(target_x - self.roam_start.x(), target_y - self.roam_start.y())

        # ADAPTIVE TRAVEL SPEEDS (Natural walking velocity, variable pacing)
        speed_px_per_sec = 180.0
        if duration_ms is None or duration_ms <= 0:
            if mode in ("urgent", "media", "action", "button"):
                speed_px_per_sec = 230.0
                duration_ms = max(900, min(3600, int((dist / speed_px_per_sec) * 1000)))
            elif mode in ("curious", "inspect", "curiosity", "point"):
                speed_px_per_sec = 170.0
                duration_ms = max(1100, min(4200, int((dist / speed_px_per_sec) * 1000)))
            elif mode in ("careful", "select", "highlight", "text"):
                speed_px_per_sec = 145.0
                duration_ms = max(1200, min(4500, int((dist / speed_px_per_sec) * 1000)))
            elif mode in ("stroll", "leisure", "idle_walk"):
                speed_px_per_sec = 125.0
                duration_ms = max(1400, min(5000, int((dist / speed_px_per_sec) * 1000)))
            else:  # auto
                if dist > 700:
                    speed_px_per_sec = 210.0
                elif dist > 300:
                    speed_px_per_sec = 175.0
                else:
                    speed_px_per_sec = 140.0
                duration_ms = max(1000, min(4000, int((dist / speed_px_per_sec) * 1000)))
        else:
            speed_px_per_sec = max(100.0, (dist / max(1, duration_ms)) * 1000.0)

        interval_ms = 33
        self.roam_steps_total = max(15, duration_ms // interval_ms)
        self.roam_current_step = 0
        self.is_roaming = True

        # Relaxed procedural walk (gesture_engine.js): body turned ~35deg toward the travel
        # direction, head counter-rotated so her face stays toward Amo while she glances around.
        if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
            dx = 1 if target_x >= self.roam_start.x() else -1
            # scene yaw +rel faces screen-right (VRM0 rotated by PI)
            ov.vrm_widget.set_body_facing(dx * 0.62, turn_speed=4.0)
            speed_ratio = max(0.8, min(1.3, speed_px_per_sec / 160.0))
            ov.vrm_widget.start_walking(dx, speed_ratio)

        if getattr(ov, "using_live2d", True) and hasattr(ov, "live2d_widget"):
            ov.live2d_widget.start_motion("TapBody")

        ov.anim_state = "walking"
        ov.wake_up()
        self.roam_timer.start(interval_ms)

    def _step_roam(self):
        ov = self.overlay
        self.roam_current_step += 1
        t = self.roam_current_step / float(self.roam_steps_total)

        # Ease-in-out with a short acceleration/deceleration (no window hop: the body bob
        # is done by the skeleton, so the window glides smoothly)
        ease = 0.5 - 0.5 * math.cos(t * math.pi)
        cur_x = int(self.roam_start.x() + (self.roam_target.x() - self.roam_start.x()) * ease)
        cur_y = int(self.roam_start.y() + (self.roam_target.y() - self.roam_start.y()) * ease)

        ov.move(cur_x, cur_y)
        ov.sync_hyprland_position(cur_x, cur_y)
        ov.anchor_bottom_right = QPoint(cur_x + ov.width(), cur_y + ov.height())

        if self.roam_current_step >= self.roam_steps_total:
            self.roam_timer.stop()
            self.is_roaming = False
            ov.anim_state = "idle"
            ov.move(self.roam_target.x(), self.roam_target.y())
            ov.sync_hyprland_position(self.roam_target.x(), self.roam_target.y())
            ov.anchor_bottom_right = QPoint(self.roam_target.x() + ov.width(), self.roam_target.y() + ov.height())

            # Transition out of walking into resting idle posture with smooth organic turn-around
            if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget"):
                # Legs settle first, then she turns calmly toward Amo (slow yaw = no snap/spin)
                ov.vrm_widget.stop_walking()
                QTimer.singleShot(180, lambda: ov.vrm_widget.set_body_facing(0.0, turn_speed=2.6))
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

import time
from typing import Tuple, Optional, Dict, Any
from PyQt6.QtCore import QObject, QTimer, QPoint
from PyQt6.QtWidgets import QApplication

class DesktopInertiaEngine(QObject):
    GRAVITY_M_S2 = 9.8
    PIXELS_PER_METER = 180.0

    def __init__(self, overlay):
        super().__init__(overlay)
        self.overlay = overlay
        self.vx = 0.0
        self.vy = 0.0
        self.friction = 0.88
        self.min_velocity = 0.4
        self.is_gliding = False
        self.is_falling = False
        self.drag_start_y = 0.0
        self.last_drag_time = 0.0
        self.last_drag_pos = (0.0, 0.0)
        self.glide_timer = QTimer(self)
        self.glide_timer.timeout.connect(self._step_glide)

    def start_drag(self, x: float, y: float):
        self.stop_glide()
        self.drag_start_y = float(y)
        self.last_drag_time = time.time()
        self.last_drag_pos = (float(x), float(y))
        self.vx = 0.0
        self.vy = 0.0
        ov = self.overlay
        if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget") and hasattr(ov.vrm_widget, "set_physical_state"):
            ov.vrm_widget.set_physical_state("DRAGGED_SUSPENDED")

    def update_drag(self, x: float, y: float):
        now = time.time()
        dt = max(0.001, now - self.last_drag_time)
        dx = float(x) - self.last_drag_pos[0]
        dy = float(y) - self.last_drag_pos[1]
        self.vx = dx / dt
        self.vy = dy / dt
        self.last_drag_time = now
        self.last_drag_pos = (float(x), float(y))
        ov = self.overlay
        if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget") and hasattr(ov.vrm_widget, "set_physical_state"):
            ov.vrm_widget.set_physical_state("DRAGGED_SUSPENDED", vy=dy)

    def _get_floor_y(self) -> float:
        ov = self.overlay
        screens = QApplication.screens()
        if screens:
            geom = screens[0].geometry()
            return float(geom.height() - ov.height() - 35)
        return 1000.0

    def _find_supporting_ledge(self, cur_x: float, prev_y: float, new_y: float) -> Optional[Dict[str, Any]]:
        ov = self.overlay
        if not hasattr(ov, "screen_interact") or not ov.screen_interact:
            return None
        try:
            wins = ov.screen_interact.get_hyprland_windows()
        except Exception:
            return None
        avatar_center_x = cur_x + (ov.width() * 0.5)
        overlap_offset = int(ov.height() * 0.22)
        for w in wins:
            wx = float(w.get("x", 0))
            wy = float(w.get("y", 0))
            ww = float(w.get("w", 0))
            if wx + 20.0 <= avatar_center_x <= wx + ww - 20.0:
                perch_y = wy - ov.height() + overlap_offset
                if prev_y <= perch_y + 24.0 and new_y >= perch_y - 10.0:
                    return {"window": w, "perch_y": perch_y}
        return None

    def release_drag(self, x: float, y: float) -> Tuple[float, float]:
        floor_y = self._get_floor_y()
        speed = (self.vx ** 2 + self.vy ** 2) ** 0.5
        if float(y) < floor_y - 25.0:
            self.is_falling = True
            self.is_gliding = True
            ov = self.overlay
            if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget") and hasattr(ov.vrm_widget, "set_physical_state"):
                ov.vrm_widget.set_physical_state("FREE_FALL", vy=max(120.0, self.vy))
            self.glide_timer.start(16)
        elif speed > self.min_velocity:
            self.is_falling = False
            self.is_gliding = True
            self.glide_timer.start(16)
        else:
            self.stop_glide()
        return self.vx, self.vy

    def apply_impulse(self, ix: float, iy: float):
        self.vx += float(ix)
        self.vy += float(iy)
        if not self.is_gliding:
            self.is_gliding = True
            self.glide_timer.start(16)

    def stop_glide(self, landed: bool = False, impact_speed: float = 0.0, perched_style: Optional[str] = None):
        self.is_gliding = False
        self.is_falling = False
        self.glide_timer.stop()
        self.vx = 0.0
        self.vy = 0.0
        ov = self.overlay
        if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget") and hasattr(ov.vrm_widget, "set_physical_state"):
            comp = max(0.45, min(1.25, impact_speed / 420.0))
            if perched_style:
                ov.vrm_widget.set_physical_state("GROUNDED", landing_compression=comp)
                QTimer.singleShot(250, lambda: ov.vrm_widget.set_perched(True, perched_style))
            elif landed:
                ov.vrm_widget.set_physical_state("GROUNDED", landing_compression=comp)
                QTimer.singleShot(250, lambda: ov.vrm_widget.set_physical_state("GROUNDED"))
            else:
                ov.vrm_widget.set_physical_state("GROUNDED")

    def pause(self):
        self.glide_timer.stop()

    def resume(self):
        if self.is_gliding:
            self.glide_timer.start(16)

    def _step_glide(self):
        if not self.is_gliding:
            return
        ov = self.overlay
        dt = 0.016
        cur_x = float(ov.x())
        cur_y = float(ov.y())

        if self.is_falling:
            gravity_accel = self.GRAVITY_M_S2 * self.PIXELS_PER_METER
            self.vy += gravity_accel * dt
            self.vx *= 0.95
            disp_x = self.vx * dt
            disp_y = self.vy * dt
            if getattr(ov, "using_vrm", False) and hasattr(ov, "vrm_widget") and hasattr(ov.vrm_widget, "set_physical_state"):
                ov.vrm_widget.set_physical_state("FREE_FALL", vy=self.vy)
        else:
            self.vx *= self.friction
            self.vy *= self.friction
            disp_x = self.vx
            disp_y = self.vy

        new_x = cur_x + disp_x
        new_y = cur_y + disp_y

        screens = QApplication.screens()
        if screens:
            geom = screens[0].geometry()
            max_x = float(geom.width() - ov.width() - 35)
            floor_y = float(geom.height() - ov.height() - 35)
        else:
            max_x = 1800.0
            floor_y = 1000.0

        clamped_x = max(20.0, min(new_x, max_x))
        clamped_y = max(20.0, min(new_y, floor_y))

        if abs(clamped_x - new_x) > 0.01:
            self.vx = -self.vx * 0.4

        if self.is_falling and self.vy > 0.0:
            ledge_hit = self._find_supporting_ledge(clamped_x, cur_y, new_y)
            if ledge_hit:
                perch_y = float(ledge_hit["perch_y"])
                ov.move(int(clamped_x), int(perch_y))
                if hasattr(ov, "sync_hyprland_position"):
                    ov.sync_hyprland_position(int(clamped_x), int(perch_y))
                ov.anchor_bottom_right = QPoint(int(clamped_x) + ov.width(), int(perch_y) + ov.height())
                if hasattr(ov, "screen_interact") and ov.screen_interact:
                    ov.screen_interact.is_currently_perched = True
                    ov.screen_interact.current_perched_window = ledge_hit["window"]
                self.stop_glide(landed=True, impact_speed=abs(self.vy), perched_style="sit")
                return

            if new_y >= floor_y - 1.0:
                impact_v = abs(self.vy)
                ov.move(int(clamped_x), int(floor_y))
                if hasattr(ov, "sync_hyprland_position"):
                    ov.sync_hyprland_position(int(clamped_x), int(floor_y))
                ov.anchor_bottom_right = QPoint(int(clamped_x) + ov.width(), int(floor_y) + ov.height())
                self.stop_glide(landed=True, impact_speed=impact_v)
                return

        if not self.is_falling and abs(clamped_y - new_y) > 0.01:
            self.vy = -self.vy * 0.4

        ov.move(int(clamped_x), int(clamped_y))
        if hasattr(ov, "sync_hyprland_position"):
            ov.sync_hyprland_position(int(clamped_x), int(clamped_y))
        ov.anchor_bottom_right = QPoint(int(clamped_x) + ov.width(), int(clamped_y) + ov.height())

        if not self.is_falling:
            speed = (self.vx ** 2 + self.vy ** 2) ** 0.5
            if speed < self.min_velocity:
                self.stop_glide()

import time
from typing import Tuple
from PyQt6.QtCore import QObject, QTimer, QPoint
from PyQt6.QtWidgets import QApplication

class DesktopInertiaEngine(QObject):
    def __init__(self, overlay):
        super().__init__(overlay)
        self.overlay = overlay
        self.vx = 0.0
        self.vy = 0.0
        self.friction = 0.88
        self.min_velocity = 0.4
        self.is_gliding = False
        self.last_drag_time = 0.0
        self.last_drag_pos = (0.0, 0.0)
        self.glide_timer = QTimer(self)
        self.glide_timer.timeout.connect(self._step_glide)

    def start_drag(self, x: float, y: float):
        self.stop_glide()
        self.last_drag_time = time.time()
        self.last_drag_pos = (float(x), float(y))
        self.vx = 0.0
        self.vy = 0.0

    def update_drag(self, x: float, y: float):
        now = time.time()
        dt = max(0.001, now - self.last_drag_time)
        dx = float(x) - self.last_drag_pos[0]
        dy = float(y) - self.last_drag_pos[1]
        self.vx = (dx / dt) * 0.16
        self.vy = (dy / dt) * 0.16
        self.last_drag_time = now
        self.last_drag_pos = (float(x), float(y))

    def release_drag(self, x: float, y: float) -> Tuple[float, float]:
        speed = (self.vx ** 2 + self.vy ** 2) ** 0.5
        if speed > self.min_velocity:
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

    def stop_glide(self):
        self.is_gliding = False
        self.glide_timer.stop()
        self.vx = 0.0
        self.vy = 0.0

    def pause(self):
        self.glide_timer.stop()

    def resume(self):
        if self.is_gliding:
            self.glide_timer.start(16)

    def _step_glide(self):
        if not self.is_gliding:
            return
        ov = self.overlay
        cur_x = float(ov.x())
        cur_y = float(ov.y())
        new_x = cur_x + self.vx
        new_y = cur_y + self.vy
        screens = QApplication.screens()
        if screens:
            geom = screens[0].geometry()
            clamped_x = max(20.0, min(new_x, float(geom.width() - ov.width() - 35)))
            clamped_y = max(70.0, min(new_y, float(geom.height() - ov.height() - 35)))
        else:
            clamped_x = max(20.0, min(new_x, 1800.0))
            clamped_y = max(70.0, min(new_y, 1000.0))

        if abs(clamped_x - new_x) > 0.01:
            self.vx = -self.vx * 0.4
        if abs(clamped_y - new_y) > 0.01:
            self.vy = -self.vy * 0.4

        ov.move(int(clamped_x), int(clamped_y))
        if hasattr(ov, "sync_hyprland_position"):
            ov.sync_hyprland_position(int(clamped_x), int(clamped_y))
        ov.anchor_bottom_right = QPoint(int(clamped_x) + ov.width(), int(clamped_y) + ov.height())

        self.vx *= self.friction
        self.vy *= self.friction

        speed = (self.vx ** 2 + self.vy ** 2) ** 0.5
        if speed < self.min_velocity:
            self.stop_glide()

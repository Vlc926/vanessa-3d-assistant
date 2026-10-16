import asyncio
import os
import subprocess
import threading
from typing import Dict, Any, Optional, List, Tuple
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

class HyprlandInteractionController(QObject):
    window_focused = pyqtSignal(str, str)
    active_window_changed = pyqtSignal(dict)
    telemetry_updated = pyqtSignal(dict)

    def __init__(self, overlay):
        super().__init__(overlay if isinstance(overlay, QObject) else None)
        self.overlay = overlay
        self.daemon = None
        self._daemon_thread: Optional[threading.Thread] = None
        self._is_running = False
        self.current_cursor = {"x": 0, "y": 0, "z": 0.0}
        self.current_active_window: Dict[str, Any] = {}
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_hypr_state)
        self.poll_timer.start(250)

    @property
    def active_daemon(self):
        if self.daemon:
            return self.daemon
        pe = getattr(self.overlay, "perception_engine", None)
        if pe and getattr(pe, "daemon", None):
            return pe.daemon
        pd = getattr(self.overlay, "perception_daemon", None)
        if pd and getattr(pd, "daemon", None):
            return pd.daemon
        return None

    def _poll_hypr_state(self):
        w = self.get_cached_active_window()
        if w:
            prev_addr = self.current_active_window.get("address", "")
            curr_addr = w.get("address", "")
            if curr_addr != prev_addr:
                self.current_active_window = w
                self.active_window_changed.emit(w)
                self.window_focused.emit(w.get("class", ""), w.get("title", ""))
        cx, cy = self.get_cached_cursor()
        self.current_cursor = {"x": cx, "y": cy, "z": 0.0}

    def start_daemon_service(self, target_fps: float = 30.0):
        if self._is_running:
            return
        self._is_running = True

        def _runner():
            try:
                from src.perception.daemon_main import PerceptionDaemon
                self.daemon = PerceptionDaemon(target_fps=target_fps)
                asyncio.run(self.daemon.run())
            except Exception:
                pass

        self._daemon_thread = threading.Thread(target=_runner, daemon=True)
        self._daemon_thread.start()

    def stop_daemon_service(self):
        self._is_running = False
        d = self.active_daemon
        if d:
            try:
                d.running = False
            except Exception:
                pass

    def get_cached_cursor(self) -> Tuple[float, float]:
        d = self.active_daemon
        if d and hasattr(d, "cached_cursor"):
            cur = d.cached_cursor
            if cur and "x" in cur and "y" in cur:
                return float(cur["x"]), float(cur["y"])
        return 0.0, 0.0

    def get_cached_active_window(self) -> Optional[Dict[str, Any]]:
        d = self.active_daemon
        if not d:
            return None
        active_addr = getattr(d, "cached_active_address", "")
        raw_clients = getattr(d.projector, "cached_clients", None)
        if active_addr and raw_clients:
            for w in raw_clients:
                if w.get("address", "").lower() == active_addr.lower():
                    return w
        return None

    def get_solid_platforms(self) -> List[Dict[str, Any]]:
        platforms: List[Dict[str, Any]] = []
        d = self.active_daemon
        if not d:
            return platforms
        raw_clients = getattr(d.projector, "cached_clients", None)
        if raw_clients:
            for w in raw_clients:
                if w.get("mapped", False) and not w.get("hidden", False):
                    at = w.get("at", [0, 0])
                    size = w.get("size", [0, 0])
                    if size[0] > 120 and size[1] > 100:
                        platforms.append({
                            "address": w.get("address", ""),
                            "title": w.get("title", ""),
                            "class": w.get("class", ""),
                            "top_ledge": {
                                "start": [float(at[0]), float(at[1]), 0.0],
                                "end": [float(at[0] + size[0]), float(at[1]), 0.0]
                            },
                            "bounds": [float(at[0]), float(at[0] + size[0]), float(at[1]), float(at[1] + size[1])]
                        })
        return platforms

    def push_window_with_inertia(
        self,
        address: str,
        impulse_x: float,
        impulse_y: float,
        mass: float = 50.0,
        friction: float = 8.0
    ):
        if self.daemon and hasattr(self.daemon, "actuator"):
            self.daemon.actuator.add_window_impulse(address, (impulse_x, impulse_y), mass, friction)
        else:
            try:
                subprocess.run(
                    ["hyprctl", "dispatch", "movewindowpixel", f"{int(impulse_x)} {int(impulse_y)},address:{address}"],
                    check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except Exception:
                pass

    def push_window_kinematic(self, address: str, dx: int, dy: int):
        if self.daemon and hasattr(self.daemon, "actuator"):
            self.daemon.actuator.push_window(address, dx, dy)
        else:
            try:
                subprocess.run(
                    ["hyprctl", "dispatch", "movewindowpixel", f"{int(dx)} {int(dy)},address:{address}"],
                    check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except Exception:
                pass

    def move_active(self, dx: int, dy: int):
        if self.daemon and hasattr(self.daemon, "actuator"):
            self.daemon.actuator.move_active(dx, dy)
        else:
            try:
                subprocess.run(
                    ["hyprctl", "dispatch", "moveactive", f"{int(dx)} {int(dy)}"],
                    check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except Exception:
                pass

    def toggle_floating(self):
        try:
            subprocess.run(
                ["hyprctl", "dispatch", "togglefloating"],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    def inject_click(self, button: str = "0xC0"):
        if self.daemon and hasattr(self.daemon, "actuator"):
            self.daemon.actuator.inject_pointer_click(button)

    def inject_mouse_move(self, x: int, y: int, absolute: bool = True):
        if self.daemon and hasattr(self.daemon, "actuator"):
            self.daemon.actuator.inject_pointer_move(x, y, absolute=absolute)

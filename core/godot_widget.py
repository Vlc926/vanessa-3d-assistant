import os
import subprocess
import atexit
from typing import Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt

from core.godot_bridge import GodotBridge

class GodotWidget(QWidget):
    clicked_signal = pyqtSignal()
    avatar_clicked = pyqtSignal(str, float, float)
    gesture_event = pyqtSignal(str, str)
    animation_started = pyqtSignal(str, float)
    animation_finished = pyqtSignal(str)
    head_pat_signal = pyqtSignal()
    body_click_signal = pyqtSignal()

    def __init__(self, parent=None, model_path: str = "/home/victor/.gemini/antigravity/scratch/jarvis_assistant/ui/static/vrm_models/Vanessa_Flagship_Anime.vrm", autostart_engine: bool = True):
        super().__init__(parent)
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.godot_bin = os.path.join(self.project_root, "bin/godot")
        self.godot_project_dir = os.path.join(self.project_root, "engine/godot_project")
        self.model_path = model_path
        self.godot_process: Optional[subprocess.Popen] = None
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent; border: none;")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.bridge = GodotBridge(host="127.0.0.1", port=8998, parent=self)
        self.bridge.avatar_clicked.connect(self.avatar_clicked.emit)
        self.bridge.gesture_event.connect(self.gesture_event.emit)
        self.bridge.animation_started.connect(self.animation_started.emit)
        self.bridge.animation_finished.connect(self.animation_finished.emit)
        self.bridge.head_pat_signal.connect(self.head_pat_signal.emit)
        self.bridge.body_click_signal.connect(self.body_click_signal.emit)
        self.bridge.connected_signal.connect(self._on_bridge_connected)
        
        if autostart_engine:
            self._start_godot_engine()
        self.bridge.start()
        atexit.register(self.terminate_engine)

    def _start_godot_engine(self):
        if not os.path.exists(self.godot_bin):
            return
        cmd = [
            self.godot_bin,
            "--path", self.godot_project_dir,
            f"--model={self.model_path}"
        ]
        try:
            self.godot_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            import threading, time
            def _hypr_setup():
                time.sleep(0.5)
                try:
                    subprocess.run(["hyprctl", "dispatch", "togglefloating", "class:Vanessa Desktop Overlay"], capture_output=True)
                    subprocess.run(["hyprctl", "dispatch", "pin", "class:Vanessa Desktop Overlay"], capture_output=True)
                except Exception:
                    pass
            threading.Thread(target=_hypr_setup, daemon=True).start()
        except Exception:
            pass

    def _on_bridge_connected(self):
        if self.model_path and os.path.exists(self.model_path):
            self.bridge.load_model(self.model_path)

    def load_model(self, model_path: str):
        self.model_path = model_path
        self.bridge.load_model(model_path)

    def set_speaking(self, is_speaking: bool):
        if is_speaking:
            self.bridge.start_talking()
        else:
            self.bridge.stop_talking()

    def set_expression(self, name: str, weight: float = 1.0):
        self.bridge.set_emotion(name, weight)

    def set_morph_target(self, name: str, weight: float = 1.0):
        self.bridge.set_emotion(name, weight)

    def set_emotion(self, mood: str, weight: float = 1.0):
        self.bridge.set_emotion(mood, weight)

    def start_motion(self, motion_name: str):
        self.bridge.play_gesture(motion_name)

    def play_gesture(self, name: str):
        self.bridge.play_gesture(name)

    def start_walking(self, direction: int = 1, speed: float = 1.0):
        self.bridge.start_walking(direction, speed)

    def stop_walking(self):
        self.bridge.stop_walking()

    def look_at(self, x: float, y: float):
        self.bridge.look_at(x, y)

    def set_avatar_mode(self, mode: str):
        pass

    def set_throttling(self, throttled: bool, fps: int = 15):
        pass

    def send_motor_intent(self, intent: str, vx: float = 0.0, vy: float = 0.0, speed: float = 1.0, mood: str = "neutral", posture: str = "standby"):
        if intent in ("walk", "roam"):
            self.start_walking(1 if vx >= 0 else -1, speed)
        else:
            self.stop_walking()

    def dispatch_sensory_event(self, payload: dict):
        pass

    def apply_conscious_skeletal_packet(self, packet: dict):
        self.bridge.send_command({"cmd": "conscious_skeletal_packet", "packet": packet})

    def send_canonical_command_packet(self, packet: dict):
        self.bridge.send_command({"cmd": "canonical_packet", "packet": packet})

    def apply_external_physics_impulse(self, dx: float, dy: float, dt: float = 0.016):
        pass

    def set_spring_profile(self, profile: str):
        pass

    def set_asymmetric_expression(self, preset: str, intensity: float = 1.0):
        self.set_expression(preset, intensity)

    def set_persona_mood(self, mood: str):
        pass

    def set_walk_speed(self, speed_ratio: float = 1.0):
        self.bridge.send_command({"cmd": "start_walking", "speed": speed_ratio, "dir": 1})

    def set_body_facing(self, yaw_radians: float, turn_speed: float = 5.0):
        pass

    def play_standby_pose(self):
        self.stop_walking()

    def play_playful_motion(self):
        self.play_gesture("wave")

    def set_music_active(self, active: bool, bpm: float = 120.0):
        pass

    def set_music_genre(self, genre: str = "pop", bpm: float = 120.0):
        pass

    def set_opacity(self, alpha: float):
        pass

    def frame_avatar(self):
        pass

    def set_perched(self, perched: bool, perch_style: str = "sit"):
        pass

    def notify_activity(self, state: str = "action"):
        pass

    def terminate_engine(self):
        if hasattr(self, "bridge") and self.bridge:
            self.bridge.stop()
        if self.godot_process and self.godot_process.poll() is None:
            try:
                self.godot_process.terminate()
                self.godot_process.wait(timeout=1.0)
            except Exception:
                try:
                    self.godot_process.kill()
                except Exception:
                    pass
            self.godot_process = None

    def closeEvent(self, event):
        self.terminate_engine()
        super().closeEvent(event)

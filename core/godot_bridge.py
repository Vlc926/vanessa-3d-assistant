import json
import socket
import threading
import time
from typing import Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal

class GodotBridge(QObject):
    avatar_clicked = pyqtSignal(str, float, float)
    gesture_event = pyqtSignal(str, str)
    animation_started = pyqtSignal(str, float)
    animation_finished = pyqtSignal(str)
    head_pat_signal = pyqtSignal()
    body_click_signal = pyqtSignal()
    model_loaded = pyqtSignal(str)
    connected_signal = pyqtSignal()
    disconnected_signal = pyqtSignal()

    def __init__(self, host: str = "127.0.0.1", port: int = 8998, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._connection_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._close_socket()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _close_socket(self):
        with self._lock:
            if self.sock:
                try:
                    self.sock.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    self.sock.close()
                except Exception:
                    pass
                self.sock = None

    def _connection_loop(self):
        while self._running:
            if not self.sock:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(2.0)
                    s.connect((self.host, self.port))
                    s.settimeout(1.0)
                    with self._lock:
                        self.sock = s
                    self.connected_signal.emit()
                except Exception:
                    time.sleep(1.0)
                    continue

            try:
                data = self.sock.recv(4096)
                if not data:
                    self._close_socket()
                    self.disconnected_signal.emit()
                    time.sleep(1.0)
                    continue
                lines = data.decode("utf-8", errors="ignore").split("\n")
                for line in lines:
                    cleaned = line.strip()
                    if cleaned:
                        self._process_message(cleaned)
            except socket.timeout:
                continue
            except Exception:
                self._close_socket()
                self.disconnected_signal.emit()
                time.sleep(1.0)

    def _process_message(self, raw: str):
        try:
            payload = json.loads(raw)
        except Exception:
            return
        event = payload.get("event", "")
        if event == "avatar_clicked":
            part = str(payload.get("part", "body"))
            x = float(payload.get("x", 0.0))
            y = float(payload.get("y", 0.0))
            self.avatar_clicked.emit(part, x, y)
            if part == "head":
                self.head_pat_signal.emit()
            else:
                self.body_click_signal.emit()
        elif event == "head_pat":
            self.head_pat_signal.emit()
        elif event == "animation_finished":
            name = str(payload.get("name", ""))
            self.animation_finished.emit(name)
        elif event == "model_loaded":
            name = str(payload.get("name", ""))
            self.model_loaded.emit(name)

    def send_command(self, payload: Dict[str, Any]):
        line = json.dumps(payload, ensure_ascii=False) + "\n"
        encoded = line.encode("utf-8")
        with self._lock:
            if self.sock:
                try:
                    self.sock.sendall(encoded)
                except Exception:
                    pass

    def load_model(self, path: str):
        self.send_command({"cmd": "load_model", "path": path})

    def start_walking(self, direction: int = 1, speed: float = 1.0):
        self.send_command({"cmd": "start_walking", "dir": direction, "speed": speed})

    def stop_walking(self):
        self.send_command({"cmd": "stop_walking"})

    def set_emotion(self, name: str, weight: float = 1.0):
        self.send_command({"cmd": "set_emotion", "name": name, "weight": weight})

    def start_talking(self):
        self.send_command({"cmd": "set_speaking", "is_speaking": True})

    def stop_talking(self):
        self.send_command({"cmd": "set_speaking", "is_speaking": False})

    def play_gesture(self, name: str, duration: float = 2.2):
        self.send_command({"cmd": "play_gesture", "name": name, "duration": duration})

    def look_at(self, x: float, y: float):
        self.send_command({"cmd": "look_at", "x": x, "y": y})

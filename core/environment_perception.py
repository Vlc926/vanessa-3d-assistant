import asyncio
import os
import threading
from typing import Dict, Any, Optional, List
from PyQt6.QtCore import QObject, pyqtSignal

class EnvironmentPerception(QObject):
    telemetry_received = pyqtSignal(dict)

    def __init__(self, overlay):
        super().__init__(overlay)
        self.overlay = overlay
        self.daemon = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self.cached_cursor = {"x": 0, "y": 0, "z": 0.0}
        self.cached_active_address = ""

    def start(self, target_fps: float = 30.0):
        if self._running:
            return
        self._running = True

        def _runner():
            try:
                from src.perception.daemon_main import PerceptionDaemon
                self.daemon = PerceptionDaemon(target_fps=target_fps)
                asyncio.run(self.daemon.run())
            except Exception:
                pass

        self._thread = threading.Thread(target=_runner, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self.daemon:
            try:
                self.daemon.running = False
            except Exception:
                pass

    def pause(self):
        pass

    def resume(self):
        pass

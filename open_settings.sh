#!/usr/bin/env bash
# open_settings.sh - Centro de Ajustes y Calibración de Vanessa

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

"$SCRIPT_DIR/.venv/bin/python" -c "
import sys, os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtNetwork import QLocalSocket
from ui.settings_dialog import VanessaSettingsDialog
from core.brain import AssistantBrain
from core.memory import MemoryManager
from core.system_control import SystemController
from core.file_manager import FileManager
from core.music_detector import MusicDetector

class StandaloneBridge:
    def __init__(self, mem):
        self.memory = mem
        cfg = mem.get_personality_config() or {}
        self.using_vrm = (cfg.get('avatar_type', 'vrm') == 'vrm')
        self.current_vrm_model = cfg.get('vrm_model', 'avatar_a')
        self.using_live2d = (cfg.get('avatar_type') == 'live2d')
        self.current_live2d_model = cfg.get('live2d_model', 'hiyori')
        self.current_theme = cfg.get('theme', 'hutao')
        self.vanessa_volume = int(cfg.get('voice_settings', {}).get('volume', 85))
        self.mouse_tracking_enabled = cfg.get('mouse_tracking', True)

    def open_models_folder(self):
        import subprocess
        subprocess.Popen(['xdg-open', 'ui/static/vrm_models'])

    def set_volume(self, v):
        self.vanessa_volume = v
        s = QLocalSocket()
        s.connectToServer('vanessa_overlay_ipc')
        if s.waitForConnected(300):
            s.write(f'volume:{v}\n'.encode())
            s.waitForBytesWritten(300)
            s.disconnectFromServer()

    def switch_vrm_model(self, m):
        self.current_vrm_model = m
        s = QLocalSocket()
        s.connectToServer('vanessa_overlay_ipc')
        if s.waitForConnected(300):
            s.write(f'model:{m}\n'.encode())
            s.waitForBytesWritten(300)
            s.disconnectFromServer()

    def switch_live2d_model(self, m):
        self.current_live2d_model = m

    def switch_theme(self, t):
        self.current_theme = t

    def show_balloon(self, msg, duration_ms=4000):
        pass

app = QApplication(sys.argv)
mem = MemoryManager()
brain = AssistantBrain(mem, SystemController(), FileManager(), MusicDetector(), 'config/personality.json')
bridge = StandaloneBridge(mem)
dlg = VanessaSettingsDialog(brain, bridge)

def on_saved():
    s = QLocalSocket()
    s.connectToServer('vanessa_overlay_ipc')
    if s.waitForConnected(400):
        s.write(b'reload_settings\n')
        s.waitForBytesWritten(400)
        s.disconnectFromServer()

dlg.settings_saved_signal.connect(on_saved)
sys.exit(dlg.exec())
"

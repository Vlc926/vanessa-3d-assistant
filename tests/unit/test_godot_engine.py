import os
import sys
import unittest
import subprocess
from PyQt6.QtWidgets import QApplication
from core.godot_bridge import GodotBridge
from core.godot_widget import GodotWidget

class TestGodotEngineIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.godot_bin = os.path.join(self.root_dir, "bin/godot")
        self.project_dir = os.path.join(self.root_dir, "engine/godot_project")

    def test_godot_binary_exists_and_runs(self):
        self.assertTrue(os.path.exists(self.godot_bin))
        self.assertTrue(os.access(self.godot_bin, os.X_OK))
        res = subprocess.run([self.godot_bin, "--version"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("4.", res.stdout)

    def test_godot_project_files_exist(self):
        project_file = os.path.join(self.project_dir, "project.godot")
        main_scene = os.path.join(self.project_dir, "main.tscn")
        avatar_script = os.path.join(self.project_dir, "scripts/avatar_rig.gd")
        ipc_script = os.path.join(self.project_dir, "scripts/ipc_server.gd")
        shader_file = os.path.join(self.project_dir, "shaders/cel_shading.gdshader")
        
        self.assertTrue(os.path.exists(project_file))
        self.assertTrue(os.path.exists(main_scene))
        self.assertTrue(os.path.exists(avatar_script))
        self.assertTrue(os.path.exists(ipc_script))
        self.assertTrue(os.path.exists(shader_file))

    def test_godot_headless_startup(self):
        res = subprocess.run(
            [self.godot_bin, "--path", self.project_dir, "--headless", "--quit"],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0)

    def test_godot_bridge_interface(self):
        bridge = GodotBridge(port=18998)
        self.assertIsNotNone(bridge.avatar_clicked)
        self.assertIsNotNone(bridge.gesture_event)
        self.assertIsNotNone(bridge.animation_finished)
        self.assertIsNotNone(bridge.head_pat_signal)

        events_received = []
        bridge.avatar_clicked.connect(lambda p, x, y: events_received.append((p, x, y)))
        bridge._process_message('{"event": "avatar_clicked", "part": "head", "x": 100, "y": 200}')
        self.assertEqual(len(events_received), 1)
        self.assertEqual(events_received[0], ("head", 100.0, 200.0))

    def test_godot_widget_api_compatibility(self):
        widget = GodotWidget(model_path="/fake/model.vrm", autostart_engine=False)
        self.assertTrue(hasattr(widget, "load_model"))
        self.assertTrue(hasattr(widget, "set_speaking"))
        self.assertTrue(hasattr(widget, "set_emotion"))
        self.assertTrue(hasattr(widget, "play_gesture"))
        self.assertTrue(hasattr(widget, "start_walking"))
        self.assertTrue(hasattr(widget, "stop_walking"))
        self.assertTrue(hasattr(widget, "look_at"))
        widget.set_speaking(True)
        widget.set_emotion("happy", 1.0)
        widget.start_walking(1, 1.2)
        widget.stop_walking()
        widget.terminate_engine()

if __name__ == "__main__":
    unittest.main()

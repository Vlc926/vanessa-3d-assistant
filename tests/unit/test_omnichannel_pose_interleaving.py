import unittest
from unittest.mock import MagicMock, patch
import time
from PyQt6.QtWidgets import QApplication
import sys

from core.desktop_life import DesktopLifeEngine
from core.hypr_interaction_controller import HyprlandInteractionController

class TestOmnichannelPoseInterleaving(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.mock_overlay = MagicMock()
        self.mock_overlay.using_vrm = True
        self.mock_overlay.vrm_widget = MagicMock()
        self.mock_overlay.current_alpha = 1.0
        self.mock_overlay.anim_state = "idle"
        self.mock_overlay.tts = MagicMock()
        self.mock_overlay.tts.is_speaking = False
        self.mock_overlay.is_roaming = False
        self.engine = DesktopLifeEngine(self.mock_overlay, check_interval_ms=999999)

    def tearDown(self):
        self.engine.life_timer.stop()
        self.engine.watchdog_timer.stop()

    def test_notify_user_activity_unthrottles_vrm(self):
        self.engine.is_throttled = True
        self.engine.notify_user_activity()
        self.assertFalse(self.engine.is_throttled)
        self.mock_overlay.vrm_widget.set_throttling.assert_called_with(False, 30.0)
        self.mock_overlay.vrm_widget.notify_activity.assert_called_with("action")

    def test_inactivity_watchdog_triggers_throttling(self):
        self.engine.is_throttled = False
        self.engine.last_user_activity_time = time.time() - 75.0
        self.engine.check_inactivity_watchdog()
        self.assertTrue(self.engine.is_throttled)
        self.mock_overlay.vrm_widget.set_throttling.assert_called_with(True, 15.0)

    def test_intercalated_pose_avoids_immediate_repeats(self):
        pool = ["pose_a", "pose_b", "pose_c"]
        self.engine.last_pose_name = "pose_a"
        self.engine.pose_history = ["pose_a"]
        for _ in range(5):
            prev = self.engine.last_pose_name
            self.engine.play_intercalated_pose(pool)
            self.assertNotEqual(self.engine.last_pose_name, prev)

    def test_on_active_window_changed_code_editor(self):
        win = {
            "address": "0x1234abcd",
            "class": "kitty",
            "title": "nvim main.py"
        }
        self.engine.on_active_window_changed(win)
        self.mock_overlay.vrm_widget.notify_activity.assert_called_with("action")
        self.assertTrue(self.engine.last_pose_name in ["think_chin", "thinking", "inspect", "ritsu_calc", "cheer_fist", "curious_lean", "pout"])

    def test_on_active_window_changed_media(self):
        win = {
            "address": "0x5678ef01",
            "class": "spotify",
            "title": "Music Track"
        }
        self.engine.on_active_window_changed(win)
        self.assertTrue(self.engine.last_pose_name in ["relax", "dance_reze", "happy_gesture", "clapping", "heart_hands", "peace_wink"])

    def test_hypr_controller_active_daemon_resolution(self):
        controller = HyprlandInteractionController(self.mock_overlay)
        fake_daemon = MagicMock()
        fake_daemon.cached_cursor = {"x": 100, "y": 200}
        fake_daemon.cached_active_address = "0x1122"
        fake_daemon.projector.cached_clients = [{"address": "0x1122", "title": "Editor", "class": "nvim"}]
        self.mock_overlay.perception_engine.daemon = fake_daemon

        cur_x, cur_y = controller.get_cached_cursor()
        self.assertEqual(cur_x, 100.0)
        self.assertEqual(cur_y, 200.0)

        win = controller.get_cached_active_window()
        self.assertIsNotNone(win)
        self.assertEqual(win.get("class"), "nvim")
        controller.poll_timer.stop()

if __name__ == "__main__":
    unittest.main()

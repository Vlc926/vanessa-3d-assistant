import PyQt6.QtWebEngineWidgets
import unittest
from unittest.mock import MagicMock
from PyQt6.QtCore import QObject, QPoint
from PyQt6.QtWidgets import QApplication

class MockOverlay(QObject):
    def __init__(self):
        super().__init__()
        self.using_vrm = True
        self.vrm_widget = MagicMock()
        self.is_sleeping = False
        self._vrm_custom_action_active = False
        self.is_dragging = False
        self._last_gaze_pos = (0.0, 0.0)
        self.brain = MagicMock()
        self.brain.personality = {}

    def x(self):
        return 500

    def y(self):
        return 300

    def width(self):
        return 350

    def height(self):
        return 580

    def screen(self):
        return None

    def show_balloon(self, text, duration_ms=4000):
        pass

class TestVanessaDesktopIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def test_cursor_gaze_with_perception_daemon(self):
        overlay = MockOverlay()
        daemon = MagicMock()
        daemon.cached_cursor = {"x": 1000, "y": 600}
        overlay.perception_daemon = daemon

        from vanessa_desktop import VanessaDesktopOverlay
        VanessaDesktopOverlay._track_cursor_gaze(overlay)

        overlay.vrm_widget.look_at.assert_called_once()
        args = overlay.vrm_widget.look_at.call_args[0]
        self.assertIsInstance(args[0], float)
        self.assertIsInstance(args[1], float)

    def test_screen_interaction_uses_perception_cache(self):
        overlay = MockOverlay()
        daemon = MagicMock()
        daemon.cached_cursor = {"x": 800, "y": 450}
        daemon.cached_active_address = "0x111222"
        daemon.projector.cached_clients = [
            {
                "address": "0x111222",
                "mapped": True,
                "hidden": False,
                "at": [100, 200],
                "size": [600, 400],
                "title": "Code Editor",
                "class": "code",
                "initialClass": "code",
                "pid": 4321
            }
        ]
        overlay.perception_daemon = daemon

        from core.screen_interaction import ScreenInteractor
        interactor = ScreenInteractor(overlay)

        windows = interactor.get_hyprland_windows()
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0]["address"], "0x111222")
        self.assertEqual(windows[0]["title"], "Code Editor")

        active = interactor.get_active_hyprland_window()
        self.assertIsNotNone(active)
        self.assertEqual(active["address"], "0x111222")
        self.assertEqual(active["title"], "Code Editor")

    def test_voice_action_push_window(self):
        overlay = MockOverlay()
        daemon = MagicMock()
        daemon.cached_active_address = "0x998877"
        overlay.perception_daemon = daemon

        from vanessa_desktop import VanessaDesktopOverlay
        action_dict = {
            "action": "push_window",
            "dx": 75,
            "dy": 0,
            "address": "0x998877"
        }
        VanessaDesktopOverlay.on_voice_action(overlay, action_dict)
        daemon.actuator.push_window.assert_called_once_with("0x998877", 75, 0)

    def test_avatar_lifecycle_controller(self):
        overlay = MockOverlay()
        from core.avatar_controller import AvatarLifecycleController
        ctrl = AvatarLifecycleController(overlay)

        ctrl.set_avatar_mode("chibi")
        self.assertEqual(ctrl.current_mode, "chibi")
        overlay.vrm_widget.set_avatar_mode.assert_called_with("chibi")

        toggled = ctrl.toggle_avatar_mode()
        self.assertEqual(toggled, "standard")

        ctrl.set_throttling(True, 15)
        self.assertTrue(ctrl.is_throttled)
        self.assertEqual(ctrl.throttle_fps, 15)
        overlay.vrm_widget.set_throttling.assert_called_with(True, 15)

        models = ctrl.get_available_models()
        self.assertIsInstance(models, dict)

    def test_dialogue_emotion_controller(self):
        overlay = MockOverlay()
        from core.dialogue_emotion_controller import DialogueEmotionController
        ctrl = DialogueEmotionController(overlay)

        weights = ctrl.map_emotion_to_blendshapes("happy", 0.9)
        self.assertAlmostEqual(weights["happy"], 0.9)

        packet = ctrl.build_command_packet(
            action="walk",
            target_coords=(100.0, 200.0, 0.0),
            emotion="happy",
            emotion_intensity=0.85,
            voice_id="dalia_anime",
            avatar_mode="chibi"
        )
        self.assertEqual(packet["action"], "walk")
        self.assertEqual(packet["avatar_mode"], "chibi")
        self.assertIn("blendshapes_weights", packet)
        self.assertAlmostEqual(packet["blendshapes_weights"]["happy"], 0.85)

    def test_hyprland_interaction_controller(self):
        overlay = MockOverlay()
        from core.hypr_interaction_controller import HyprlandInteractionController
        ctrl = HyprlandInteractionController(overlay)

        daemon = MagicMock()
        daemon.cached_cursor = {"x": 550, "y": 320}
        daemon.cached_active_address = "0xabc"
        daemon.projector.cached_clients = [
            {
                "address": "0xabc",
                "mapped": True,
                "hidden": False,
                "at": [50, 50],
                "size": [800, 600],
                "title": "Terminal",
                "class": "kitty"
            }
        ]
        ctrl.daemon = daemon

        cur = ctrl.get_cached_cursor()
        self.assertEqual(cur, (550.0, 320.0))

        active = ctrl.get_cached_active_window()
        self.assertIsNotNone(active)
        self.assertEqual(active["address"], "0xabc")

        platforms = ctrl.get_solid_platforms()
        self.assertEqual(len(platforms), 1)
        self.assertEqual(platforms[0]["address"], "0xabc")
        self.assertIn("top_ledge", platforms[0])

        ctrl.push_window_with_inertia("0xabc", 30.0, 0.0)
        daemon.actuator.add_window_impulse.assert_called_once_with("0xabc", (30.0, 0.0), 50.0, 8.0)

    def test_desktop_physics_inertia(self):
        overlay = MockOverlay()
        from core.desktop_physics import DesktopInertiaEngine
        engine = DesktopInertiaEngine(overlay)

        engine.start_drag(100.0, 100.0)
        engine.update_drag(150.0, 150.0)
        vx, vy = engine.release_drag(150.0, 150.0)
        self.assertIsInstance(vx, float)
        self.assertIsInstance(vy, float)
        engine.stop_glide()
        self.assertFalse(engine.is_gliding)

if __name__ == "__main__":
    unittest.main()

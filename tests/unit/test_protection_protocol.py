import unittest
import os
import sys
from PyQt6.QtCore import QCoreApplication
from core.protection_protocol import ProtectionProtocolManager

class DummyOverlay:
    def __init__(self):
        self.balloons = []
        self.using_vrm = True
        self.vrm_widget = DummyVRMWidget()
        self.tts = None
        self.ambient_voice_only = False

    def show_balloon(self, msg, duration_ms=3000):
        self.balloons.append(msg)

class DummyVRMWidget:
    def __init__(self):
        self.expressions = []
        self.gestures = []
        self.intents = []

    def set_expression(self, name, weight=1.0):
        self.expressions.append((name, weight))

    def play_gesture(self, name):
        self.gestures.append(name)

    def send_motor_intent(self, intent, vx, vy, speed, mood, posture):
        self.intents.append((intent, mood, posture))

class TestProtectionProtocol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        if not QCoreApplication.instance():
            cls.app = QCoreApplication(sys.argv)
        else:
            cls.app = QCoreApplication.instance()

    def setUp(self):
        self.overlay = DummyOverlay()
        self.mgr = ProtectionProtocolManager(self.overlay)

    def tearDown(self):
        if self.mgr.timer.isActive():
            self.mgr.timer.stop()
        if self.mgr.cooldown_timer.isActive():
            self.mgr.cooldown_timer.stop()

    def test_initial_state(self):
        self.assertFalse(self.mgr.is_active)
        self.assertEqual(self.mgr.total_duration_seconds, 300)
        self.assertEqual(self.mgr.remaining_seconds, 0)
        self.assertEqual(self.mgr.cooldown_remaining, 0)
        self.assertEqual(self.mgr.formatted_remaining_time(), "00:00")

    def test_activation_starts_five_minute_demo(self):
        success, msg = self.mgr.activate_protocol_demo(reason="manual_test")
        self.assertTrue(success)
        self.assertTrue(self.mgr.is_active)
        self.assertEqual(self.mgr.remaining_seconds, 300)
        self.assertEqual(self.mgr.formatted_remaining_time(), "05:00")
        self.assertTrue(self.mgr.timer.isActive())
        self.assertTrue(any("DEMO 5 MIN" in b for b in self.overlay.balloons))
        self.assertTrue(any(exp[0] == "serious" for exp in self.overlay.vrm_widget.expressions))

    def test_cannot_activate_while_already_active(self):
        self.mgr.activate_protocol_demo()
        success, msg = self.mgr.activate_protocol_demo()
        self.assertFalse(success)
        self.assertIn("ya está activo", msg)

    def test_timer_countdown_ticks(self):
        self.mgr.activate_protocol_demo()
        ticks_received = []
        self.mgr.tick_signal.connect(lambda sec, s: ticks_received.append((sec, s)))

        self.mgr._on_tick()
        self.assertEqual(self.mgr.remaining_seconds, 299)
        self.assertEqual(self.mgr.formatted_remaining_time(), "04:59")
        self.assertEqual(len(ticks_received), 1)
        self.assertEqual(ticks_received[0], (299, "04:59"))

    def test_natural_completion_after_300_seconds(self):
        self.mgr.activate_protocol_demo()
        self.mgr.remaining_seconds = 1
        self.mgr._on_tick()

        self.assertFalse(self.mgr.is_active)
        self.assertEqual(self.mgr.remaining_seconds, 0)
        self.assertEqual(self.mgr.cooldown_remaining, 120)
        self.assertTrue(any("CONCLUIDO CON ÉXITO" in b for b in self.overlay.balloons))

    def test_manual_deactivation_enters_cooldown(self):
        self.mgr.activate_protocol_demo()
        success, msg = self.mgr.deactivate_protocol(completed_naturally=False)
        self.assertTrue(success)
        self.assertFalse(self.mgr.is_active)
        self.assertEqual(self.mgr.cooldown_remaining, 120)
        self.assertTrue(self.mgr.cooldown_timer.isActive())

        can_run, reason = self.mgr.can_activate()
        self.assertFalse(can_run)
        self.assertIn("estabilidad mental", reason)

    def test_cooldown_decrement(self):
        self.mgr.cooldown_remaining = 2
        self.mgr._on_cooldown_tick()
        self.assertEqual(self.mgr.cooldown_remaining, 1)
        self.mgr._on_cooldown_tick()
        self.assertEqual(self.mgr.cooldown_remaining, 0)

        can_run, _ = self.mgr.can_activate()
        self.assertTrue(can_run)

if __name__ == "__main__":
    unittest.main()

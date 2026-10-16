import unittest
import os
import sys
from PyQt6.QtWidgets import QApplication

class TestConsciousSkeletalController(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        from core.conscious_skeletal_controller import ConsciousSkeletalController
        class DummyOverlay:
            def __init__(self):
                self.vrm_widget = None
        self.overlay = DummyOverlay()
        self.controller = ConsciousSkeletalController(self.overlay)

    def tearDown(self):
        if hasattr(self.controller, "timer") and self.controller.timer:
            self.controller.timer.stop()

    def test_channel1_conversation_turns(self):
        self.controller.handle_conversation_turn("user", "¿Cómo estás hoy Vanessa?", emotion="", intent="")
        pkt = self.controller.compute_packet()
        c1 = pkt["channel1_conversation"]
        self.assertEqual(c1["role"], "user")
        self.assertEqual(c1["intent"], "question")
        self.assertIn("curious", pkt["biomechanical_pose"]["facial_preset"])
        self.assertGreater(pkt["biomechanical_pose"]["head_tilt"][0], 0.0)

        self.controller.handle_conversation_turn("assistant", "¡Excelente, Amo Víctor! Estoy muy feliz.", emotion="happy", intent="statement")
        pkt2 = self.controller.compute_packet()
        c1_2 = pkt2["channel1_conversation"]
        self.assertEqual(c1_2["role"], "assistant")
        self.assertEqual(c1_2["emotion"], "happy")
        self.assertEqual(pkt2["biomechanical_pose"]["facial_preset"], "joy")

    def test_channel2_desktop_environments(self):
        self.controller.update_desktop_context("server.py - Neovim", "kitty", inactive_windows=[1, 2, 3], is_fullscreen=False)
        pkt = self.controller.compute_packet()
        c2 = pkt["channel2_desktop"]
        self.assertEqual(c2["category"], "ide")
        self.assertEqual(c2["inactive_count"], 3)
        self.assertFalse(c2["is_fullscreen"])

        self.controller.update_desktop_context("GitHub - Mozilla Firefox", "firefox", inactive_windows=[], is_fullscreen=False)
        pkt2 = self.controller.compute_packet()
        self.assertEqual(pkt2["channel2_desktop"]["category"], "browser")

    def test_channel3_multimedia_classification(self):
        self.controller.update_media_context("music", title="Idol", artist="Yoasobi", is_playing=True, tempo_bpm=160.0)
        pkt = self.controller.compute_packet()
        c3 = pkt["channel3_media"]
        self.assertEqual(c3["type"], "music")
        self.assertTrue(c3["sway_enabled"])
        self.assertEqual(c3["tempo_bpm"], 160.0)

        self.controller.update_media_context("video", title="Zenless Zone Zero Cutscene", artist="YouTube", is_playing=True, tempo_bpm=120.0)
        pkt2 = self.controller.compute_packet()
        self.assertEqual(pkt2["channel3_media"]["type"], "video")
        self.assertFalse(pkt2["channel3_media"]["sway_enabled"])

        self.controller.update_media_context("audio", title="Call", is_playing=True)
        pkt3 = self.controller.compute_packet()
        self.assertEqual(pkt3["channel3_media"]["type"], "audio")
        self.assertFalse(pkt3["channel3_media"]["sway_enabled"])

    def test_channel4_haptics_reactions(self):
        self.controller.handle_haptic_interaction("head_pat")
        pkt = self.controller.compute_packet()
        c4 = pkt["channel4_haptics"]
        self.assertEqual(c4["state"], "head_pat")
        self.assertLess(c4["squash_factor"], 1.0)
        self.assertEqual(pkt["biomechanical_pose"]["facial_preset"], "joy")

        self.controller.handle_haptic_interaction("drag_move", 100, 100, dx=15, dy=-10)
        pkt2 = self.controller.compute_packet()
        self.assertEqual(pkt2["channel4_haptics"]["state"], "drag_move")
        self.assertNotEqual(pkt2["channel4_haptics"]["inertia_lean"], [0.0, 0.0])
        self.assertGreater(pkt2["channel4_haptics"]["squash_factor"], 1.0)

        self.controller.handle_haptic_interaction("drag_release")
        pkt3 = self.controller.compute_packet()
        self.assertEqual(pkt3["channel4_haptics"]["inertia_lean"], [0.0, 0.0])

    def test_channel5_dual_inactivity_timers(self):
        self.controller.update_inactivity_timers(pc_idle_seconds=10.0, vanessa_idle_seconds=120.0)
        pkt = self.controller.compute_packet()
        c5 = pkt["channel5_dual_idle"]
        self.assertEqual(c5["mode"], "companion_working")
        self.assertEqual(c5["pc_idle_seconds"], 10.0)
        self.assertEqual(c5["vanessa_idle_seconds"], 120.0)

        self.controller.update_inactivity_timers(pc_idle_seconds=300.0, vanessa_idle_seconds=300.0)
        pkt2 = self.controller.compute_packet()
        self.assertEqual(pkt2["channel5_dual_idle"]["mode"], "system_sleep")
        self.assertGreater(pkt2["biomechanical_pose"]["arm_relaxation"], 0.9)

        self.controller.update_inactivity_timers(pc_idle_seconds=5.0, vanessa_idle_seconds=5.0)
        pkt3 = self.controller.compute_packet()
        self.assertEqual(pkt3["channel5_dual_idle"]["mode"], "active_dialogue")

    def test_packet_schema_and_signal_emission(self):
        received = []
        self.controller.skeletal_packet_emitted.connect(lambda p: received.append(p))
        self.controller.dispatch()
        self.assertEqual(len(received), 1)
        pkt = received[0]
        self.assertIn("channel1_conversation", pkt)
        self.assertIn("channel2_desktop", pkt)
        self.assertIn("channel3_media", pkt)
        self.assertIn("channel4_haptics", pkt)
        self.assertIn("channel5_dual_idle", pkt)
        self.assertIn("channel6_tactical", pkt)
        self.assertIn("biomechanical_pose", pkt)
        bio = pkt["biomechanical_pose"]
        self.assertIn("head_tilt", bio)
        self.assertIn("spine_lean", bio)
        self.assertIn("contrapposto_shift", bio)
        self.assertIn("knee_flexion", bio)

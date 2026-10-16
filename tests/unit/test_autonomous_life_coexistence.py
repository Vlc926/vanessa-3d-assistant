import unittest
import os
import sys
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication, QWidget
from core.autonomous_life import AutonomousCoexistenceEngine
from core.protection_protocol import ProtectionProtocolManager
from ui.context_menu import build_context_menu

class DummyOverlayForCoexistence(QWidget):
    def __init__(self):
        super().__init__()
        self.balloons = []
        self.using_vrm = True
        self.vrm_widget = DummyVRM()
        self.current_alpha = 1.0
        self.tts = DummyTTS()
        self.ambient_voice_only = False
        self.vrm_models_map = {"vivian": "/dummy/v.vrm"}
        self.current_vrm_model = "vivian"
        self.current_size_preset = "medium"
        self.avatar_mode = "standard"
        self.protection_protocol = ProtectionProtocolManager(self)
        self.autonomous_coexistence = AutonomousCoexistenceEngine(self)

    def show_balloon(self, msg, duration_ms=3000):
        self.balloons.append(msg)

    def trigger_protection_protocol_demo(self):
        return self.protection_protocol.activate_protocol_demo(reason="menu")

    def trigger_coexistence_snack(self):
        return self.autonomous_coexistence.trigger_spontaneous_snack(forced=True)

    def trigger_choreography_dance(self, routine_name=None):
        return self.autonomous_coexistence.trigger_choreography_dance(routine_name)

    def trigger_stretch_break(self):
        return self.autonomous_coexistence.trigger_stretch_break()

    def start_pomodoro_session(self):
        return self.autonomous_coexistence.start_pomodoro_session()

    def stop_pomodoro_session(self):
        return self.autonomous_coexistence.stop_pomodoro_session()

    def open_omni_sync_dialog(self):
        pass

    def open_settings_dialog(self):
        pass

    def switch_vrm_model(self, k):
        pass

    def open_model_selector_dialog(self):
        pass

    def set_avatar_size_preset(self, k, w, h):
        pass

    def toggle_avatar_mode(self):
        pass

    def wake_up(self):
        pass

    def enter_sleep_mode(self):
        pass

    def safe_exit(self):
        pass

class DummyTTS:
    def __init__(self):
        self.is_speaking = False

class DummyVRM:
    def __init__(self):
        self.expressions = []
        self.gestures = []
        self.motions = []

    def set_expression(self, name, weight=1.0):
        self.expressions.append((name, weight))

    def play_gesture(self, name):
        self.gestures.append(name)

    def start_motion(self, name):
        self.motions.append(name)

class TestAutonomousLifeCoexistence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.overlay = DummyOverlayForCoexistence()
        self.engine = self.overlay.autonomous_coexistence

    def tearDown(self):
        if self.engine.snack_timer.isActive():
            self.engine.snack_timer.stop()
        if self.engine.pomodoro_timer.isActive():
            self.engine.pomodoro_timer.stop()
        if self.engine.stretch_timer.isActive():
            self.engine.stretch_timer.stop()

    def test_no_virtual_pet_bars(self):
        self.assertFalse(hasattr(self.engine, "hunger_level"))
        self.assertFalse(hasattr(self.engine, "thirst_level"))
        self.assertFalse(hasattr(self.engine, "pet_health"))
        self.assertFalse(hasattr(self.engine, "buy_food"))

    def test_snack_catalog_diversity(self):
        catalog = self.engine.SNACK_CATALOG
        self.assertGreaterEqual(len(catalog), 8)
        names = [item["name"] for item in catalog]
        self.assertTrue(any("Ramen" in n for n in names))
        self.assertTrue(any("Matcha" in n or "Té" in n for n in names))
        self.assertTrue(any("Dorayaki" in n for n in names))
        self.assertTrue(any("Boba" in n for n in names))
        self.assertTrue(any("Taiyaki" in n for n in names))
        self.assertTrue(any("Pocky" in n for n in names))

    def test_spontaneous_snack_execution(self):
        snack = self.engine.trigger_spontaneous_snack(forced=True)
        self.assertIsNotNone(snack)
        self.assertIn("name", snack)
        self.assertIn("phrase", snack)
        self.assertTrue(len(self.overlay.balloons) > 0)
        self.assertIn(snack["name"].upper(), self.overlay.balloons[-1])
        self.assertTrue(len(self.overlay.vrm_widget.gestures) > 0)

    def test_choreography_dance_execution(self):
        routine = self.engine.trigger_choreography_dance("dance_reze")
        self.assertEqual(routine, "dance_reze")
        self.assertIn("dance_reze", self.overlay.vrm_widget.gestures)
        self.assertTrue(any("ritmo musical" in b for b in self.overlay.balloons))

    def test_stretch_break_rule_20_20_20(self):
        self.engine.trigger_stretch_break()
        self.assertTrue(any("PAUSA ACTIVA" in b for b in self.overlay.balloons))
        self.assertIn("idle_stretch", self.overlay.vrm_widget.gestures)

    def test_pomodoro_session_cycle(self):
        self.engine.start_pomodoro_session()
        self.assertTrue(self.engine.pomodoro_active)
        self.assertEqual(self.engine.pomodoro_state, "work")
        self.assertEqual(self.engine.pomodoro_seconds_left, 25 * 60)

        self.engine.pomodoro_seconds_left = 1
        self.engine._on_pomodoro_tick()

        self.assertEqual(self.engine.pomodoro_state, "break")
        self.assertEqual(self.engine.pomodoro_cycles_completed, 1)
        self.assertEqual(self.engine.pomodoro_seconds_left, 5 * 60)
        self.assertTrue(any("BLOQUE DE FOCO COMPLETADO" in b for b in self.overlay.balloons))

        self.engine.stop_pomodoro_session()
        self.assertFalse(self.engine.pomodoro_active)
        self.assertEqual(self.engine.pomodoro_state, "idle")

    def test_context_menu_contains_protocol_and_coexistence(self):
        menu = build_context_menu(self.overlay)
        action_texts = [a.text() for a in menu.actions()]
        self.assertTrue(any("Protocolo de Protección" in t for t in action_texts))
        self.assertTrue(any("Convivencia" in t for t in action_texts))

        for a in menu.actions():
            sub = a.menu()
            if sub and "Convivencia" in a.text():
                sub_texts = [sa.text() for sa in sub.actions()]
                self.assertTrue(any("Merendar" in st for st in sub_texts))
                self.assertTrue(any("Pomodoro" in st for st in sub_texts))
                self.assertTrue(any("Baile" in st for st in sub_texts))
                self.assertTrue(any("Pausa Activa" in st for st in sub_texts))

    def test_context_menu_reflects_active_protocol_state(self):
        self.overlay.protection_protocol.activate_protocol_demo()
        menu = build_context_menu(self.overlay)
        action_texts = [a.text() for a in menu.actions()]
        self.assertTrue(any("Desactivar Protocolo" in t for t in action_texts))
        self.overlay.protection_protocol.deactivate_protocol()

if __name__ == "__main__":
    unittest.main()

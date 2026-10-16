import unittest
import os
import sys
from PyQt6.QtWidgets import QApplication

class TestUIAndModelsBlackbox(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def test_settings_dialog_end_to_end_flow(self):
        from ui.settings_dialog import VanessaSettingsDialog

        class MockMemory:
            def __init__(self):
                self.saved_personality = None
            def save_personality_config(self, cfg):
                self.saved_personality = dict(cfg)

        class MockBrain:
            def __init__(self):
                self.personality = {
                    "name": "Vanessa Maid",
                    "title": "Asistente Personal",
                    "mouse_tracking": True,
                    "eye_saccades": True,
                    "breathing_physics": True,
                    "head_patting": True,
                    "music_perception": True,
                    "ambient_voice_only": True,
                    "voice_settings": {"online_voice": "gaby_elevenlabs"}
                }
                self.settings = {"voice_settings": {}}
                self.gemini_api_key = "test_key_12345"
                self.preferred_model = "gemini-3.5-flash"
                self.settings_path = "/tmp/test_vanessa_settings.json"
                self.memory = MockMemory()
            def set_api_key(self, k):
                self.gemini_api_key = k
            def set_preferred_model(self, m):
                self.preferred_model = m

        class MockOverlay:
            def __init__(self):
                self.vanessa_volume = 85
                self.vrm_models_map = {
                    "vanessa": "/tmp/a.vrm",
                    "vita": "/tmp/vita.vrm",
                    "darkness": "/tmp/darkness.vrm"
                }
                self.current_vrm_model = "vanessa"
                self.stt = None
                self.voice_mgr = None
                self.mouse_tracking_enabled = True
                self.balloon_msg = ""
                self.switched_vrm = None
            def pos(self):
                from PyQt6.QtCore import QPoint
                return QPoint(200, 200)
            def width(self):
                return 400
            def height(self):
                return 600
            def show_balloon(self, msg, duration_ms=3000):
                self.balloon_msg = msg
            def switch_vrm_model(self, name):
                self.switched_vrm = name

        brain = MockBrain()
        overlay = MockOverlay()
        dlg = VanessaSettingsDialog(brain, overlay)

        dlg.name_edit.setText("Vanessa ZZZ")
        dlg.title_edit.setText("Combat Maid Assistant")
        dlg.key_edit.setText("new_gemini_key_999")

        model_idx = -1
        for i in range(dlg.model_combo.count()):
            if dlg.model_combo.itemData(i) == "vrm:vita":
                model_idx = i
                break
        if model_idx >= 0:
            dlg.model_combo.setCurrentIndex(model_idx)

        signal_emitted = []
        dlg.settings_saved_signal.connect(lambda: signal_emitted.append(True))

        dlg.save_all_settings()

        self.assertTrue(len(signal_emitted) > 0)
        self.assertEqual(brain.personality["name"], "Vanessa ZZZ")
        self.assertEqual(brain.personality["title"], "Combat Maid Assistant")
        self.assertEqual(brain.gemini_api_key, "new_gemini_key_999")
        if model_idx >= 0:
            self.assertEqual(brain.personality["vrm_model"], "vita")
            self.assertEqual(overlay.switched_vrm, "vita")
        self.assertIn("guardados con éxito", overlay.balloon_msg)

    def test_model_selector_dialog_card_interaction(self):
        from ui.model_selector_dialog import VanessaModelSelectorDialog

        models_map = {
            "vanessa": "/tmp/fake_vanessa.vrm",
            "vita": "/tmp/fake_vita.vrm",
            "darkness": "/tmp/fake_darkness.vrm"
        }

        dlg = VanessaModelSelectorDialog(models_map, current_model="vanessa")

        chosen = []
        dlg.model_chosen.connect(lambda k, p: chosen.append((k, p)))

        dlg._select_model("vita")
        self.assertEqual(len(chosen), 1)
        self.assertEqual(chosen[0][0], "vita")
        self.assertEqual(chosen[0][1], "/tmp/fake_vita.vrm")
        self.assertEqual(dlg.current_model, "vita")

    def test_avatar_lifecycle_mode_toggle(self):
        from core.avatar_controller import AvatarLifecycleController

        class MockVRMWidget:
            def __init__(self):
                self.mode = "standard"
                self.throttled = False
                self.fps = 60
                self.loaded_path = ""
            def set_avatar_mode(self, m):
                self.mode = m
            def set_throttling(self, th, fps):
                self.throttled = th
                self.fps = fps
            def load_model(self, path):
                self.loaded_path = path

        class MockOverlay:
            def __init__(self):
                self.vrm_widget = MockVRMWidget()

        overlay = MockOverlay()
        ctrl = AvatarLifecycleController(overlay)

        new_mode = ctrl.toggle_avatar_mode()
        self.assertEqual(new_mode, "chibi")
        self.assertEqual(overlay.vrm_widget.mode, "chibi")

        new_mode2 = ctrl.toggle_avatar_mode()
        self.assertEqual(new_mode2, "standard")
        self.assertEqual(overlay.vrm_widget.mode, "standard")

        ctrl.set_throttling(True, 30)
        self.assertTrue(overlay.vrm_widget.throttled)
        self.assertEqual(overlay.vrm_widget.fps, 30)

        ctrl.load_model("kira")
        self.assertEqual(ctrl.current_model_key, "kira")
        self.assertTrue(overlay.vrm_widget.loaded_path.endswith("Kira_Urban_Anime.vrm"))

        ctrl.load_model("ellen")
        self.assertEqual(ctrl.current_model_key, "ellen")
        self.assertTrue(overlay.vrm_widget.loaded_path.endswith("Ellen_Joe_Maid.vrm"))

        ctrl.load_model("nicole")
        self.assertEqual(ctrl.current_model_key, "nicole")
        self.assertTrue(overlay.vrm_widget.loaded_path.endswith("Nicole_Demara.vrm"))

        ctrl.load_model("anby")
        self.assertEqual(ctrl.current_model_key, "anby")
        self.assertTrue(overlay.vrm_widget.loaded_path.endswith("Anby_Demara.vrm"))

        ctrl.load_model("belle")
        self.assertEqual(ctrl.current_model_key, "belle")
        self.assertTrue(overlay.vrm_widget.loaded_path.endswith("Belle_Proxy.vrm"))

        ctrl.load_model("jane")
        self.assertEqual(ctrl.current_model_key, "jane")
        self.assertTrue(overlay.vrm_widget.loaded_path.endswith("Jane_Doe_Thiren.vrm"))

        ctrl.load_model("miyabi")
        self.assertEqual(ctrl.current_model_key, "miyabi")
        self.assertTrue(overlay.vrm_widget.loaded_path.endswith("Hoshimi_Miyabi_Section6.vrm"))

        ctrl.load_model("billy")
        self.assertEqual(ctrl.current_model_key, "billy")
        self.assertTrue(overlay.vrm_widget.loaded_path.endswith("Billy_Kid_Starlight.vrm"))

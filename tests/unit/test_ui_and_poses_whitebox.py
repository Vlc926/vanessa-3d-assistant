import unittest
import os
import sys
from PyQt6.QtWidgets import QApplication, QLineEdit, QComboBox, QScrollArea, QTextEdit

class TestUIAndPosesWhitebox(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    def test_settings_dialog_stylesheet_and_dimensions(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        settings_file = os.path.join(root, "ui/settings_dialog.py")
        self.assertTrue(os.path.exists(settings_file))
        with open(settings_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("min-height: 38px", content)
        self.assertIn("max-height: 42px", content)
        self.assertIn("padding: 4px 10px", content)
        self.assertIn("QScrollArea", content)
        self.assertIn("_wrap_tab_scroll", content)

    def test_settings_dialog_tabs_wrapped_in_scroll_area(self):
        from ui.settings_dialog import VanessaSettingsDialog
        class DummyBrain:
            def __init__(self):
                self.personality = {"name": "Vanessa", "title": "Maid"}
                self.settings = {}
                self.gemini_api_key = ""
                self.preferred_model = "gemini-3.5-flash"
                self.settings_path = "/tmp/dummy_settings.json"
        class DummyOverlay:
            def __init__(self):
                self.vanessa_volume = 80
                self.vrm_models_map = {"vanessa": "/tmp/a.vrm", "vita": "/tmp/v.vrm"}
                self.current_vrm_model = "vanessa"
                self.stt = None
                self.voice_mgr = None
            def pos(self):
                from PyQt6.QtCore import QPoint
                return QPoint(100, 100)
            def width(self):
                return 400
            def height(self):
                return 600

        dlg = VanessaSettingsDialog(DummyBrain(), DummyOverlay())
        self.assertEqual(dlg.tabs.count(), 4)
        for i in range(dlg.tabs.count()):
            tab_widget = dlg.tabs.widget(i)
            self.assertIsInstance(tab_widget, QScrollArea, f"Tab {i} must be a QScrollArea")

    def test_model_catalog_includes_zzz_and_maids(self):
        from core.avatar_controller import AvatarLifecycleController
        class DummyOverlay:
            pass
        ctrl = AvatarLifecycleController(DummyOverlay())
        models = ctrl.get_available_models()
        self.assertIn("vanessa", models)
        self.assertIn("ellen", models)
        self.assertIn("nicole", models)
        self.assertIn("anby", models)
        self.assertIn("jane", models)
        self.assertIn("miyabi", models)
        self.assertIn("billy", models)
        self.assertIn("belle", models)
        self.assertIn("kira", models)
        self.assertIn("aoi", models)
        self.assertIn("kuro", models)
        self.assertIn("orion", models)

    def test_vrm_models_files_exist_on_disk(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        vrm_dir = os.path.join(root, "ui/static/vrm_models")
        expected_files = [
            "Vanessa_Flagship_Anime.vrm",
            "Ellen_Joe_Maid.vrm",
            "Nicole_Demara.vrm",
            "Anby_Demara.vrm",
            "Jane_Doe_Thiren.vrm",
            "Hoshimi_Miyabi_Section6.vrm",
            "Billy_Kid_Starlight.vrm",
            "Belle_Proxy.vrm",
            "Kira_Urban_Anime.vrm",
            "Aoi_Cyber_Anime.vrm",
            "Kuro_Goth_Anime.vrm",
            "Orion_SciFi_Anime.vrm"
        ]
        for f in expected_files:
            path = os.path.join(vrm_dir, f)
            self.assertTrue(os.path.exists(path), f"Expected model file {f} to exist")
            self.assertGreater(os.path.getsize(path), 1000000, f"Model file {f} is too small")

    def test_kinematics_no_inverted_legs_idle(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        pk_file = os.path.join(root, "ui/vrm/personality_kinematics.js")
        with open(pk_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("idle-maid.vrma", content, "idle-maid.vrma has inverted leg tracks and must not be used")
        self.assertIn("idle_maid: { file: '/ui/vrm/animations/idle_loop.vrma'", content)

    def test_app_js_initial_motion_is_idle_loop(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        app_file = os.path.join(root, "ui/vrm/app.js")
        with open(app_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("animController.playMotion('idle_loop')", content)
        self.assertNotIn("animController.playMotion('idle-maid')", content)

    def test_spring_dynamics_safe_bounds(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        st_file = os.path.join(root, "ui/vrm/spring_dynamics_tuner.js")
        with open(st_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("stiffness = 2.4", content)
        self.assertNotIn("stiffness = 3.2", content)

    def test_no_comments_in_modified_code(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        files_to_check = [
            os.path.join(root, "ui/settings_dialog.py"),
            os.path.join(root, "ui/model_selector_dialog.py"),
            os.path.join(root, "core/avatar_controller.py"),
            os.path.join(root, "core/protection_protocol.py"),
            os.path.join(root, "core/autonomous_life.py"),
            os.path.join(root, "ui/context_menu.py"),
            os.path.join(root, "vanessa_desktop.py"),
            os.path.join(root, "tests/unit/test_protection_protocol.py"),
            os.path.join(root, "tests/unit/test_autonomous_life_coexistence.py"),
            os.path.join(root, "core/conscious_skeletal_controller.py"),
            os.path.join(root, "tests/unit/test_conscious_skeletal_controller.py"),
            os.path.join(root, "ui/vrm/conscious_skeletal_driver.js"),
            os.path.join(root, "ui/vrm/foot_ik_solver.js"),
            os.path.join(root, "ui/vrm/gaze_controller.js"),
            os.path.join(root, "ui/vrm/animation_controller.js"),
            os.path.join(root, "ui/vrm/app.js"),
            os.path.join(root, "ui/vrm/spring_dynamics_tuner.js"),
            os.path.join(root, "ui/vrm/frame_modulation_controller.js"),
            os.path.join(root, "ui/vrm/squash_stretch_modifier.js"),
            os.path.join(root, "ui/vrm/personality_kinematics.js"),
            os.path.join(root, "ui/vrm/gacha_cinematic_controller.js"),
            os.path.join(root, "ui/vrm/mmd_humanoid_adapter.js"),
            os.path.join(root, "ui/vrm/gacha_animation_graph.js"),
            os.path.join(root, "deploy/docker/simulation_server.py"),
            os.path.join(root, "deploy/docker/run_container.sh"),
            os.path.join(root, "deploy/docker/Dockerfile"),
            os.path.join(root, "deploy/docker/docker-compose.yml")
        ]
        c_slash = chr(47) * 2
        c_open = chr(47) + chr(42)
        c_close = chr(42) + chr(47)

        import ast
        for path in files_to_check:
            self.assertTrue(os.path.exists(path))
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if path.endswith(".py"):
                tree = ast.parse(content, filename=path)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
                        doc = ast.get_docstring(node)
                        if doc:
                            self.fail(f"Docstring found in {path}")
                for idx, line in enumerate(content.splitlines(), 1):
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        self.fail(f"Comment found in Python file {path}:{idx}")
            else:
                for idx, line in enumerate(content.splitlines(), 1):
                    stripped = line.strip()
                    self.assertFalse(stripped.startswith("#"), f"Comment at {path}:{idx}")
                    self.assertFalse(stripped.startswith(c_slash), f"Slash comment at {path}:{idx}")
                    self.assertFalse(stripped.startswith(c_open), f"Block comment at {path}:{idx}")
                    self.assertFalse(c_close in stripped, f"Block comment end at {path}:{idx}")

    def test_conscious_skeletal_driver_bounded_slerp(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        driver_file = os.path.join(root, "ui/vrm/conscious_skeletal_driver.js")
        with open(driver_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("hips.quaternion.multiply", content)
        self.assertNotIn("leftUpperLeg.quaternion.multiply", content)
        self.assertNotIn("spine.quaternion.multiply", content)
        self.assertNotIn("head.quaternion.multiply", content)
        self.assertIn("leftUpperLeg.quaternion.slerp", content)
        self.assertIn("hips.quaternion.slerp", content)

    def test_model_facing_direction_is_frontal(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        app_file = os.path.join(root, "ui/vrm/app.js")
        mm_file = os.path.join(root, "ui/vrm/motion_matching.js")
        with open(app_file, "r", encoding="utf-8") as f:
            app_content = f.read()
        with open(mm_file, "r", encoding="utf-8") as f:
            mm_content = f.read()
        self.assertIn("const baseRot = Math.PI;", app_content)
        self.assertIn("const baseRot = Math.PI;", mm_content)
        self.assertIn("newVrm.scene.rotation.y = Math.PI;", app_content)

    def test_docker_simulation_assets_exist(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        docker_dir = os.path.join(root, "deploy/docker")
        for f in ["Dockerfile", "docker-compose.yml", "run_container.sh", "simulation_server.py"]:
            p = os.path.join(docker_dir, f)
            self.assertTrue(os.path.exists(p), f"Expected {f} to exist")

    def test_gacha_animation_graph_bone_masking_and_locomotion(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        graph_file = os.path.join(root, "ui/vrm/gacha_animation_graph.js")
        with open(graph_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("pelvicYOffset", content)
        self.assertIn("pelvicRollOffset", content)
        self.assertIn("updateMaskedEmotes", content)
        self.assertIn("thinking_chin", content)
        self.assertIn("joyful_cheer", content)

    def test_mmd_humanoid_adapter_mapping(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        adapter_file = os.path.join(root, "ui/vrm/mmd_humanoid_adapter.js")
        with open(adapter_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("全ての親", content)
        self.assertIn("センター", content)
        self.assertIn("isolateMmdIkChains", content)
        self.assertIn("createExpressionProxy", content)

    def test_vroid_official_models_exist_and_valid(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        vrm_dir = os.path.join(root, "ui/static/vrm_models")
        vroid_samples = [
            "VRoid_AliciaSolid.vrm",
            "VRoid_AvatarSample_A.vrm",
            "VRoid_AvatarSample_B.vrm",
            "VRoid_AvatarSample_C.vrm",
            "VRoid_AvatarSample_VRM1.vrm",
            "VRoid_Sendagaya_Shibu.vrm",
            "VRoid_Victoria_Rubin.vrm",
            "VRoid_Vita.vrm",
            "VRoid_Vivi.vrm"
        ]
        for f in vroid_samples:
            p = os.path.join(vrm_dir, f)
            self.assertTrue(os.path.exists(p), f"VRoid model {f} must exist")
            self.assertGreater(os.path.getsize(p), 5000000, f"VRoid model {f} size too small")
            with open(p, "rb") as fp:
                header = fp.read(4)
                self.assertEqual(header, b"glTF", f"VRoid model {f} must be valid glTF")

    def test_spring_dynamics_tuner_advanced_physics(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        spring_file = os.path.join(root, "ui/vrm/spring_dynamics_tuner.js")
        with open(spring_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("applyExternalImpulse", content)
        self.assertIn("windStrength", content)
        self.assertIn("stiffnessMultiplier", content)
        self.assertIn("dragMultiplier", content)
        self.assertIn("breathPulse", content)

    def test_anime_facial_driver_vroid_compatibility(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        face_file = os.path.join(root, "ui/vrm/anime_facial_driver.js")
        with open(face_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("catalogModelExpressions", content)
        self.assertIn("aliasMap", content)
        self.assertIn("asymmetricPresets", content)
        self.assertIn("Fcl_ALL_Joy", content)
        self.assertIn("Fcl_EYE_Close_L", content)
        self.assertIn("setDecoupledGaze", content)

    def test_conscious_skeletal_driver_upper_chest_and_shoulders(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        driver_file = os.path.join(root, "ui/vrm/conscious_skeletal_driver.js")
        with open(driver_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("upperChest", content)
        self.assertIn("leftShoulder", content)
        self.assertIn("rightShoulder", content)
        self.assertIn("leftHand", content)

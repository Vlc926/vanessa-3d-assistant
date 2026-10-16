import unittest
import math
import os

class TestSakugaZZZPipeline(unittest.TestCase):
    def test_volume_conservation_math(self):
        stretch_factors = [0.7, 0.85, 1.0, 1.25, 1.5]
        exaggeration = 1.0

        for lam in stretch_factors:
            comp = math.pow(lam, -0.5 * exaggeration)
            volume = comp * lam * comp
            self.assertAlmostEqual(volume, 1.0, places=5)

    def test_stepped_frame_quantization(self):
        fps = 24.0
        interval = 1.0 / fps

        t1 = 0.025
        step1 = math.floor(t1 / interval) * interval
        self.assertAlmostEqual(step1, 0.0, places=4)

        t2 = 0.045
        step2 = math.floor(t2 / interval) * interval
        self.assertAlmostEqual(step2, interval, places=4)

        t3 = 0.085
        step3 = math.floor(t3 / interval) * interval
        self.assertAlmostEqual(step3, 2.0 * interval, places=4)

    def test_damped_harmonic_overshoot(self):
        decay = 18.0
        freq = 26.0

        amp_0 = math.exp(-decay * 0.0) * math.cos(freq * 0.0)
        self.assertAlmostEqual(amp_0, 1.0, places=4)

        amp_t = math.exp(-decay * 0.2) * math.cos(freq * 0.2)
        self.assertLess(abs(amp_t), 0.1)

    def test_new_js_files_exist_and_clean(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        js_files = [
            os.path.join(root, "ui/vrm/squash_stretch_modifier.js"),
            os.path.join(root, "ui/vrm/frame_modulation_controller.js"),
            os.path.join(root, "ui/vrm/anime_facial_driver.js"),
            os.path.join(root, "ui/vrm/spring_dynamics_tuner.js")
        ]

        c_line = chr(47) * 2
        c_open = chr(47) + chr(42)
        c_close = chr(42) + chr(47)

        for path in js_files:
            self.assertTrue(os.path.exists(path), f"File {path} must exist")
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for idx, line in enumerate(lines, 1):
                    stripped = line.strip()
                    self.assertFalse(stripped.startswith("#"), f"Hash comment at {path}:{idx}")
                    self.assertFalse(stripped.startswith(c_line), f"Slash comment at {path}:{idx}")
                    self.assertFalse(stripped.startswith(c_open), f"Block comment at {path}:{idx}")
                    self.assertFalse(c_close in stripped, f"Block comment end at {path}:{idx}")

    def test_app_js_integration(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        app_js_path = os.path.join(root, "ui/vrm/app.js")
        self.assertTrue(os.path.exists(app_js_path))

        with open(app_js_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("SquashAndStretchModifier", content)
        self.assertIn("FrameModulationController", content)
        self.assertIn("AnimeFacialDriver", content)
        self.assertIn("SpringDynamicsTuner", content)
        self.assertIn("squashStretchModifier.update", content)
        self.assertIn("frameModulationController.update", content)
        self.assertIn("animeFacialDriver.update", content)
        self.assertIn("springDynamicsTuner.update", content)

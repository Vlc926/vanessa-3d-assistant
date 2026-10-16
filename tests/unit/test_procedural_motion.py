import unittest
import math
from tests.test_doubles.loader import get_procedural_motion_class

class TestProceduralMotion(unittest.TestCase):
    def setUp(self):
        motion_cls = get_procedural_motion_class()
        self.motion = motion_cls(omega=8.0)

    def test_resting_breathing_frequency(self):
        self.assertAlmostEqual(self.motion.breath_freq, 0.28, delta=1e-3)
        chest, clavicle = self.motion.update_breathing(dt=0.1)
        self.assertIsInstance(chest, float)
        self.assertIsInstance(clavicle, float)

    def test_stress_modulation_and_decay(self):
        self.motion.trigger_stress()
        self.assertAlmostEqual(self.motion.breath_freq, 0.65, delta=1e-3)

        for _ in range(50):
            self.motion.update_breathing(dt=0.2)

        self.assertLess(self.motion.breath_freq, 0.40)
        self.assertGreaterEqual(self.motion.breath_freq, 0.28)

    def test_gaze_spring_asymptotic_convergence(self):
        target = math.radians(45.0)
        dt = 1.0 / 60.0
        for _ in range(60):
            self.motion.update_gaze_spring(target, dt)

        self.assertAlmostEqual(self.motion.gaze_angle, target, delta=0.05)

    def test_gaze_spring_angular_clamping(self):
        extreme_target = math.radians(120.0)
        max_allowed = math.radians(85.0)
        dt = 1.0 / 60.0
        for _ in range(60):
            self.motion.update_gaze_spring(extreme_target, dt)

        self.assertLessEqual(self.motion.gaze_angle, max_allowed + 1e-4)

    def test_ocular_saccades_micro_jitter(self):
        jx, jy = self.motion.update_ocular_saccades(1.5)
        self.assertLessEqual(abs(jx), 0.02)
        self.assertLessEqual(abs(jy), 0.02)

if __name__ == "__main__":
    unittest.main()

import unittest
import math
from tests.test_doubles.loader import get_procedural_motion_class

class TestF9ProceduralMicroMovements(unittest.TestCase):
    def setUp(self):
        motion_cls = get_procedural_motion_class()
        self.motion = motion_cls(omega=8.0)

    def test_f9_dual_frequency_breathing_baseline(self):
        self.assertAlmostEqual(self.motion.breath_freq, 0.28, delta=1e-3)
        c, cl = self.motion.update_breathing(dt=0.05)
        self.assertLessEqual(abs(c), 0.05)
        self.assertLessEqual(abs(cl), 0.02)

    def test_f9_breathing_stress_acceleration_and_decay(self):
        self.motion.trigger_stress()
        self.assertAlmostEqual(self.motion.breath_freq, 0.65, delta=1e-3)
        for _ in range(40):
            self.motion.update_breathing(dt=0.1)
        self.assertLess(self.motion.breath_freq, 0.50)

    def test_f9_critically_damped_gaze_filter(self):
        target = math.radians(30.0)
        angles = []
        for _ in range(60):
            a = self.motion.update_gaze_spring(target, dt=1.0/60.0)
            angles.append(a)
        self.assertAlmostEqual(angles[-1], target, delta=0.05)
        self.assertGreater(angles[15], angles[0])
        self.assertGreater(angles[30], angles[15])

    def test_f9_cervical_gaze_tracking_clamping(self):
        target = math.radians(110.0)
        max_angle = math.radians(85.0)
        for _ in range(60):
            self.motion.update_gaze_spring(target, dt=1.0/60.0)
        self.assertLessEqual(self.motion.gaze_angle, max_angle + 1e-4)

    def test_f9_ocular_saccades_micro_tremor(self):
        jx, jy = self.motion.update_ocular_saccades(2.0)
        self.assertLessEqual(abs(jx), 0.02)
        self.assertLessEqual(abs(jy), 0.02)

    def test_f9_zero_dt_time_freeze_stability(self):
        initial_angle = self.motion.gaze_angle
        angle = self.motion.update_gaze_spring(math.radians(45.0), dt=0.0)
        self.assertEqual(angle, initial_angle)

if __name__ == "__main__":
    unittest.main()

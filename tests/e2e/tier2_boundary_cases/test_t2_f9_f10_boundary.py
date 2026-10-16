import unittest
import math
from tests.test_doubles.loader import get_procedural_motion_class, get_vision_services_class

class TestT2F9F10Boundary(unittest.TestCase):
    def setUp(self):
        motion_cls = get_procedural_motion_class()
        vision_cls = get_vision_services_class()
        self.motion = motion_cls(omega=8.0)
        self.service = vision_cls(offline_mode=True)

    def test_t2_f9_gaze_angle_exceeding_pi(self):
        self.motion.update_gaze_spring(math.pi, dt=0.1)
        max_limit = math.radians(85.0)
        self.assertLessEqual(self.motion.gaze_angle, max_limit + 1e-4)

        self.motion.update_gaze_spring(-math.pi, dt=0.1)
        min_limit = -math.radians(85.0)
        self.assertGreaterEqual(self.motion.gaze_angle, min_limit - 1e-4)

    def test_t2_f9_micro_dt_breathing(self):
        c, cl = self.motion.update_breathing(dt=1e-8)
        self.assertFalse(math.isnan(c))
        self.assertFalse(math.isnan(cl))

    def test_t2_f9_breathing_stress_long_term_decay(self):
        self.motion.trigger_stress()
        for _ in range(200):
            self.motion.update_breathing(dt=0.5)
        self.assertAlmostEqual(self.motion.breath_freq, 0.28, delta=1e-3)

    def test_t2_f9_ocular_saccades_huge_time(self):
        jx, jy = self.motion.update_ocular_saccades(1e6)
        self.assertFalse(math.isnan(jx))
        self.assertFalse(math.isnan(jy))

    def test_t2_f9_spring_zero_omega(self):
        motion_cls = get_procedural_motion_class()
        frozen = motion_cls(omega=0.0)
        angle = frozen.update_gaze_spring(math.radians(45.0), dt=0.1)
        self.assertAlmostEqual(angle, 0.0, delta=1e-3)

    def test_t2_f9_spring_fast_omega(self):
        motion_cls = get_procedural_motion_class()
        snappy = motion_cls(omega=16.0)
        for _ in range(60):
            snappy.update_gaze_spring(math.radians(45.0), dt=1.0/60.0)
        self.assertAlmostEqual(snappy.gaze_angle, math.radians(45.0), delta=0.12)

    def test_t2_f10_grim_zero_dimensions(self):
        cmd = self.service.build_grim_command(0, 0, 0, 0)
        self.assertEqual(cmd[2], "0,0 0x0")

    def test_t2_f10_grim_negative_coords(self):
        cmd = self.service.build_grim_command(-50, -100, 800, 600)
        self.assertEqual(cmd[2], "-50,-100 800x600")

    def test_t2_f10_dhash_uniform_grid_zero_hash(self):
        uniform = [[128 for _ in range(9)] for _ in range(8)]
        h = self.service.compute_dhash_from_grid(uniform)
        self.assertEqual(h, 0)

    def test_t2_f10_dhash_descending_grid_full_hash(self):
        desc = [[9 - c for c in range(9)] for _ in range(8)]
        h = self.service.compute_dhash_from_grid(desc)
        self.assertEqual(h, 0xFFFFFFFFFFFFFFFF)

    def test_t2_f10_hamming_none_hash_returns_max(self):
        dist = self.service.hamming_distance(None, 0x1234)
        self.assertEqual(dist, 64)

    def test_t2_f10_context_summary_empty_strings(self):
        summary = self.service.generate_context_summary("", "", "")
        self.assertEqual(summary["activity"], "")
        self.assertEqual(summary["active_tool"], "")

if __name__ == "__main__":
    unittest.main()

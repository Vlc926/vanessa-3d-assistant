import unittest
import numpy as np
from tests.test_doubles.loader import get_two_bone_ik_class, get_foot_lock_class

class TestF7TwoBoneIKFootLock(unittest.TestCase):
    def setUp(self):
        ik_cls = get_two_bone_ik_class()
        lock_cls = get_foot_lock_class()
        self.solver = ik_cls(l1=0.42, l2=0.40)
        self.lock = lock_cls(l1=0.42, l2=0.40, hip_rest_y=0.82)
        self.p_root = np.array([0.0, 0.82, 0.0])
        self.v_pole = np.array([0.0, 0.40, 1.0])

    def test_f7_analytical_ik_law_of_cosines_precision(self):
        target = np.array([0.1, 0.05, 0.05])
        _, _, p_ankle = self.solver.solve(self.p_root, target, self.v_pole)
        err = float(np.linalg.norm(p_ankle - target))
        self.assertLess(err, 1e-4)

    def test_f7_zero_foot_sliding_under_window_translation(self):
        win_pos = np.array([50.0, 100.0, 0.0])
        initial_foot = np.array([80.0, 100.0, 0.0])
        self.lock.plant_foot(initial_foot, win_pos)

        for step in range(120):
            win_pos[0] += 1.5
            win_pos[1] += 0.5
            current_world = self.lock.get_world_foot_pos(win_pos)
            slip = float(np.linalg.norm(current_world - (win_pos + self.lock.local_anchor)))
            self.assertEqual(slip, 0.0)

    def test_f7_singularity_avoidance_overextended_target(self):
        extreme_target = np.array([10.0, -20.0, 5.0])
        _, p_knee, p_ankle = self.solver.solve(self.p_root, extreme_target, self.v_pole)
        self.assertFalse(np.isnan(p_knee).any())
        self.assertFalse(np.isnan(p_ankle).any())
        dist = float(np.linalg.norm(p_ankle - self.p_root))
        self.assertAlmostEqual(dist, self.solver.total_len * 0.9999, delta=1e-3)

    def test_f7_hip_drop_pelvis_compensation(self):
        win_pos = np.array([0.0, 0.0, 0.0])
        self.lock.plant_foot([0.0, 0.0, 0.0], win_pos)
        initial_hip_y = self.lock.hip_pos[1]

        self.lock.update_hip_position(win_pos, pelvis_x=0.45)
        self.assertLess(self.lock.hip_pos[1], initial_hip_y)

    def test_f7_alternating_foot_stance_swing_phase(self):
        win_pos = np.array([0.0, 0.0, 0.0])
        self.lock.plant_foot([0.0, 0.0, 0.0], win_pos)
        self.assertEqual(self.lock.state, "STANCE")

        self.lock.update_hip_position(win_pos, pelvis_x=0.2)
        self.assertFalse(self.lock.check_liftoff(win_pos, step_distance_threshold=0.5))

        self.lock.update_hip_position(win_pos, pelvis_x=0.7)
        self.assertTrue(self.lock.check_liftoff(win_pos, step_distance_threshold=0.5))
        self.assertEqual(self.lock.state, "SWING")

    def test_f7_collinear_pole_fallback_stability(self):
        target = np.array([0.0, 0.1, 0.0])
        collinear_pole = np.array([0.0, 0.5, 0.0])
        _, p_knee, p_ankle = self.solver.solve(self.p_root, target, collinear_pole)
        self.assertFalse(np.isnan(p_knee).any())
        self.assertFalse(np.isnan(p_ankle).any())
        err = float(np.linalg.norm(p_ankle - target))
        self.assertLess(err, 1e-4)

if __name__ == "__main__":
    unittest.main()

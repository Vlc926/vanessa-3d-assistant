import unittest
import numpy as np
from tests.test_doubles.loader import get_two_bone_ik_class

class TestTwoBoneIKSolver(unittest.TestCase):
    def setUp(self):
        solver_cls = get_two_bone_ik_class()
        self.solver = solver_cls(l1=0.42, l2=0.40)
        self.p_root = np.array([0.0, 0.82, 0.0], dtype=np.float64)
        self.v_pole = np.array([0.0, 0.40, 1.0], dtype=np.float64)

    def test_reachable_targets_converge_accurately(self):
        test_targets = [
            np.array([0.0, 0.10, 0.20]),
            np.array([0.15, 0.05, 0.10]),
            np.array([-0.10, 0.25, 0.05]),
            np.array([0.0, 0.05, 0.0])
        ]
        for t in test_targets:
            p_root, p_knee, p_ankle = self.solver.solve(self.p_root, t, self.v_pole)
            err = float(np.linalg.norm(p_ankle - t))
            self.assertLess(err, 1e-4)

    def test_over_extended_target_no_nan_and_clamped(self):
        t_far = np.array([0.0, -10.0, 0.0])
        p_root, p_knee, p_ankle = self.solver.solve(self.p_root, t_far, self.v_pole)
        self.assertFalse(np.isnan(p_knee).any())
        self.assertFalse(np.isnan(p_ankle).any())
        dist = float(np.linalg.norm(p_ankle - self.p_root))
        max_reach = self.solver.total_len * 0.9999
        self.assertAlmostEqual(dist, max_reach, delta=1e-3)

    def test_collinear_pole_singularity_fallback(self):
        t = np.array([0.0, 0.10, 0.0])
        v_collinear = np.array([0.0, 0.50, 0.0])
        p_root, p_knee, p_ankle = self.solver.solve(self.p_root, t, v_collinear)
        self.assertFalse(np.isnan(p_knee).any())
        self.assertFalse(np.isnan(p_ankle).any())
        err = float(np.linalg.norm(p_ankle - t))
        self.assertLess(err, 1e-4)

    def test_target_at_root_origin_singularity(self):
        t_root = np.copy(self.p_root)
        p_root, p_knee, p_ankle = self.solver.solve(self.p_root, t_root, self.v_pole)
        self.assertFalse(np.isnan(p_knee).any())
        self.assertFalse(np.isnan(p_ankle).any())

    def test_bone_lengths_preservation(self):
        t = np.array([0.2, 0.15, 0.1])
        p_root, p_knee, p_ankle = self.solver.solve(self.p_root, t, self.v_pole)
        len1 = float(np.linalg.norm(p_knee - p_root))
        len2 = float(np.linalg.norm(p_ankle - p_knee))
        self.assertAlmostEqual(len1, self.solver.l1, delta=1e-3)
        self.assertAlmostEqual(len2, self.solver.l2, delta=1e-3)

if __name__ == "__main__":
    unittest.main()

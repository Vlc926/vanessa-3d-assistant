import math
import random
import unittest
from typing import List, Tuple
import numpy as np
from src.visual.two_bone_ik import TwoBoneIKSolver
from src.visual.foot_lock import FootLockController

class TestChallengerM21Stress(unittest.TestCase):
    def setUp(self) -> None:
        np.random.seed(42)
        random.seed(42)
        self.l1 = 0.42
        self.l2 = 0.40
        self.hip_rest_y = 0.82
        self.solver = TwoBoneIKSolver(l1=self.l1, l2=self.l2)
        self.controller = FootLockController(l1=self.l1, l2=self.l2, hip_rest_y=self.hip_rest_y)

    def test_stress_10000_targets_across_3d_sphere(self) -> None:
        total_points = 10000
        min_reach = abs(self.l1 - self.l2) + 1e-4
        max_reach = (self.l1 + self.l2) * 0.9999

        num_reachable = 6000
        num_overextended = 2000
        num_underextended = 1000
        num_boundary = 500
        num_singular = 500

        self.assertEqual(num_reachable + num_overextended + num_underextended + num_boundary + num_singular, total_points)

        roots = [
            np.array([0.0, 0.82, 0.0], dtype=np.float64),
            np.array([100.0, 200.0, 300.0], dtype=np.float64),
            np.array([-500.0, 1000.0, -250.0], dtype=np.float64),
            np.array([10000.0, -10000.0, 0.0], dtype=np.float64),
            np.array([0.0, 0.0, 0.0], dtype=np.float64),
        ]

        pole_variations = [
            np.array([0.0, 0.40, 1.0], dtype=np.float64),
            np.array([0.0, 0.0, 1.0], dtype=np.float64),
            np.array([1.0, 0.0, 0.0], dtype=np.float64),
            np.array([0.0, 1.0, 0.0], dtype=np.float64),
            np.array([0.0, 0.0, 0.0], dtype=np.float64),
        ]

        max_convergence_err = 0.0
        sum_convergence_err = 0.0
        max_len1_err = 0.0
        max_len2_err = 0.0

        for i in range(num_reachable):
            p_root = roots[i % len(roots)]
            v_dir = np.random.normal(size=3)
            norm_v = float(np.linalg.norm(v_dir))
            while norm_v < 1e-9:
                v_dir = np.random.normal(size=3)
                norm_v = float(np.linalg.norm(v_dir))
            u_dir = v_dir / norm_v

            dist = np.random.uniform(min_reach + 0.001, max_reach - 0.001)
            p_target = p_root + dist * u_dir

            if i % 10 == 0:
                v_pole = p_root + np.random.choice([-1.0, 1.0]) * np.random.uniform(0.1, 5.0) * u_dir
            elif i % 10 == 1:
                v_pole = np.copy(p_root)
            else:
                v_pole = p_root + pole_variations[i % len(pole_variations)]

            out_root, p_knee, p_ankle = self.solver.solve(p_root, p_target, v_pole)

            self.assertFalse(np.isnan(p_knee).any())
            self.assertFalse(np.isnan(p_ankle).any())
            self.assertFalse(np.isinf(p_knee).any())
            self.assertFalse(np.isinf(p_ankle).any())

            err = float(np.linalg.norm(p_ankle - p_target))
            self.assertLess(err, 1e-4)

            l1_meas = float(np.linalg.norm(p_knee - p_root))
            l2_meas = float(np.linalg.norm(p_ankle - p_knee))
            err_l1 = abs(l1_meas - self.l1)
            err_l2 = abs(l2_meas - self.l2)

            self.assertLess(err_l1, 1e-4)
            self.assertLess(err_l2, 1e-4)

            if err > max_convergence_err:
                max_convergence_err = err
            sum_convergence_err += err
            if err_l1 > max_len1_err:
                max_len1_err = err_l1
            if err_l2 > max_len2_err:
                max_len2_err = err_l2

        for i in range(num_overextended):
            p_root = roots[i % len(roots)]
            v_dir = np.random.normal(size=3)
            norm_v = float(np.linalg.norm(v_dir))
            while norm_v < 1e-9:
                v_dir = np.random.normal(size=3)
                norm_v = float(np.linalg.norm(v_dir))
            u_dir = v_dir / norm_v

            dist = np.random.uniform(max_reach + 0.01, 100.0)
            p_target = p_root + dist * u_dir
            v_pole = p_root + pole_variations[i % len(pole_variations)]

            out_root, p_knee, p_ankle = self.solver.solve(p_root, p_target, v_pole)

            self.assertFalse(np.isnan(p_knee).any())
            self.assertFalse(np.isnan(p_ankle).any())
            self.assertFalse(np.isinf(p_knee).any())
            self.assertFalse(np.isinf(p_ankle).any())

            d_ankle = float(np.linalg.norm(p_ankle - p_root))
            self.assertAlmostEqual(d_ankle, max_reach, delta=1e-3)

            u_ankle = (p_ankle - p_root) / d_ankle
            cos_align = float(np.dot(u_ankle, u_dir))
            self.assertGreater(cos_align, 0.9999)

            err_l1 = abs(float(np.linalg.norm(p_knee - p_root)) - self.l1)
            err_l2 = abs(float(np.linalg.norm(p_ankle - p_knee)) - self.l2)
            self.assertLess(err_l1, 1e-4)
            self.assertLess(err_l2, 1e-4)

        for i in range(num_underextended):
            p_root = roots[i % len(roots)]
            v_dir = np.random.normal(size=3)
            norm_v = float(np.linalg.norm(v_dir))
            while norm_v < 1e-9:
                v_dir = np.random.normal(size=3)
                norm_v = float(np.linalg.norm(v_dir))
            u_dir = v_dir / norm_v

            dist = np.random.uniform(1e-5, min_reach - 1e-5)
            p_target = p_root + dist * u_dir
            v_pole = p_root + pole_variations[i % len(pole_variations)]

            out_root, p_knee, p_ankle = self.solver.solve(p_root, p_target, v_pole)

            self.assertFalse(np.isnan(p_knee).any())
            self.assertFalse(np.isnan(p_ankle).any())
            self.assertFalse(np.isinf(p_knee).any())
            self.assertFalse(np.isinf(p_ankle).any())

            d_ankle = float(np.linalg.norm(p_ankle - p_root))
            self.assertAlmostEqual(d_ankle, min_reach, delta=1e-3)

            err_l1 = abs(float(np.linalg.norm(p_knee - p_root)) - self.l1)
            err_l2 = abs(float(np.linalg.norm(p_ankle - p_knee)) - self.l2)
            self.assertLess(err_l1, 1e-4)
            self.assertLess(err_l2, 1e-4)

        for i in range(num_boundary):
            p_root = roots[i % len(roots)]
            v_dir = np.random.normal(size=3)
            u_dir = v_dir / float(np.linalg.norm(v_dir))
            boundary_dist = [
                min_reach,
                min_reach - 1e-6,
                min_reach + 1e-6,
                max_reach,
                max_reach - 1e-6,
                max_reach + 1e-6,
                self.l1 + self.l2
            ][i % 7]
            p_target = p_root + boundary_dist * u_dir
            v_pole = p_root + pole_variations[i % len(pole_variations)]

            out_root, p_knee, p_ankle = self.solver.solve(p_root, p_target, v_pole)

            self.assertFalse(np.isnan(p_knee).any())
            self.assertFalse(np.isnan(p_ankle).any())
            err_l1 = abs(float(np.linalg.norm(p_knee - p_root)) - self.l1)
            err_l2 = abs(float(np.linalg.norm(p_ankle - p_knee)) - self.l2)
            self.assertLess(err_l1, 1e-4)
            self.assertLess(err_l2, 1e-4)

        for i in range(num_singular):
            p_root = roots[i % len(roots)]
            if i % 2 == 0:
                p_target = np.copy(p_root)
            else:
                p_target = p_root + np.random.uniform(1e-12, 1e-7, size=3)
            v_pole = p_root + pole_variations[i % len(pole_variations)]

            out_root, p_knee, p_ankle = self.solver.solve(p_root, p_target, v_pole)

            self.assertFalse(np.isnan(p_knee).any())
            self.assertFalse(np.isnan(p_ankle).any())
            self.assertEqual(out_root.shape, (3,))
            self.assertEqual(p_knee.shape, (3,))
            self.assertEqual(p_ankle.shape, (3,))

    def test_stress_foot_locking_translating_window_velocity_sweeps_1000_frames(self) -> None:
        win_pos = np.array([200.0, 150.0, 0.0], dtype=np.float64)
        initial_foot = np.array([245.0, 150.0, 0.0], dtype=np.float64)
        self.controller.plant_foot(initial_foot, win_pos)
        self.assertEqual(self.controller.state, "STANCE")

        expected_local_anchor = initial_foot - win_pos
        self.assertTrue(np.allclose(self.controller.local_anchor, expected_local_anchor))

        dt = 1.0 / 60.0
        prev_world_foot = self.controller.get_world_foot_pos(win_pos)
        prev_win_pos = np.copy(win_pos)

        total_frames = 1000
        for frame in range(total_frames):
            t = float(frame) * dt

            vx = 25.0 * math.sin(0.08 * float(frame)) + 12.0 * math.cos(0.25 * float(frame))
            vy = 18.0 * math.cos(0.05 * float(frame)) - 8.0 * math.sin(0.15 * float(frame))
            vz = 6.0 * math.sin(0.12 * float(frame))

            if frame in [200, 450, 700, 850]:
                vx += 50.0
                vy -= 30.0
                vz += 15.0

            jitter = (np.random.rand(3) - 0.5) * 0.1

            step_disp = np.array([vx, vy, vz], dtype=np.float64) * dt + jitter
            win_pos += step_disp

            cur_world_foot = self.controller.get_world_foot_pos(win_pos)

            reconstructed_local = cur_world_foot - win_pos
            local_slip = float(np.linalg.norm(reconstructed_local - self.controller.local_anchor))
            self.assertLess(local_slip, 1e-12)

            delta_foot = cur_world_foot - prev_world_foot
            delta_win = win_pos - prev_win_pos
            frame_slip = float(np.linalg.norm(delta_foot - delta_win))
            self.assertLess(frame_slip, 1e-12)

            self.assertEqual(self.controller.state, "STANCE")

            prev_world_foot = np.copy(cur_world_foot)
            prev_win_pos = np.copy(win_pos)

    def test_edge_cases_singularities_and_large_dt(self) -> None:
        p_root = np.array([0.0, 0.82, 0.0], dtype=np.float64)

        for axis in [
            np.array([1.0, 0.0, 0.0]),
            np.array([-1.0, 0.0, 0.0]),
            np.array([0.0, 1.0, 0.0]),
            np.array([0.0, -1.0, 0.0]),
            np.array([0.0, 0.0, 1.0]),
            np.array([0.0, 0.0, -1.0]),
        ]:
            p_target = p_root + 0.45 * axis
            for alpha in [-5.0, -1.0, -0.1, 0.1, 1.0, 5.0]:
                v_collinear = p_root + alpha * axis
                _, p_knee, p_ankle = self.solver.solve(p_root, p_target, v_collinear)
                err = float(np.linalg.norm(p_ankle - p_target))
                self.assertLess(err, 1e-4)
                self.assertFalse(np.isnan(p_knee).any())
                self.assertFalse(np.isnan(p_ankle).any())

        for axis in [np.array([0.0, 0.0, 1.0]), np.array([0.0, 0.0, -1.0])]:
            p_target = p_root + 0.40 * axis
            v_zero_relative = np.copy(p_root)
            _, p_knee, p_ankle = self.solver.solve(p_root, p_target, v_zero_relative)
            err = float(np.linalg.norm(p_ankle - p_target))
            self.assertLess(err, 1e-4)

        origin_p_root = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        _, p_knee, p_ankle = self.solver.solve(origin_p_root, origin_p_root, origin_p_root)
        self.assertFalse(np.isnan(p_knee).any())
        self.assertFalse(np.isnan(p_ankle).any())

        w_pos = np.array([10.0, 20.0, 0.0])
        self.controller.plant_foot([10.0, 20.0, 0.0], w_pos)

        for test_dt in [1e-6, 1.0, 10.0, 1000.0, 1e6, 0.0, -5.0]:
            hip = self.controller.update_hip_position(w_pos, pelvis_x=10.0, dt=test_dt)
            self.assertFalse(np.isnan(hip).any())
            self.assertFalse(np.isinf(hip).any())
            self.assertGreaterEqual(hip[1], self.hip_rest_y - 0.35 - 1e-6)

        hip_overextended = self.controller.update_hip_position(w_pos, pelvis_x=1000.0, dt=1.0)
        self.assertGreaterEqual(hip_overextended[1], self.hip_rest_y - 0.35 - 1e-6)

        self.controller.plant_foot([10.0, 20.0, 0.0], w_pos)
        self.controller.update_hip_position(w_pos, pelvis_x=10.0)
        self.assertFalse(self.controller.check_liftoff(w_pos, step_distance_threshold=0.50))
        self.assertEqual(self.controller.state, "STANCE")

        self.controller.update_hip_position(w_pos, pelvis_x=10.51)
        self.assertTrue(self.controller.check_liftoff(w_pos, step_distance_threshold=0.50))
        self.assertEqual(self.controller.state, "SWING")

        self.controller.plant_foot([10.51, 20.0, 0.0], w_pos)
        self.assertEqual(self.controller.state, "STANCE")
        self.assertFalse(self.controller.check_liftoff(w_pos, step_distance_threshold=0.50))

    def test_coupled_locomotion_1000_frames(self) -> None:
        win_pos = np.array([50.0, 100.0, 0.0], dtype=np.float64)
        pelvis_x = 50.0
        self.controller.plant_foot([pelvis_x, 100.0, 0.0], win_pos)
        pole_vec = np.array([0.0, 0.0, 1.0], dtype=np.float64)

        for frame in range(1000):
            win_pos[0] += 0.8 * math.sin(0.02 * float(frame))
            win_pos[1] += 0.4 * math.cos(0.03 * float(frame))
            pelvis_x += 0.01

            hip_pos = self.controller.update_hip_position(win_pos, pelvis_x=pelvis_x, dt=1.0 / 60.0)
            foot_pos = self.controller.get_world_foot_pos(win_pos)

            slip = float(np.linalg.norm(foot_pos - win_pos - self.controller.local_anchor))
            self.assertEqual(slip, 0.0)

            out_root, knee, ankle = self.solver.solve(hip_pos, foot_pos, hip_pos + pole_vec)

            self.assertFalse(np.isnan(knee).any())
            self.assertFalse(np.isnan(ankle).any())

            if self.controller.check_liftoff(win_pos, step_distance_threshold=0.40):
                new_foot = np.array([pelvis_x, win_pos[1], 0.0], dtype=np.float64)
                self.controller.plant_foot(new_foot, win_pos)

if __name__ == "__main__":
    unittest.main()

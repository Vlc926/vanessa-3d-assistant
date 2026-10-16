import unittest
import numpy as np
from tests.test_doubles.loader import get_two_bone_ik_class, get_foot_lock_class, get_ledge_physics_class

class TestT2F7F8Boundary(unittest.TestCase):
    def setUp(self):
        ik_cls = get_two_bone_ik_class()
        lock_cls = get_foot_lock_class()
        physics_cls = get_ledge_physics_class()
        self.solver = ik_cls(l1=0.42, l2=0.40)
        self.lock = lock_cls(l1=0.42, l2=0.40, hip_rest_y=0.82)
        self.physics = physics_cls(gravity=-18.5, terminal_velocity=35.0)

    def test_t2_f7_target_identical_to_root(self):
        p_root = np.array([0.0, 1.0, 0.0])
        p0, p1, p2 = self.solver.solve(p_root, p_root, [0.0, 0.0, 1.0])
        self.assertFalse(np.isnan(p1).any())
        self.assertFalse(np.isnan(p2).any())

    def test_t2_f7_huge_negative_y_distance(self):
        p_root = np.array([0.0, 0.0, 0.0])
        target = np.array([0.0, -1000.0, 0.0])
        _, p1, p2 = self.solver.solve(p_root, target, [0.0, 0.0, 1.0])
        dist = float(np.linalg.norm(p2 - p_root))
        self.assertAlmostEqual(dist, self.solver.total_len * 0.9999, delta=1e-3)

    def test_t2_f7_zero_pole_vector(self):
        p_root = np.array([0.0, 0.8, 0.0])
        target = np.array([0.1, 0.1, 0.1])
        _, p1, p2 = self.solver.solve(p_root, target, [0.0, 0.0, 0.0])
        self.assertFalse(np.isnan(p1).any())
        self.assertFalse(np.isnan(p2).any())

    def test_t2_f7_large_dt_hip_drop_clamping(self):
        win_pos = [0.0, 0.0, 0.0]
        self.lock.plant_foot([0.0, 0.0, 0.0], win_pos)
        hip = self.lock.update_hip_position(win_pos, pelvis_x=0.5, dt=5.0)
        self.assertFalse(np.isnan(hip).any())
        self.assertGreater(hip[1], 0.0)

    def test_t2_f7_extreme_negative_anchor_plant(self):
        self.lock.plant_foot([-1000.0, -2000.0, 0.0], [0.0, 0.0, 0.0])
        world_foot = self.lock.get_world_foot_pos([10.0, 20.0, 0.0])
        self.assertEqual(world_foot[0], -990.0)
        self.assertEqual(world_foot[1], -1980.0)

    def test_t2_f8_extremely_high_gravity_step(self):
        physics_cls = get_ledge_physics_class()
        heavy_gravity = physics_cls(gravity=-500.0, terminal_velocity=100.0)
        heavy_gravity.pos = np.array([0.0, 1000.0, 0.0])
        heavy_gravity.state = "FREE_FALL"
        heavy_gravity.step(1.0, [])
        self.assertEqual(heavy_gravity.vel[1], -100.0)

    def test_t2_f8_micro_dt_integration(self):
        self.physics.pos = np.array([0.0, 50.0, 0.0])
        self.physics.state = "FREE_FALL"
        self.physics.step(1e-6, [])
        self.assertAlmostEqual(self.physics.pos[1], 50.0, delta=1e-5)

    def test_t2_f8_instantaneous_window_deletion_triggers_imbalance(self):
        platforms = [{"x_min": -1.0, "x_max": 1.0, "y_top": 2.0}]
        self.physics.pos = np.array([0.0, 2.0, 0.0])
        self.physics.state = "GROUNDED"
        self.physics.step(1.0/60.0, platforms)
        self.assertEqual(self.physics.state, "GROUNDED")

        self.physics.step(1.0/60.0, [])
        self.assertEqual(self.physics.state, "IMBALANCE")

    def test_t2_f8_swept_ccd_zero_thickness_platform(self):
        platforms = [{"x_min": -10.0, "x_max": 10.0, "y_top": 5.0}]
        self.physics.pos = np.array([0.0, 6.0, 0.0])
        self.physics.vel = np.array([0.0, -20.0, 0.0])
        self.physics.state = "FREE_FALL"
        self.physics.step(0.1, platforms)
        self.assertEqual(self.physics.pos[1], 5.0)

    def test_t2_f8_landing_critical_speed_threshold(self):
        platforms = [{"x_min": -10.0, "x_max": 10.0, "y_top": 0.0}]
        self.physics.pos = np.array([0.0, 1.0, 0.0])
        self.physics.vel = np.array([0.0, -8.0, 0.0])
        self.physics.state = "FREE_FALL"
        self.physics.step(0.15, platforms)
        self.assertEqual(self.physics.state, "LANDING")
        self.assertGreaterEqual(self.physics.landing_impact_speed, 8.0)

    def test_t2_f8_terminal_velocity_downward_launch(self):
        self.physics.pos = np.array([0.0, 1000.0, 0.0])
        self.physics.vel = np.array([0.0, -100.0, 0.0])
        self.physics.state = "FREE_FALL"
        self.physics.step(0.01, [])
        self.assertEqual(self.physics.vel[1], -self.physics.terminal_velocity)

if __name__ == "__main__":
    unittest.main()

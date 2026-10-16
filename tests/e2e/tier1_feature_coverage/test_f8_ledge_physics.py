import unittest
import numpy as np
from tests.test_doubles.loader import get_ledge_physics_class

class TestF8LedgePhysics(unittest.TestCase):
    def setUp(self):
        physics_cls = get_ledge_physics_class()
        self.engine = physics_cls(gravity=-18.5, terminal_velocity=35.0, imbalance_duration=0.45)

    def test_f8_grounded_surface_detection(self):
        platforms = [{"x_min": 0.0, "x_max": 2.0, "y_top": 1.5}]
        self.engine.pos = np.array([1.0, 1.5, 0.0])
        self.engine.state = "GROUNDED"
        self.engine.step(1.0 / 60.0, platforms)
        self.assertEqual(self.engine.state, "GROUNDED")

    def test_f8_loss_of_support_imbalance_state(self):
        platforms = [{"x_min": 0.0, "x_max": 1.0, "y_top": 1.5}]
        self.engine.pos = np.array([1.5, 1.5, 0.0])
        self.engine.state = "GROUNDED"
        self.engine.step(1.0 / 60.0, platforms)
        self.assertEqual(self.engine.state, "IMBALANCE")

    def test_f8_imbalance_recovery_window(self):
        platforms = [{"x_min": 0.0, "x_max": 1.0, "y_top": 1.5}]
        self.engine.pos = np.array([1.02, 1.5, 0.0])
        self.engine.state = "IMBALANCE"
        self.engine.imbalance_timer = 0.30

        self.engine.pos[0] = 0.8
        self.engine.step(1.0 / 60.0, platforms)
        self.assertEqual(self.engine.state, "GROUNDED")

    def test_f8_free_fall_gravity_trajectory(self):
        platforms = []
        self.engine.pos = np.array([0.0, 1000.0, 0.0])
        self.engine.vel = np.array([0.0, 0.0, 0.0])
        self.engine.state = "FREE_FALL"

        dt = 1.0 / 60.0
        for _ in range(30):
            self.engine.step(dt, platforms)

        t = 30 * dt
        expected_y = 1000.0 + 0.5 * (-18.5) * (t ** 2)
        self.assertAlmostEqual(self.engine.pos[1], expected_y, delta=0.5)

    def test_f8_swept_ccd_collision_landing(self):
        platforms = [{"x_min": -5.0, "x_max": 5.0, "y_top": 2.0}]
        self.engine.pos = np.array([0.0, 2.5, 0.0])
        self.engine.vel = np.array([0.0, -15.0, 0.0])
        self.engine.state = "FREE_FALL"

        self.engine.step(0.1, platforms)
        self.assertIn(self.engine.state, ("LANDING", "GROUNDED"))
        self.assertEqual(self.engine.pos[1], 2.0)

    def test_f8_heavy_landing_crouch_duration(self):
        platforms = [{"x_min": -5.0, "x_max": 5.0, "y_top": 0.0}]
        self.engine.pos = np.array([0.0, 50.0, 0.0])
        self.engine.vel = np.array([0.0, 0.0, 0.0])
        self.engine.state = "FREE_FALL"

        while self.engine.state == "FREE_FALL":
            self.engine.step(1.0 / 60.0, platforms)

        self.assertEqual(self.engine.state, "LANDING")
        self.assertGreater(self.engine.crouch_timer, 0.0)

        self.engine.step(0.40, platforms)
        self.assertEqual(self.engine.state, "GROUNDED")

if __name__ == "__main__":
    unittest.main()

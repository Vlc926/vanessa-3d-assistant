import unittest
import numpy as np
from tests.test_doubles.loader import get_ledge_physics_class

class TestLedgePhysics(unittest.TestCase):
    def setUp(self):
        physics_cls = get_ledge_physics_class()
        self.engine = physics_cls(gravity=-18.5, terminal_velocity=35.0, imbalance_duration=0.45)

    def test_grounded_remains_on_platform(self):
        platforms = [{"x_min": -1.0, "x_max": 1.0, "y_top": 0.5}]
        self.engine.pos = np.array([0.0, 0.5, 0.0])
        self.engine.state = "GROUNDED"

        self.engine.step(1.0 / 60.0, platforms)
        self.assertEqual(self.engine.state, "GROUNDED")
        self.assertEqual(self.engine.pos[1], 0.5)

    def test_loss_of_support_triggers_imbalance(self):
        platforms = [{"x_min": -1.0, "x_max": -0.5, "y_top": 0.5}]
        self.engine.pos = np.array([0.0, 0.5, 0.0])
        self.engine.state = "GROUNDED"

        self.engine.step(1.0 / 60.0, platforms)
        self.assertEqual(self.engine.state, "IMBALANCE")
        self.assertAlmostEqual(self.engine.imbalance_timer, 0.45, delta=0.02)

    def test_imbalance_countdown_to_free_fall(self):
        platforms = []
        self.engine.pos = np.array([0.0, 1.0, 0.0])
        self.engine.state = "IMBALANCE"
        self.engine.imbalance_timer = 0.05

        self.engine.step(0.06, platforms)
        self.assertEqual(self.engine.state, "FREE_FALL")

    def test_free_fall_gravity_acceleration_and_terminal_velocity(self):
        platforms = []
        self.engine.pos = np.array([0.0, 1000.0, 0.0])
        self.engine.vel = np.array([0.0, 0.0, 0.0])
        self.engine.state = "FREE_FALL"

        dt = 0.1
        for _ in range(50):
            self.engine.step(dt, platforms)

        self.assertEqual(self.engine.vel[1], -self.engine.terminal_velocity)

    def test_swept_collision_detection_and_heavy_landing(self):
        platforms = [{"x_min": -2.0, "x_max": 2.0, "y_top": 1.0}]
        self.engine.pos = np.array([0.0, 10.0, 0.0])
        self.engine.vel = np.array([0.0, 0.0, 0.0])
        self.engine.state = "FREE_FALL"

        while self.engine.state == "FREE_FALL":
            self.engine.step(1.0 / 60.0, platforms)

        self.assertIn(self.engine.state, ("LANDING", "GROUNDED"))
        self.assertEqual(self.engine.pos[1], 1.0)
        self.assertGreater(self.engine.landing_impact_speed, 8.0)

if __name__ == "__main__":
    unittest.main()

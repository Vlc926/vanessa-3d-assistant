import unittest
import numpy as np
from tests.test_doubles.loader import get_foot_lock_class

class TestFootLocking(unittest.TestCase):
    def setUp(self):
        controller_cls = get_foot_lock_class()
        self.controller = controller_cls(l1=0.42, l2=0.40, hip_rest_y=0.82)

    def test_zero_sliding_on_moving_window(self):
        win_pos = np.array([100.0, 200.0, 0.0])
        initial_foot = np.array([150.0, 200.0, 0.0])
        self.controller.plant_foot(initial_foot, win_pos)
        self.assertEqual(self.controller.state, "STANCE")

        for frame in range(60):
            win_pos[0] += 3.5
            win_pos[1] -= 1.2
            world_foot = self.controller.get_world_foot_pos(win_pos)
            reconstructed_local = world_foot - win_pos
            slip = float(np.linalg.norm(reconstructed_local - self.controller.local_anchor))
            self.assertEqual(slip, 0.0)

    def test_hip_drop_compensation(self):
        win_pos = np.array([0.0, 0.0, 0.0])
        initial_foot = np.array([0.0, 0.0, 0.0])
        self.controller.plant_foot(initial_foot, win_pos)

        rest_hip_y = self.controller.hip_pos[1]
        for step in range(30):
            pelvis_x = float(step) * 0.03
            self.controller.update_hip_position(win_pos, pelvis_x)

        self.assertLess(self.controller.hip_pos[1], rest_hip_y)

    def test_liftoff_threshold_trigger(self):
        win_pos = np.array([0.0, 0.0, 0.0])
        initial_foot = np.array([0.0, 0.0, 0.0])
        self.controller.plant_foot(initial_foot, win_pos)
        self.assertEqual(self.controller.state, "STANCE")

        self.controller.update_hip_position(win_pos, pelvis_x=0.2)
        lifted = self.controller.check_liftoff(win_pos, step_distance_threshold=0.50)
        self.assertFalse(lifted)
        self.assertEqual(self.controller.state, "STANCE")

        self.controller.update_hip_position(win_pos, pelvis_x=0.6)
        lifted = self.controller.check_liftoff(win_pos, step_distance_threshold=0.50)
        self.assertTrue(lifted)
        self.assertEqual(self.controller.state, "SWING")

    def test_plant_foot_resets_state(self):
        self.controller.state = "SWING"
        self.controller.plant_foot([10.0, 20.0, 0.0], [5.0, 10.0, 0.0])
        self.assertEqual(self.controller.state, "STANCE")
        self.assertEqual(list(self.controller.local_anchor), [5.0, 10.0, 0.0])

if __name__ == "__main__":
    unittest.main()

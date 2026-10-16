import unittest
from tests.test_doubles.loader import get_actuator_class

class TestF4PhysicalActuator(unittest.TestCase):
    def setUp(self):
        actuator_cls = get_actuator_class()
        self.actuator = actuator_cls(execute_real=False)

    def test_f4_push_window_pixel_dispatch(self):
        res = self.actuator.push_window("0x5616a03008b0", 25, 10)
        self.assertEqual(res["status"], "ok")
        self.assertIn("movewindowpixel", res["executed"])
        self.assertIn("25 10,address:0x5616a03008b0", res["executed"])

    def test_f4_resize_window_pixel_dispatch(self):
        res = self.actuator.resize_window("0x5616a03008b0", -50, 0)
        self.assertEqual(res["status"], "ok")
        self.assertIn("resizewindowpixel", res["executed"])
        self.assertIn("-50 0,address:0x5616a03008b0", res["executed"])

    def test_f4_ydotool_mousemove_absolute(self):
        res = self.actuator.inject_pointer_move(640, 480, absolute=True)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["event"]["x"], 640)
        self.assertEqual(res["event"]["y"], 480)

    def test_f4_ydotool_click_left_masks(self):
        res1 = self.actuator.inject_pointer_click(0xC0)
        res2 = self.actuator.inject_pointer_click(0x40)
        res3 = self.actuator.inject_pointer_click(0x80)
        self.assertEqual(res1["event"]["button"], 0xC0)
        self.assertEqual(res2["event"]["button"], 0x40)
        self.assertEqual(res3["event"]["button"], 0x80)

    def test_f4_impulse_physics_displacement(self):
        d_light = self.actuator.compute_push_displacement(5.0, avatar_mass=1.0, friction=0.1)
        d_heavy = self.actuator.compute_push_displacement(15.0, avatar_mass=1.0, friction=0.1)
        self.assertGreater(d_heavy, d_light)

    def test_f4_zero_mass_protection(self):
        d_zero = self.actuator.compute_push_displacement(10.0, avatar_mass=0.0)
        self.assertEqual(d_zero, 0.0)

if __name__ == "__main__":
    unittest.main()

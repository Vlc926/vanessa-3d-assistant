import unittest
from tests.test_doubles.loader import get_actuator_class

class TestActuator(unittest.TestCase):
    def setUp(self):
        actuator_cls = get_actuator_class()
        self.actuator = actuator_cls(execute_real=False)

    def test_push_window_dispatch_formatting(self):
        res = self.actuator.push_window("0x5616a03008b0", 50, -20)
        self.assertEqual(res["status"], "ok")
        self.assertEqual(len(self.actuator.recorded_dispatches), 1)
        disp = self.actuator.recorded_dispatches[0]
        self.assertEqual(disp["cmd"], "movewindowpixel")
        self.assertEqual(disp["args"], "50 -20,address:0x5616a03008b0")

    def test_resize_window_dispatch_formatting(self):
        res = self.actuator.resize_window("0x5616a03008b0", 100, 50)
        self.assertEqual(res["status"], "ok")
        disp = self.actuator.recorded_dispatches[-1]
        self.assertEqual(disp["cmd"], "resizewindowpixel")
        self.assertEqual(disp["args"], "100 50,address:0x5616a03008b0")

    def test_pointer_movement_injection(self):
        res = self.actuator.inject_pointer_move(350, 420, absolute=True)
        self.assertEqual(res["status"], "ok")
        ev = self.actuator.recorded_pointer_events[-1]
        self.assertEqual(ev["action"], "mousemove")
        self.assertEqual(ev["x"], 350)
        self.assertEqual(ev["y"], 420)
        self.assertTrue(ev["absolute"])

    def test_pointer_click_injection_button_codes(self):
        self.actuator.inject_pointer_click(0xC0)
        self.actuator.inject_pointer_click(0x40)
        self.actuator.inject_pointer_click(0x80)
        self.assertEqual(len(self.actuator.recorded_pointer_events), 3)
        self.assertEqual(self.actuator.recorded_pointer_events[0]["button"], 0xC0)
        self.assertEqual(self.actuator.recorded_pointer_events[1]["button"], 0x40)
        self.assertEqual(self.actuator.recorded_pointer_events[2]["button"], 0x80)

    def test_push_displacement_physics_calculation(self):
        d1 = self.actuator.compute_push_displacement(impulse_force=10.0, avatar_mass=1.0, friction=0.2)
        d2 = self.actuator.compute_push_displacement(impulse_force=10.0, avatar_mass=2.0, friction=0.2)
        self.assertEqual(d1, 8.0)
        self.assertEqual(d2, 4.0)

if __name__ == "__main__":
    unittest.main()

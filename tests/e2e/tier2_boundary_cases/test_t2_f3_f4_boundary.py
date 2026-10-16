import unittest
from tests.test_doubles.loader import get_geometry_projector_class, get_actuator_class

class TestT2F3F4Boundary(unittest.TestCase):
    def setUp(self):
        projector_cls = get_geometry_projector_class()
        actuator_cls = get_actuator_class()
        self.projector = projector_cls(screen_w=1920, screen_h=1200)
        self.actuator = actuator_cls(execute_real=False)

    def test_t2_f3_zero_size_window_projection(self):
        client = {"address": "0xzero", "at": [100, 100], "size": [0, 0]}
        res = self.projector.project_client(client)
        self.assertIn("planes", res)
        top = next(p for p in res["planes"] if p["type"] == "window_top")
        self.assertEqual(top["bounds"][0], top["bounds"][1])

    def test_t2_f3_negative_pixel_coordinates(self):
        p3d = self.projector.pixel_to_3d(-500, -200)
        self.assertLess(p3d[0], -self.projector.w3d / 2.0)
        self.assertGreater(p3d[1], self.projector.h3d / 2.0)

    def test_t2_f3_extreme_4k_coordinates(self):
        p3d = self.projector.pixel_to_3d(3840, 2160)
        self.assertGreater(p3d[0], self.projector.w3d / 2.0)
        self.assertLess(p3d[1], -self.projector.h3d / 2.0)

    def test_t2_f3_degenerate_aspect_ratio_window(self):
        client = {"address": "0xthin", "at": [100, 100], "size": [1, 1000]}
        res = self.projector.project_client(client)
        top = next(p for p in res["planes"] if p["type"] == "window_top")
        self.assertAlmostEqual(top["bounds"][1] - top["bounds"][0], 0.0, delta=0.01)

    def test_t2_f3_fov_variation_scaling(self):
        projector_cls = get_geometry_projector_class()
        proj_narrow = projector_cls(fov_deg=10.0)
        proj_wide = projector_cls(fov_deg=90.0)
        self.assertLess(proj_narrow.w3d, proj_wide.w3d)

    def test_t2_f3_top_ledge_bounds_ordering_invariant(self):
        client = {"address": "0xinv", "at": [500, 400], "size": [200, 300]}
        res = self.projector.project_client(client)
        start_x = res["top_ledge"]["start"][0]
        end_x = res["top_ledge"]["end"][0]
        self.assertLess(start_x, end_x)

    def test_t2_f4_zero_delta_push_window(self):
        res = self.actuator.push_window("0x1", 0, 0)
        self.assertEqual(res["status"], "ok")
        self.assertIn("0 0,address:0x1", res["executed"])

    def test_t2_f4_negative_delta_push_window(self):
        res = self.actuator.push_window("0x1", -500, -250)
        self.assertEqual(res["status"], "ok")
        self.assertIn("-500 -250,address:0x1", res["executed"])

    def test_t2_f4_large_delta_resize_window(self):
        res = self.actuator.resize_window("0x1", 5000, 5000)
        self.assertEqual(res["status"], "ok")
        self.assertIn("5000 5000,address:0x1", res["executed"])

    def test_t2_f4_custom_button_code_injection(self):
        res = self.actuator.inject_pointer_click(0xAA)
        self.assertEqual(res["event"]["button"], 0xAA)

    def test_t2_f4_impulse_with_total_friction(self):
        disp = self.actuator.compute_push_displacement(100.0, avatar_mass=1.0, friction=1.0)
        self.assertEqual(disp, 0.0)

    def test_t2_f4_impulse_with_negative_mass(self):
        disp = self.actuator.compute_push_displacement(10.0, avatar_mass=-1.0)
        self.assertEqual(disp, 0.0)

if __name__ == "__main__":
    unittest.main()

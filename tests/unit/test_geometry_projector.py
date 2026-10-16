import unittest
from tests.test_doubles.loader import get_geometry_projector_class

class TestGeometryProjector(unittest.TestCase):
    def setUp(self):
        projector_cls = get_geometry_projector_class()
        self.projector = projector_cls(screen_w=1920, screen_h=1200, fov_deg=30.0, z_ref=2.8)

    def test_center_screen_projection_is_origin(self):
        p3d = self.projector.pixel_to_3d(960, 600, z_depth=0.0)
        self.assertAlmostEqual(p3d[0], 0.0, delta=0.01)
        self.assertAlmostEqual(p3d[1], 0.0, delta=0.01)

    def test_roundtrip_coordinate_transformation(self):
        test_pixels = [(100, 150), (960, 600), (1800, 1100), (0, 0)]
        for px, py in test_pixels:
            p3d = self.projector.pixel_to_3d(px, py)
            r_px, r_py = self.projector.point_3d_to_pixel(p3d[0], p3d[1])
            self.assertAlmostEqual(px, r_px, delta=2)
            self.assertAlmostEqual(py, r_py, delta=2)

    def test_z_depth_hierarchy(self):
        tiled_inactive = {"floating": False, "focusHistoryID": 1}
        tiled_active = {"floating": False, "focusHistoryID": 0}
        floating_inactive = {"floating": True, "focusHistoryID": 2}
        floating_active = {"floating": True, "focusHistoryID": 0}

        z_ti = self.projector.calculate_z_depth(tiled_inactive, is_active=False)
        z_ta = self.projector.calculate_z_depth(tiled_active, is_active=True)
        z_fi = self.projector.calculate_z_depth(floating_inactive, is_active=False)
        z_fa = self.projector.calculate_z_depth(floating_active, is_active=True)

        self.assertEqual(z_ti, 0.0)
        self.assertEqual(z_ta, 0.08)
        self.assertGreater(z_fi, z_ti)
        self.assertGreater(z_fa, z_fi)

    def test_top_ledge_segment_extraction(self):
        client = {
            "address": "0x5616a03008b0",
            "at": [100, 150],
            "size": [800, 600],
            "floating": False,
            "focusHistoryID": 0
        }
        res = self.projector.project_client(client, is_active=True)
        top_ledge = res["top_ledge"]
        self.assertIn("start", top_ledge)
        self.assertIn("end", top_ledge)
        self.assertAlmostEqual(top_ledge["start"][1], top_ledge["end"][1], delta=1e-3)
        self.assertLess(top_ledge["start"][0], top_ledge["end"][0])

    def test_collision_planes_generated(self):
        client = {
            "address": "0x5616a03008b0",
            "at": [200, 200],
            "size": [500, 400],
            "floating": True
        }
        res = self.projector.project_client(client)
        planes = res["planes"]
        types = [p["type"] for p in planes]
        self.assertIn("window_top", types)
        self.assertIn("window_border_left", types)
        self.assertIn("window_border_right", types)
        self.assertIn("window_scrollbar", types)

if __name__ == "__main__":
    unittest.main()

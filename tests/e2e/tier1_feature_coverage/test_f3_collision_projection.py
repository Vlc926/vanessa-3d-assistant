import unittest
from tests.test_doubles.loader import get_geometry_projector_class

class TestF3CollisionProjection(unittest.TestCase):
    def setUp(self):
        projector_cls = get_geometry_projector_class()
        self.projector = projector_cls(screen_w=1920, screen_h=1200)

    def test_f3_window_top_rail_collider_bounds(self):
        client = {"address": "0x123", "at": [200, 300], "size": [800, 600], "floating": False}
        proj = self.projector.project_client(client)
        planes = proj["planes"]
        top_plane = next(p for p in planes if p["type"] == "window_top")
        self.assertEqual(top_plane["plane"][0], 0.0)
        self.assertEqual(top_plane["plane"][1], 1.0)
        self.assertEqual(top_plane["plane"][2], 0.0)
        bounds = top_plane["bounds"]
        self.assertLess(bounds[0], bounds[1])
        self.assertLessEqual(bounds[2], bounds[3])

    def test_f3_vertical_borders_colliders(self):
        client = {"address": "0x123", "at": [200, 300], "size": [800, 600], "floating": False}
        proj = self.projector.project_client(client)
        planes = proj["planes"]
        left_plane = next(p for p in planes if p["type"] == "window_border_left")
        right_plane = next(p for p in planes if p["type"] == "window_border_right")
        self.assertEqual(left_plane["plane"][0], 1.0)
        self.assertEqual(right_plane["plane"][0], -1.0)

    def test_f3_scrollbar_climbing_collider(self):
        client = {"address": "0x123", "at": [200, 300], "size": [800, 600], "floating": False}
        proj = self.projector.project_client(client)
        planes = proj["planes"]
        scroll_plane = next(p for p in planes if p["type"] == "window_scrollbar")
        self.assertEqual(scroll_plane["type"], "window_scrollbar")
        self.assertEqual(len(scroll_plane["bounds"]), 6)

    def test_f3_multi_window_z_stacking(self):
        c1 = {"address": "0x1", "at": [100, 100], "size": [400, 300], "floating": False, "focusHistoryID": 2}
        c2 = {"address": "0x2", "at": [200, 200], "size": [400, 300], "floating": True, "focusHistoryID": 1}
        c3 = {"address": "0x3", "at": [300, 300], "size": [400, 300], "floating": True, "focusHistoryID": 0}

        p1 = self.projector.project_client(c1, is_active=False)
        p2 = self.projector.project_client(c2, is_active=False)
        p3 = self.projector.project_client(c3, is_active=True)

        self.assertLess(p1["z_depth"], p2["z_depth"])
        self.assertLess(p2["z_depth"], p3["z_depth"])

    def test_f3_window_resize_projection_updates(self):
        c_small = {"address": "0x1", "at": [100, 100], "size": [400, 300]}
        c_large = {"address": "0x1", "at": [100, 100], "size": [800, 600]}
        p_small = self.projector.project_client(c_small)
        p_large = self.projector.project_client(c_large)

        top_small = next(p for p in p_small["planes"] if p["type"] == "window_top")
        top_large = next(p for p in p_large["planes"] if p["type"] == "window_top")

        w_small = top_small["bounds"][1] - top_small["bounds"][0]
        w_large = top_large["bounds"][1] - top_large["bounds"][0]
        self.assertAlmostEqual(w_large, 2.0 * w_small, delta=0.01)

    def test_f3_top_ledge_metric_length(self):
        client = {"address": "0x1", "at": [0, 600], "size": [1920, 600]}
        proj = self.projector.project_client(client)
        ledge = proj["top_ledge"]
        metric_width = ledge["end"][0] - ledge["start"][0]
        self.assertAlmostEqual(metric_width, self.projector.w3d, delta=0.05)

if __name__ == "__main__":
    unittest.main()

import unittest
from tests.test_doubles.loader import get_overlay_window_class

class TestF6LayerShellOverlay(unittest.TestCase):
    def setUp(self):
        overlay_cls = get_overlay_window_class()
        self.overlay = overlay_cls(layer=3, width=1920, height=1200)

    def test_f6_layer_overlay_configuration(self):
        self.assertEqual(self.overlay.layer, 3)

    def test_f6_transparent_background_rgba(self):
        self.assertEqual(self.overlay.background_rgba, (0.0, 0.0, 0.0, 0.0))

    def test_f6_click_through_empty_region(self):
        self.overlay.set_click_through(True)
        self.overlay.update_avatar_mesh_bounds([])
        intercepted = self.overlay.test_point_intercepts_click(500, 500)
        self.assertFalse(intercepted)

    def test_f6_mesh_input_region_mask_intercepts_clicks(self):
        self.overlay.set_click_through(True)
        self.overlay.update_avatar_mesh_bounds([(200, 300, 100, 150)])
        inside = self.overlay.test_point_intercepts_click(250, 350)
        outside = self.overlay.test_point_intercepts_click(100, 100)
        self.assertTrue(inside)
        self.assertFalse(outside)

    def test_f6_dynamic_mesh_bounds_updates(self):
        self.overlay.set_click_through(True)
        self.overlay.update_avatar_mesh_bounds([(100, 100, 50, 50)])
        self.assertTrue(self.overlay.test_point_intercepts_click(120, 120))

        self.overlay.update_avatar_mesh_bounds([(300, 300, 50, 50)])
        self.assertFalse(self.overlay.test_point_intercepts_click(120, 120))
        self.assertTrue(self.overlay.test_point_intercepts_click(320, 320))

    def test_f6_fullscreen_dimensions_matching_monitor(self):
        self.assertEqual(self.overlay.width, 1920)
        self.assertEqual(self.overlay.height, 1200)

if __name__ == "__main__":
    unittest.main()

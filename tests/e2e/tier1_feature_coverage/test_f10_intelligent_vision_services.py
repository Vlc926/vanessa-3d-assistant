import unittest
from tests.test_doubles.loader import get_vision_services_class

class TestF10IntelligentVisionServices(unittest.TestCase):
    def setUp(self):
        vision_cls = get_vision_services_class()
        self.service = vision_cls(offline_mode=True)

    def test_f10_grim_capture_roi_command(self):
        cmd = self.service.build_grim_command(50, 100, 1200, 800, "/tmp/active_roi.jpg")
        self.assertEqual(cmd[0], "grim")
        self.assertEqual(cmd[2], "50,100 1200x800")
        self.assertEqual(cmd[-1], "/tmp/active_roi.jpg")

    def test_f10_dhash_perceptual_fingerprint(self):
        grid = [[i * j for j in range(9)] for i in range(8)]
        h = self.service.compute_dhash_from_grid(grid)
        self.assertIsInstance(h, int)
        self.assertGreaterEqual(h, 0)

    def test_f10_deduplication_skips_identical_frames(self):
        h = 0xAAAAAAAAAAAAAAAA
        self.assertFalse(self.service.should_skip_ai_analysis(h))
        self.assertTrue(self.service.should_skip_ai_analysis(h))

    def test_f10_deduplication_triggers_on_screen_change(self):
        h1 = 0x0000000000000000
        h2 = 0x00000000000000FF
        self.assertFalse(self.service.should_skip_ai_analysis(h1))
        self.assertFalse(self.service.should_skip_ai_analysis(h2))

    def test_f10_context_summary_json_schema(self):
        summary = self.service.generate_context_summary("debugging", "pytest", "focused")
        keys = {"activity", "active_tool", "user_mood", "recommended_state"}
        self.assertTrue(keys.issubset(summary.keys()))
        self.assertEqual(summary["active_tool"], "pytest")

    def test_f10_offline_mode_mock_fallback(self):
        summary = self.service.generate_context_summary()
        self.assertIsNotNone(summary)
        self.assertEqual(self.service.call_count, 1)

if __name__ == "__main__":
    unittest.main()

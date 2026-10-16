import unittest
from tests.test_doubles.loader import get_vision_services_class

class TestVisionConnector(unittest.TestCase):
    def setUp(self):
        vision_cls = get_vision_services_class()
        self.service = vision_cls(offline_mode=True)

    def test_grim_command_geometry_formatting(self):
        cmd = self.service.build_grim_command(100, 200, 800, 600, "/tmp/crop.jpg")
        self.assertEqual(cmd[0], "grim")
        self.assertIn("-g", cmd)
        idx = cmd.index("-g")
        self.assertEqual(cmd[idx + 1], "100,200 800x600")
        self.assertEqual(cmd[-1], "/tmp/crop.jpg")

    def test_dhash_calculation_from_grid(self):
        grid1 = [[10 if c % 2 == 0 else 5 for c in range(9)] for _ in range(8)]
        h1 = self.service.compute_dhash_from_grid(grid1)
        self.assertIsInstance(h1, int)
        self.assertGreater(h1, 0)

    def test_hamming_distance_exact(self):
        h1 = 0b101010
        h2 = 0b101000
        dist = self.service.hamming_distance(h1, h2)
        self.assertEqual(dist, 1)

    def test_deduplication_skip_when_under_threshold(self):
        base_hash = 0x123456789ABCDEF0
        skip_first = self.service.should_skip_ai_analysis(base_hash)
        self.assertFalse(skip_first)

        slightly_different_hash = base_hash ^ 0b11
        skip_second = self.service.should_skip_ai_analysis(slightly_different_hash)
        self.assertTrue(skip_second)

        completely_different = base_hash ^ 0xFFFFFFFFFFFFFFFF
        skip_third = self.service.should_skip_ai_analysis(completely_different)
        self.assertFalse(skip_third)

    def test_context_summary_generation_offline(self):
        summary = self.service.generate_context_summary(activity="coding", tool="nvim", mood="deep_focus")
        self.assertEqual(summary["activity"], "coding")
        self.assertEqual(summary["active_tool"], "nvim")
        self.assertEqual(summary["user_mood"], "deep_focus")
        self.assertEqual(summary["recommended_state"], "perch")

if __name__ == "__main__":
    unittest.main()

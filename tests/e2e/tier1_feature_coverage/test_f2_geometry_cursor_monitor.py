import unittest
from tests.test_doubles.loader import get_hypr_client_class

class TestF2GeometryCursorMonitor(unittest.TestCase):
    def setUp(self):
        client_cls = get_hypr_client_class()
        self.client = client_cls()

    def test_f2_cursor_position_query(self):
        self.client.set_mock_cursor(450, 620)
        x, y = self.client.get_cursor_position()
        self.assertEqual(x, 450)
        self.assertEqual(y, 620)

    def test_f2_clients_query_and_geometry_fields(self):
        clients = self.client.get_clients()
        self.assertGreater(len(clients), 0)
        c = clients[0]
        self.assertIn("at", c)
        self.assertIn("size", c)
        self.assertIn("address", c)
        self.assertEqual(len(c["at"]), 2)
        self.assertEqual(len(c["size"]), 2)

    def test_f2_active_window_selection_by_focus_history(self):
        mock_list = [
            {"address": "0x1", "focusHistoryID": 1, "title": "win1"},
            {"address": "0x2", "focusHistoryID": 0, "title": "active_win"},
            {"address": "0x3", "focusHistoryID": 2, "title": "win3"}
        ]
        self.client.set_mock_clients(mock_list)
        active = self.client.get_active_client()
        self.assertIsNotNone(active)
        self.assertEqual(active["address"], "0x2")
        self.assertEqual(active["title"], "active_win")

    def test_f2_empty_clients_list_handling(self):
        self.client.set_mock_clients([])
        clients = self.client.get_clients()
        self.assertEqual(clients, [])
        active = self.client.get_active_client()
        self.assertIsNone(active)

    def test_f2_cursor_boundary_coordinates(self):
        self.client.set_mock_cursor(0, 0)
        x0, y0 = self.client.get_cursor_position()
        self.assertEqual(x0, 0)
        self.assertEqual(y0, 0)

        self.client.set_mock_cursor(1920, 1200)
        x1, y1 = self.client.get_cursor_position()
        self.assertEqual(x1, 1920)
        self.assertEqual(y1, 1200)

    def test_f2_multiple_clients_sorting_and_indexing(self):
        mock_list = [
            {"address": f"0x{i}", "workspace": {"id": i}, "at": [i*100, i*100], "size": [500, 300]}
            for i in range(5)
        ]
        self.client.set_mock_clients(mock_list)
        clients = self.client.get_clients()
        self.assertEqual(len(clients), 5)
        for i, c in enumerate(clients):
            self.assertEqual(c["address"], f"0x{i}")
            self.assertEqual(c["at"], [i*100, i*100])

if __name__ == "__main__":
    unittest.main()

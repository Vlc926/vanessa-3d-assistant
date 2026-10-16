import unittest
from tests.test_doubles.loader import get_socket_reader_class, get_hypr_client_class

class TestT2F1F2Boundary(unittest.TestCase):
    def setUp(self):
        reader_cls = get_socket_reader_class()
        client_cls = get_hypr_client_class()
        self.reader = reader_cls()
        self.client = client_cls()

    def test_t2_f1_empty_chunk_feed(self):
        events = self.reader.feed_data("")
        self.assertEqual(events, [])

    def test_t2_f1_malformed_line_without_delimiter(self):
        events = self.reader.feed_data("invalid_event_line_here\n")
        self.assertEqual(events, [])

    def test_t2_f1_unknown_event_name_graceful_handling(self):
        events = self.reader.feed_data("nonexistent_event>>data1,data2\n")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "nonexistent_event")

    def test_t2_f1_empty_event_data_fields(self):
        events = self.reader.feed_data("openwindow>>\n")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event"], "openwindow")

    def test_t2_f1_huge_event_payload_stress(self):
        huge_title = "A" * 10000
        line = f"openwindow>>0x1234,1,huge_class,{huge_title}\n"
        events = self.reader.feed_data(line)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["title"], huge_title)

    def test_t2_f1_rapid_window_churn_burst(self):
        burst = "".join([f"openwindow>>{i},1,foot,foot\nclosewindow>>{i}\n" for i in range(50)])
        events = self.reader.feed_data(burst)
        self.assertEqual(len(events), 100)

    def test_t2_f2_negative_cursor_coordinates(self):
        self.client.set_mock_cursor(-50, -100)
        x, y = self.client.get_cursor_position()
        self.assertEqual(x, -50)
        self.assertEqual(y, -100)

    def test_t2_f2_huge_cursor_coordinates(self):
        self.client.set_mock_cursor(50000, 30000)
        x, y = self.client.get_cursor_position()
        self.assertEqual(x, 50000)
        self.assertEqual(y, 30000)

    def test_t2_f2_empty_clients_list_returns_none_active(self):
        self.client.set_mock_clients([])
        self.assertEqual(self.client.get_clients(), [])
        self.assertIsNone(self.client.get_active_client())

    def test_t2_f2_client_with_missing_keys(self):
        incomplete_client = {"address": "0xabc"}
        self.client.set_mock_clients([incomplete_client])
        active = self.client.get_active_client()
        self.assertEqual(active["address"], "0xabc")

    def test_t2_f2_client_with_zero_dimensions(self):
        degenerate = {"address": "0x0", "at": [0, 0], "size": [0, 0], "focusHistoryID": 0}
        self.client.set_mock_clients([degenerate])
        active = self.client.get_active_client()
        self.assertEqual(active["size"], [0, 0])

    def test_t2_f2_hundred_clients_scaling(self):
        large_set = [{"address": f"0x{i}", "at": [i, i], "size": [100, 100], "focusHistoryID": i} for i in range(100)]
        self.client.set_mock_clients(large_set)
        clients = self.client.get_clients()
        self.assertEqual(len(clients), 100)
        active = self.client.get_active_client()
        self.assertEqual(active["address"], "0x0")

if __name__ == "__main__":
    unittest.main()

import unittest
from tests.test_doubles.loader import get_socket_reader_class

class TestF1Socket2Stream(unittest.TestCase):
    def setUp(self):
        reader_cls = get_socket_reader_class()
        self.reader = reader_cls()

    def test_f1_openwindow_event_parsing_and_normalization(self):
        line = "openwindow>>5616a03008b0,1,foot,foot\n"
        events = self.reader.feed_data(line)
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev["event"], "openwindow")
        self.assertEqual(ev["address"], "0x5616a03008b0")
        self.assertEqual(ev["workspace"], "1")
        self.assertEqual(ev["window_class"], "foot")
        self.assertEqual(ev["title"], "foot")

    def test_f1_closewindow_event_parsing(self):
        line = "closewindow>>0x5616a03008b0\n"
        events = self.reader.feed_data(line)
        self.assertEqual(len(events), 1)
        ev = events[0]
        self.assertEqual(ev["event"], "closewindow")
        self.assertEqual(ev["address"], "0x5616a03008b0")

    def test_f1_movewindow_and_movewindowv2_parsing(self):
        chunk = "movewindow>>5616a03008b0,2\nmovewindowv2>>5616a03008b0,3,work3\n"
        events = self.reader.feed_data(chunk)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["event"], "movewindow")
        self.assertEqual(events[0]["workspace_name"], "2")
        self.assertEqual(events[1]["event"], "movewindowv2")
        self.assertEqual(int(events[1]["workspace_id"]), 3)
        self.assertEqual(events[1]["workspace_name"], "work3")

    def test_f1_activewindow_and_unfocused_handling(self):
        chunk = "activewindow>>kitty,terminal\nactivewindow>>,\nactivewindowv2>>\n"
        events = self.reader.feed_data(chunk)
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0]["window_class"], "kitty")
        self.assertEqual(events[0]["title"], "terminal")
        self.assertEqual(events[1]["window_class"], "")
        self.assertEqual(events[1]["title"], "")
        self.assertEqual(events[2]["address"], "")

    def test_f1_changefloatingmode_parsing(self):
        chunk = "changefloatingmode>>5616a03008b0,1\nchangefloatingmode>>5616a03008b0,0\n"
        events = self.reader.feed_data(chunk)
        self.assertEqual(len(events), 2)
        self.assertTrue(events[0]["floating"])
        self.assertFalse(events[1]["floating"])

    def test_f1_multiline_chunk_buffering_and_partial_chunks(self):
        part1 = "openwindow>>5616a0300"
        events1 = self.reader.feed_data(part1)
        self.assertEqual(len(events1), 0)

        part2 = "8b0,1,foot,foot\nclosewindow>>5616a03008b0\n"
        events2 = self.reader.feed_data(part2)
        self.assertEqual(len(events2), 2)
        self.assertEqual(events2[0]["event"], "openwindow")
        self.assertEqual(events2[1]["event"], "closewindow")

if __name__ == "__main__":
    unittest.main()

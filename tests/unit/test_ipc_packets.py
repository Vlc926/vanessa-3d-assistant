import unittest
import json
import time
from tests.test_doubles.loader import get_ipc_server_class

class TestIPCPackets(unittest.TestCase):
    def setUp(self):
        server_cls = get_ipc_server_class()
        self.server = server_cls()

    def test_telemetry_packet_schema_compliance(self):
        packet = self.server.build_telemetry_packet()
        required_keys = {"timestamp", "cursor", "active_window", "collision_planes", "action_feedback"}
        self.assertTrue(required_keys.issubset(packet.keys()))

    def test_cursor_packet_coordinates(self):
        c = {"x": 500, "y": 300, "z": 0.0}
        packet = self.server.build_telemetry_packet(cursor=c)
        self.assertEqual(packet["cursor"]["x"], 500)
        self.assertEqual(packet["cursor"]["y"], 300)

    def test_active_window_top_ledge_format(self):
        packet = self.server.build_telemetry_packet()
        win = packet["active_window"]
        self.assertIn("address", win)
        self.assertIn("top_ledge", win)
        self.assertIn("start", win["top_ledge"])
        self.assertIn("end", win["top_ledge"])
        self.assertEqual(len(win["top_ledge"]["start"]), 3)

    def test_packet_json_serializability(self):
        packet = self.server.build_telemetry_packet()
        serialized = json.dumps(packet)
        deserialized = json.loads(serialized)
        self.assertEqual(deserialized["active_window"]["address"], packet["active_window"]["address"])

    def test_control_packet_schema(self):
        cmd = {
            "command": "push_window",
            "target_address": "0x5616a03008b0",
            "delta": [50, 0]
        }
        encoded = json.dumps(cmd)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["command"], "push_window")
        self.assertEqual(decoded["delta"], [50, 0])

if __name__ == "__main__":
    unittest.main()

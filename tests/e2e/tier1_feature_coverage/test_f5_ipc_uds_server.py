import unittest
import asyncio
import os
import time
from tests.test_doubles.loader import get_ipc_server_class, get_ipc_client_class

class TestF5IPCUdsServer(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.sock_path = f"/tmp/jarvis_test_f5_{os.getpid()}_{int(time.time()*1000)}.sock"
        server_cls = get_ipc_server_class()
        client_cls = get_ipc_client_class()
        self.server = server_cls(socket_path=self.sock_path, fps=60)
        self.client_cls = client_cls
        await self.server.start()

    async def asyncTearDown(self):
        await self.server.stop()
        if os.path.exists(self.sock_path):
            os.remove(self.sock_path)

    async def test_f5_uds_server_lifecycle_bind_and_cleanup(self):
        self.assertTrue(os.path.exists(self.sock_path))
        self.assertTrue(self.server.running)

    async def test_f5_client_connection_and_frame_streaming(self):
        client = self.client_cls(socket_path=self.sock_path)
        await client.connect()
        packet = self.server.build_telemetry_packet()
        await self.server.broadcast_frame(packet)
        received = await client.read_next_frame(timeout=1.0)
        self.assertIsNotNone(received)
        self.assertEqual(received["cursor"]["x"], packet["cursor"]["x"])
        await client.close()

    async def test_f5_schema_validation_of_streamed_packet(self):
        client = self.client_cls(socket_path=self.sock_path)
        await client.connect()
        packet = self.server.build_telemetry_packet()
        await self.server.broadcast_frame(packet)
        rec = await client.read_next_frame(timeout=1.0)
        self.assertIn("timestamp", rec)
        self.assertIn("cursor", rec)
        self.assertIn("active_window", rec)
        self.assertIn("collision_planes", rec)
        self.assertIn("action_feedback", rec)
        await client.close()

    async def test_f5_bidirectional_control_reception(self):
        client = self.client_cls(socket_path=self.sock_path)
        await client.connect()
        cmd = {
            "command": "push_window",
            "target_address": "0x5616a03008b0",
            "delta": [50, 0]
        }
        await client.send_command(cmd)
        await asyncio.sleep(0.05)
        self.assertGreater(len(self.server.received_commands), 0)
        last_cmd = self.server.received_commands[-1]
        self.assertEqual(last_cmd["command"], "push_window")
        self.assertEqual(last_cmd["delta"], [50, 0])
        await client.close()

    async def test_f5_multi_client_broadcast(self):
        c1 = self.client_cls(socket_path=self.sock_path)
        c2 = self.client_cls(socket_path=self.sock_path)
        await c1.connect()
        await c2.connect()

        packet = self.server.build_telemetry_packet(cursor={"x": 999, "y": 888, "z": 0.0})
        await self.server.broadcast_frame(packet)

        r1 = await c1.read_next_frame(timeout=1.0)
        r2 = await c2.read_next_frame(timeout=1.0)
        self.assertEqual(r1["cursor"]["x"], 999)
        self.assertEqual(r2["cursor"]["x"], 999)

        await c1.close()
        await c2.close()

    async def test_f5_high_frequency_tick_rate(self):
        client = self.client_cls(socket_path=self.sock_path)
        await client.connect()
        for i in range(15):
            packet = self.server.build_telemetry_packet(cursor={"x": i * 10, "y": 100, "z": 0.0})
            await self.server.broadcast_frame(packet)
            await asyncio.sleep(0.01)

        frames = await client.read_frames_stream(count=15, timeout_per_frame=0.5)
        self.assertEqual(len(frames), 15)
        self.assertEqual(frames[-1]["cursor"]["x"], 140)
        await client.close()

if __name__ == "__main__":
    unittest.main()

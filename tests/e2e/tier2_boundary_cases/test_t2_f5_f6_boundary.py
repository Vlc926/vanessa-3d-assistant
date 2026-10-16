import unittest
import asyncio
import os
import time
from tests.test_doubles.loader import get_ipc_server_class, get_ipc_client_class, get_overlay_window_class

class TestT2F5F6Boundary(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.sock_path = f"/tmp/jarvis_test_t2_{os.getpid()}_{int(time.time()*1000)}.sock"
        server_cls = get_ipc_server_class()
        client_cls = get_ipc_client_class()
        overlay_cls = get_overlay_window_class()
        self.server = server_cls(socket_path=self.sock_path, fps=60)
        self.client_cls = client_cls
        self.overlay = overlay_cls()
        await self.server.start()

    async def asyncTearDown(self):
        await self.server.stop()
        if os.path.exists(self.sock_path):
            try:
                os.remove(self.sock_path)
            except OSError:
                pass

    async def test_t2_f5_client_connect_nonexistent_socket(self):
        bogus_client = self.client_cls(socket_path="/tmp/nonexistent_socket_12345.sock")
        with self.assertRaises(Exception):
            await bogus_client.connect()

    async def test_t2_f5_sudden_client_disconnect_during_broadcast(self):
        client = self.client_cls(socket_path=self.sock_path)
        await client.connect()
        await client.close()

        packet = self.server.build_telemetry_packet()
        await self.server.broadcast_frame(packet)
        self.assertTrue(self.server.running)

    async def test_t2_f5_read_frame_timeout_returns_none(self):
        client = self.client_cls(socket_path=self.sock_path)
        await client.connect()
        res = await client.read_next_frame(timeout=0.01)
        self.assertIsNone(res)
        await client.close()

    async def test_t2_f5_client_sends_malformed_json_command(self):
        client = self.client_cls(socket_path=self.sock_path)
        await client.connect()
        client.writer.write(b"not_valid_json_string\n")
        await client.writer.drain()
        await asyncio.sleep(0.05)
        self.assertEqual(len(self.server.received_commands), 0)
        await client.close()

    async def test_t2_f5_telemetry_packet_with_none_arguments(self):
        packet = self.server.build_telemetry_packet(cursor=None, active_window=None, collision_planes=None, feedback=None)
        self.assertIn("cursor", packet)
        self.assertIn("active_window", packet)
        self.assertIn("collision_planes", packet)

    async def test_t2_f5_rapid_server_restart_cycle(self):
        await self.server.stop()
        self.assertFalse(self.server.running)
        await self.server.start()
        self.assertTrue(self.server.running)

    def test_t2_f6_zero_size_mesh_rectangle(self):
        self.overlay.update_avatar_mesh_bounds([(100, 100, 0, 0)])
        intercepted = self.overlay.test_point_intercepts_click(100, 100)
        self.assertTrue(intercepted)
        outside = self.overlay.test_point_intercepts_click(101, 100)
        self.assertFalse(outside)

    def test_t2_f6_negative_coordinate_click_testing(self):
        self.overlay.update_avatar_mesh_bounds([(10, 10, 50, 50)])
        intercepted = self.overlay.test_point_intercepts_click(-100, -200)
        self.assertFalse(intercepted)

    def test_t2_f6_boundary_edge_click_interception(self):
        self.overlay.update_avatar_mesh_bounds([(100, 100, 200, 200)])
        self.assertTrue(self.overlay.test_point_intercepts_click(100, 100))
        self.assertTrue(self.overlay.test_point_intercepts_click(300, 300))
        self.assertFalse(self.overlay.test_point_intercepts_click(301, 300))

    def test_t2_f6_click_through_disabled_intercepts_all(self):
        self.overlay.set_click_through(False)
        self.overlay.update_avatar_mesh_bounds([])
        self.assertTrue(self.overlay.test_point_intercepts_click(0, 0))
        self.assertTrue(self.overlay.test_point_intercepts_click(1919, 1199))

    def test_t2_f6_fifty_mesh_rectangles_scaling(self):
        rects = [(i * 20, i * 20, 10, 10) for i in range(50)]
        self.overlay.update_avatar_mesh_bounds(rects)
        self.assertTrue(self.overlay.test_point_intercepts_click(0, 0))
        self.assertTrue(self.overlay.test_point_intercepts_click(980, 980))
        self.assertFalse(self.overlay.test_point_intercepts_click(5, 25))

    def test_t2_f6_arbitrary_layer_setting(self):
        self.overlay.set_layer(1)
        self.assertEqual(self.overlay.layer, 1)
        self.overlay.set_layer(3)
        self.assertEqual(self.overlay.layer, 3)

if __name__ == "__main__":
    unittest.main()

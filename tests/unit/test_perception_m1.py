import asyncio
import json
import os
import tempfile
import time
import unittest
from typing import Any, Dict

from src.perception.socket_reader import SocketReader, normalize_address, parse_event_line
from src.perception.hypr_client import HyprClient
from src.perception.geometry_projector import GeometryProjector
from src.perception.actuator import Actuator
from src.perception.ipc_server import IPCServer
from src.perception.daemon_main import PerceptionDaemon

class TestSocketReader(unittest.TestCase):
    def test_address_normalization_variants(self):
        self.assertEqual(normalize_address("5616a03008b0"), "0x5616a03008b0")
        self.assertEqual(normalize_address("0x5616a03008b0"), "0x5616a03008b0")
        self.assertEqual(normalize_address("0X5616A03008B0"), "0x5616a03008b0")
        self.assertEqual(normalize_address("  5616a03008b0  "), "0x5616a03008b0")
        self.assertEqual(normalize_address(""), "")

    def test_openwindow_with_commas_in_title(self):
        line = "openwindow>>5616a03008b0,1,foot,Terminal, with, commas\n"
        ev = parse_event_line(line)
        self.assertIsNotNone(ev)
        self.assertEqual(ev["event"], "openwindow")
        self.assertEqual(ev["address"], "0x5616a03008b0")
        self.assertEqual(ev["workspace"], "1")
        self.assertEqual(ev["window_class"], "foot")
        self.assertEqual(ev["title"], "Terminal, with, commas")

    def test_closewindow_event(self):
        line = "closewindow>>5616a03008b0\n"
        ev = parse_event_line(line)
        self.assertIsNotNone(ev)
        self.assertEqual(ev["event"], "closewindow")
        self.assertEqual(ev["address"], "0x5616a03008b0")

    def test_movewindow_events(self):
        line1 = "movewindow>>5616a03008b0,2\n"
        ev1 = parse_event_line(line1)
        self.assertIsNotNone(ev1)
        self.assertEqual(ev1["event"], "movewindow")
        self.assertEqual(ev1["address"], "0x5616a03008b0")
        self.assertEqual(ev1["workspace_name"], "2")

        line2 = "movewindowv2>>5616a03008b0,3,workspace_three\n"
        ev2 = parse_event_line(line2)
        self.assertIsNotNone(ev2)
        self.assertEqual(ev2["event"], "movewindowv2")
        self.assertEqual(ev2["address"], "0x5616a03008b0")
        self.assertEqual(ev2["workspace_id"], 3)
        self.assertEqual(ev2["workspace_name"], "workspace_three")

    def test_activewindow_events(self):
        line1 = "activewindow>>kitty,term\n"
        ev1 = parse_event_line(line1)
        self.assertIsNotNone(ev1)
        self.assertEqual(ev1["window_class"], "kitty")
        self.assertEqual(ev1["title"], "term")

        line2 = "activewindowv2>>5616a03008b0\n"
        ev2 = parse_event_line(line2)
        self.assertIsNotNone(ev2)
        self.assertEqual(ev2["address"], "0x5616a03008b0")

        line3 = "activewindowv2>>\n"
        ev3 = parse_event_line(line3)
        self.assertIsNotNone(ev3)
        self.assertEqual(ev3["address"], "")

    def test_floating_and_pin_events(self):
        ev_float = parse_event_line("changefloatingmode>>5616a03008b0,1\n")
        self.assertIsNotNone(ev_float)
        self.assertTrue(ev_float["floating"])

        ev_unfloat = parse_event_line("changefloatingmode>>5616a03008b0,0\n")
        self.assertIsNotNone(ev_unfloat)
        self.assertFalse(ev_unfloat["floating"])

        ev_pin = parse_event_line("pin>>5616a03008b0,1\n")
        self.assertIsNotNone(ev_pin)
        self.assertTrue(ev_pin["pinned"])

    def test_chunk_buffering_and_dispatch(self):
        reader = SocketReader()
        part1 = "openwindow>>5616a0300"
        res1 = reader.feed_data(part1)
        self.assertEqual(len(res1), 0)

        part2 = "8b0,1,foot,foot\nclosewindow>>5616a03008b0\n"
        res2 = reader.feed_data(part2)
        self.assertEqual(len(res2), 2)
        self.assertEqual(res2[0]["event"], "openwindow")
        self.assertEqual(res2[1]["event"], "closewindow")
        self.assertTrue(reader.is_geometry_dirty)

class TestHyprClient(unittest.TestCase):
    def setUp(self):
        self.client = HyprClient()

    def test_mock_cursor_query(self):
        self.client.set_mock_cursor(600, 400)
        x, y = self.client.get_cursor_position()
        self.assertEqual(x, 600)
        self.assertEqual(y, 400)

        pos_dict = self.client.get_cursor_pos()
        self.assertEqual(pos_dict["x"], 600)
        self.assertEqual(pos_dict["y"], 400)

    def test_mock_clients_and_active_window(self):
        mock_data = [
            {"address": "0x1", "focusHistoryID": 1, "title": "win1"},
            {"address": "0x2", "focusHistoryID": 0, "title": "active_win"},
        ]
        self.client.set_mock_clients(mock_data)
        clients = self.client.get_clients()
        self.assertEqual(len(clients), 2)

        active = self.client.get_active_client()
        self.assertIsNotNone(active)
        self.assertEqual(active["address"], "0x2")

    def test_empty_clients_handling(self):
        self.client.set_mock_clients([])
        self.assertEqual(self.client.get_clients(), [])
        self.assertIsNone(self.client.get_active_client())

class TestGeometryProjector(unittest.TestCase):
    def setUp(self):
        self.proj = GeometryProjector(screen_w=1920.0, screen_h=1200.0, fov_deg=30.0, z_ref=2.8)

    def test_origin_and_roundtrip(self):
        p3d = self.proj.pixel_to_3d(960, 600)
        self.assertAlmostEqual(p3d[0], 0.0, delta=0.01)
        self.assertAlmostEqual(p3d[1], 0.0, delta=0.01)

        test_points = [(100, 150), (960, 600), (1800, 1100), (0, 0)]
        for px, py in test_points:
            p = self.proj.pixel_to_3d(px, py)
            r_px, r_py = self.proj.point_3d_to_pixel(p[0], p[1])
            self.assertAlmostEqual(px, r_px, delta=2)
            self.assertAlmostEqual(py, r_py, delta=2)

    def test_z_depth_stacking(self):
        t_inact = {"floating": False, "focusHistoryID": 1}
        t_act = {"floating": False, "focusHistoryID": 0}
        f_inact = {"floating": True, "focusHistoryID": 2}
        f_act = {"floating": True, "focusHistoryID": 0}

        z_ti = self.proj.calculate_z_depth(t_inact, is_active=False)
        z_ta = self.proj.calculate_z_depth(t_act, is_active=True)
        z_fi = self.proj.calculate_z_depth(f_inact, is_active=False)
        z_fa = self.proj.calculate_z_depth(f_act, is_active=True)

        self.assertEqual(z_ti, 0.0)
        self.assertEqual(z_ta, 0.08)
        self.assertGreater(z_fi, z_ti)
        self.assertGreater(z_fa, z_fi)

    def test_walkable_top_ledge(self):
        client = {"address": "0x123", "at": [100, 150], "size": [800, 600]}
        res = self.proj.project_client(client, is_active=True)
        ledge = res["top_ledge"]
        self.assertIn("start", ledge)
        self.assertIn("end", ledge)
        self.assertAlmostEqual(ledge["start"][1], ledge["end"][1], delta=1e-3)
        self.assertLess(ledge["start"][0], ledge["end"][0])

    def test_collision_planes_types(self):
        client = {"address": "0x123", "at": [200, 200], "size": [500, 400], "floating": True}
        res = self.proj.project_client(client)
        types = [p["type"] for p in res["planes"]]
        self.assertIn("window_top", types)
        self.assertIn("window_border_left", types)
        self.assertIn("window_border_right", types)
        self.assertIn("window_scrollbar", types)

    def test_full_project_frame_schema(self):
        frame = self.proj.project_frame(
            clients=[{"address": "0x123", "at": [100, 100], "size": [400, 300]}],
            cursor={"x": 500, "y": 400},
            active_address="0x123",
        )
        self.assertIn("timestamp", frame)
        self.assertIn("cursor", frame)
        self.assertIn("active_window", frame)
        self.assertIn("collision_planes", frame)
        self.assertIn("action_feedback", frame)
        self.assertEqual(frame["active_window"]["address"], "0x123")
        floor_planes = [p for p in frame["collision_planes"] if p["type"] == "floor"]
        self.assertEqual(len(floor_planes), 1)

class TestActuator(unittest.TestCase):
    def setUp(self):
        self.actuator = Actuator(execute_real=False)

    def test_push_and_resize_dispatches(self):
        res1 = self.actuator.push_window("0x5616a03008b0", 40, -10)
        self.assertEqual(res1["status"], "ok")
        self.assertEqual(self.actuator.recorded_dispatches[-1]["cmd"], "movewindowpixel")
        self.assertEqual(self.actuator.recorded_dispatches[-1]["args"], "40 -10,address:0x5616a03008b0")

        res2 = self.actuator.resize_window("0x5616a03008b0", 80, 50)
        self.assertEqual(res2["status"], "ok")
        self.assertEqual(self.actuator.recorded_dispatches[-1]["cmd"], "resizewindowpixel")
        self.assertEqual(self.actuator.recorded_dispatches[-1]["args"], "80 50,address:0x5616a03008b0")

    def test_pointer_injection_recording(self):
        res1 = self.actuator.inject_pointer_move(500, 300, absolute=True)
        self.assertEqual(res1["status"], "ok")
        self.assertEqual(self.actuator.recorded_pointer_events[-1]["x"], 500)
        self.assertEqual(self.actuator.recorded_pointer_events[-1]["y"], 300)

        res2 = self.actuator.inject_pointer_click(0xC0)
        self.assertEqual(res2["status"], "ok")
        self.assertEqual(self.actuator.recorded_pointer_events[-1]["button"], 0xC0)

    def test_compute_push_displacement_physics(self):
        d1 = self.actuator.compute_push_displacement(10.0, avatar_mass=1.0, friction=0.2)
        d2 = self.actuator.compute_push_displacement(10.0, avatar_mass=2.0, friction=0.2)
        self.assertEqual(d1, 8.0)
        self.assertEqual(d2, 4.0)

        d_zero = self.actuator.compute_push_displacement(10.0, avatar_mass=0.0)
        self.assertEqual(d_zero, 0.0)

    def test_impulse_decay_simulation(self):
        self.actuator.add_window_impulse("0x123", (3000.0, 0.0), window_mass=50.0, friction=8.0)
        displacements1 = self.actuator.step_physics(1.0 / 60.0)
        self.assertEqual(len(displacements1), 1)
        self.assertEqual(displacements1[0][0], "0x123")
        for _ in range(60):
            self.actuator.step_physics(1.0 / 60.0)
        self.assertEqual(len(self.actuator.active_impulses), 0)

class TestIPCServerAndDaemon(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.sock_path = f"/tmp/jarvis_unit_m1_{os.getpid()}_{int(time.time()*1000)}.sock"
        self.server = IPCServer(socket_path=self.sock_path, fps=60.0)
        await self.server.start()

    async def asyncTearDown(self):
        await self.server.stop()
        if os.path.exists(self.sock_path):
            os.remove(self.sock_path)

    async def test_server_broadcast_and_client_receive(self):
        reader, writer = await asyncio.open_unix_connection(self.sock_path)
        await asyncio.sleep(0.01)
        packet = self.server.build_telemetry_packet(cursor={"x": 123, "y": 456, "z": 0.0})
        await self.server.broadcast_frame(packet)
        line = await asyncio.wait_for(reader.readline(), timeout=1.0)
        received = json.loads(line.decode("utf-8").strip())
        self.assertEqual(received["cursor"]["x"], 123)
        self.assertEqual(received["cursor"]["y"], 456)
        writer.close()
        await writer.wait_closed()

    async def test_control_command_reception(self):
        reader, writer = await asyncio.open_unix_connection(self.sock_path)
        await asyncio.sleep(0.01)
        cmd = {"command": "push_window", "target_address": "0x5616a03008b0", "delta": [20, 10]}
        writer.write((json.dumps(cmd) + "\n").encode("utf-8"))
        await writer.drain()
        await asyncio.sleep(0.05)
        self.assertGreater(len(self.server.received_commands), 0)
        self.assertEqual(self.server.received_commands[-1]["command"], "push_window")
        writer.close()
        await writer.wait_closed()

    async def test_daemon_produce_frame_and_control(self):
        daemon = PerceptionDaemon(ipc_socket_path=None, target_fps=60.0, execute_real=False)
        daemon.hypr_client.set_mock_cursor(320, 240)
        daemon.hypr_client.set_mock_clients([
            {"address": "0x999", "at": [50, 50], "size": [400, 300], "focusHistoryID": 0, "title": "win"}
        ])
        daemon.on_hypr_event("openwindow", "999,1,class,title")
        frame = await daemon.produce_frame()
        self.assertIsNotNone(frame)
        self.assertEqual(frame["cursor"]["x"], 320)
        self.assertEqual(frame["cursor"]["y"], 240)

        ctrl_res = await daemon.handle_control_request({
            "command": "push_window",
            "target_address": "0x999",
            "delta": [15, 0],
        })
        self.assertEqual(ctrl_res["status"], "ok")
        self.assertEqual(ctrl_res["command"], "push_window")

if __name__ == "__main__":
    unittest.main()

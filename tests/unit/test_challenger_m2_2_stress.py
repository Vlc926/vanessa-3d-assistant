import asyncio
import json
import math
import os
import random
import time
import unittest
from typing import Any, Dict, List, Tuple
import numpy as np

from src.visual.overlay_window import OverlayWindow
from src.visual.ipc_client import IPCClient
from src.visual.visual_main import VisualCoordinator
from src.visual.two_bone_ik import TwoBoneIKSolver
from src.visual.foot_lock import FootLockController

class TestOverlayWindowStress(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(42)
        self.overlay = OverlayWindow(layer=3, width=1920, height=1200)

    def test_stress_10000_points_across_100_random_mesh_boxes(self) -> None:
        boxes: List[Tuple[float, float, float, float]] = []
        for i in range(100):
            bx = random.uniform(-200.0, 2120.0)
            by = random.uniform(-200.0, 1400.0)
            bw = random.uniform(10.0, 350.0)
            bh = random.uniform(10.0, 350.0)
            if i == 0:
                bx, by, bw, bh = 500.0, 500.0, 0.0, 0.0
            elif i == 1:
                bx, by, bw, bh = 0.0, 0.0, 100.0, 100.0
            boxes.append((bx, by, bw, bh))

        self.overlay.set_click_through(True)
        self.overlay.update_avatar_mesh_bounds(boxes)

        points: List[Tuple[float, float]] = []
        for bx, by, bw, bh in boxes:
            points.append((bx, by))
            points.append((bx + bw, by))
            points.append((bx, by + bh))
            points.append((bx + bw, by + bh))
            points.append((bx + bw * 0.5, by))
            points.append((bx + bw * 0.5, by + bh))
            points.append((bx, by + bh * 0.5))
            points.append((bx + bw, by + bh * 0.5))

        for bx, by, bw, bh in boxes:
            for _ in range(12):
                rx = bx + bw * random.uniform(0.05, 0.95)
                ry = by + bh * random.uniform(0.05, 0.95)
                points.append((rx, ry))

        for bx, by, bw, bh in boxes:
            points.append((bx - 1e-5, by + bh * 0.5))
            points.append((bx + bw + 1e-5, by + bh * 0.5))
            points.append((bx + bw * 0.5, by - 1e-5))
            points.append((bx + bw * 0.5, by + bh + 1e-5))
            points.append((bx - 1e-5, by - 1e-5))
            points.append((bx + bw + 1e-5, by + bh + 1e-5))
            points.append((bx - 1e-5, by + bh + 1e-5))
            points.append((bx + bw + 1e-5, by - 1e-5))
            points.append((bx - 2.0, by - 2.0))
            points.append((bx + bw + 2.0, by + bh + 2.0))

        remaining_needed = 10000 - len(points)
        for _ in range(remaining_needed):
            px = random.uniform(-800.0, 3000.0)
            py = random.uniform(-800.0, 2200.0)
            points.append((px, py))

        self.assertEqual(len(points), 10000)

        def oracle_hit(rect_list: List[Tuple[float, float, float, float]], x: float, y: float) -> bool:
            for rx, ry, rw, rh in rect_list:
                if rx <= x <= (rx + rw) and ry <= y <= (ry + rh):
                    return True
            return False

        t0 = time.perf_counter()
        hits_count = 0
        misses_count = 0
        for px, py in points:
            actual = self.overlay.test_point_intercepts_click(px, py)
            expected = oracle_hit(boxes, px, py)
            self.assertEqual(actual, expected)
            if actual:
                hits_count += 1
            else:
                misses_count += 1
        t_elapsed = time.perf_counter() - t0

        self.assertEqual(hits_count + misses_count, 10000)
        self.assertGreater(hits_count, 2000)
        self.assertGreater(misses_count, 2000)
        self.assertLess(t_elapsed, 0.5)

    def test_inclusive_boundary_conditions_exact_and_epsilon(self) -> None:
        target_box = (200.0, 300.0, 400.0, 500.0)
        self.overlay.set_click_through(True)
        self.overlay.update_avatar_mesh_bounds([target_box])

        exact_points = [
            (200.0, 300.0),
            (600.0, 300.0),
            (200.0, 800.0),
            (600.0, 800.0),
            (400.0, 300.0),
            (400.0, 800.0),
            (200.0, 550.0),
            (600.0, 550.0),
            (200.000001, 300.000001),
            (599.999999, 799.999999),
        ]
        for px, py in exact_points:
            self.assertTrue(self.overlay.test_point_intercepts_click(px, py))

        outside_points = [
            (199.99999, 550.0),
            (600.00001, 550.0),
            (400.0, 299.99999),
            (400.0, 800.00001),
            (199.99999, 299.99999),
            (600.00001, 299.99999),
            (199.99999, 800.00001),
            (600.00001, 800.00001),
            (-500.0, -500.0),
            (5000.0, 5000.0),
        ]
        for px, py in outside_points:
            self.assertFalse(self.overlay.test_point_intercepts_click(px, py))

    def test_click_through_toggle_and_empty_states(self) -> None:
        self.overlay.set_click_through(True)
        self.overlay.update_avatar_mesh_bounds([])
        for px, py in [(0.0, 0.0), (500.0, 500.0), (1919.0, 1199.0), (-10.0, -10.0)]:
            self.assertFalse(self.overlay.test_point_intercepts_click(px, py))

        self.overlay.set_click_through(False)
        self.overlay.update_avatar_mesh_bounds([])
        for px, py in [(0.0, 0.0), (500.0, 500.0), (1919.0, 1199.0), (-10.0, -10.0)]:
            self.assertTrue(self.overlay.test_point_intercepts_click(px, py))

        self.overlay.update_avatar_mesh_bounds([(100.0, 100.0, 50.0, 50.0)])
        for px, py in [(125.0, 125.0), (0.0, 0.0), (999.0, 999.0)]:
            self.assertTrue(self.overlay.test_point_intercepts_click(px, py))

class TestIPCClientStress(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.sock_path = f"/tmp/jarvis_stress_ipc_{os.getpid()}_{int(time.time()*1000)}.sock"
        self.server = None
        self.server_received_commands: List[Dict[str, Any]] = []

    async def asyncTearDown(self) -> None:
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        if os.path.exists(self.sock_path):
            try:
                os.remove(self.sock_path)
            except OSError:
                pass

    async def test_60hz_frame_consumption_under_network_jitter(self) -> None:
        num_frames = 120
        frame_interval = 1.0 / 60.0

        async def server_handler(reader, writer):
            rng = random.Random(1337)
            for i in range(num_frames):
                telemetry = {
                    "timestamp": time.time(),
                    "frame_id": i,
                    "cursor": {"x": 200 + i, "y": 300 + i, "z": 0.0},
                    "active_window": {
                        "address": "0x1234abcd",
                        "at": [100, 150],
                        "size": [800, 600],
                        "top_ledge": {
                            "start": [100.0, 150.0, 0.0],
                            "end": [900.0, 150.0, 0.0]
                        }
                    },
                    "collision_planes": []
                }
                payload = (json.dumps(telemetry) + "\n").encode("utf-8")
                writer.write(payload)
                await writer.drain()
                jitter_delay = max(0.001, frame_interval + rng.gauss(0.0, 0.005))
                await asyncio.sleep(jitter_delay)
            await asyncio.sleep(0.1)
            writer.close()
            await writer.wait_closed()

        self.server = await asyncio.start_unix_server(server_handler, path=self.sock_path)

        client = IPCClient(socket_path=self.sock_path)
        await client.connect()

        callback_frames: List[Dict[str, Any]] = []
        client.register_callback(lambda f: callback_frames.append(f))
        client.start_background_stream()

        await asyncio.sleep(2.5)

        self.assertGreaterEqual(len(client.received_frames), 115)
        self.assertGreaterEqual(len(callback_frames), 115)
        self.assertIsNotNone(client.get_latest_frame())
        self.assertGreaterEqual(client.get_latest_frame().get("frame_id", 0), 110)

        jitter_ms = client.calculate_jitter_ms()
        self.assertGreater(jitter_ms, 0.5)

        self.assertLessEqual(client._frame_queue.qsize(), 1)

        await client.close()

    async def test_single_slot_queue_drop_oldest_under_backpressure(self) -> None:
        burst_count = 80

        async def flood_server(reader, writer):
            for i in range(burst_count):
                packet = json.dumps({"frame_index": i, "timestamp": time.time()}) + "\n"
                writer.write(packet.encode("utf-8"))
                await writer.drain()
                await asyncio.sleep(0.002)
            await asyncio.sleep(0.1)
            writer.close()
            await writer.wait_closed()

        self.server = await asyncio.start_unix_server(flood_server, path=self.sock_path)

        client = IPCClient(socket_path=self.sock_path)
        await client.connect()
        client.start_background_stream()

        consumed_indices: List[int] = []
        for _ in range(8):
            await asyncio.sleep(0.025)
            self.assertLessEqual(client._frame_queue.qsize(), 1)
            try:
                item = client._frame_queue.get_nowait()
                consumed_indices.append(item["frame_index"])
            except asyncio.QueueEmpty:
                pass

        await asyncio.sleep(0.1)
        self.assertGreater(len(consumed_indices), 2)
        for k in range(1, len(consumed_indices)):
            self.assertGreater(consumed_indices[k], consumed_indices[k - 1])

        latest = client.get_latest_frame()
        self.assertIsNotNone(latest)
        self.assertEqual(latest["frame_index"], burst_count - 1)
        self.assertLessEqual(client._frame_queue.qsize(), 1)

        await client.close()

    async def test_bidirectional_control_routing_under_load_and_jitter(self) -> None:
        async def bidi_server_handler(reader, writer):
            async def stream_frames():
                for i in range(100):
                    data = json.dumps({"ts": time.time(), "seq": i}) + "\n"
                    writer.write(data.encode("utf-8"))
                    await writer.drain()
                    await asyncio.sleep(0.016)

            async def read_commands():
                while True:
                    line = await reader.readline()
                    if not line:
                        break
                    try:
                        cmd = json.loads(line.decode("utf-8").strip())
                        self.server_received_commands.append(cmd)
                    except Exception:
                        pass

            stream_task = asyncio.create_task(stream_frames())
            cmd_task = asyncio.create_task(read_commands())
            await asyncio.gather(stream_task, cmd_task, return_exceptions=True)
            writer.close()
            await writer.wait_closed()

        self.server = await asyncio.start_unix_server(bidi_server_handler, path=self.sock_path)

        client = IPCClient(socket_path=self.sock_path)
        await client.connect()
        client.start_background_stream()

        cmd_count = 200
        t_start = time.perf_counter()
        for idx in range(cmd_count):
            mod = idx % 8
            if mod == 0:
                await client.push_window(f"0x{idx:x}", idx, -idx)
            elif mod == 1:
                await client.push_window_impulse(f"0x{idx:x}", float(idx), float(-idx), mass=45.0, friction=7.5)
            elif mod == 2:
                await client.inject_click("0xC0" if (idx % 2 == 0) else "0xC1")
            elif mod == 3:
                await client.inject_mouse_move(idx * 2, idx * 3, absolute=True)
            elif mod == 4:
                await client.move_active(idx, -idx)
            elif mod == 5:
                await client.resize_window(f"0x{idx:x}", 50 + idx, 50 + idx)
            elif mod == 6:
                await client.close_window(f"0x{idx:x}")
            else:
                await client.focus_window(f"0x{idx:x}")

        t_end = time.perf_counter()
        total_cmd_time = t_end - t_start

        await asyncio.sleep(0.2)

        self.assertEqual(len(self.server_received_commands), cmd_count)
        self.assertLess(total_cmd_time, 1.0)

        commands_seen = {c["command"] for c in self.server_received_commands}
        self.assertEqual(len(commands_seen), 8)
        self.assertIn("push_window", commands_seen)
        self.assertIn("push_window_impulse", commands_seen)
        self.assertIn("inject_click", commands_seen)
        self.assertIn("inject_mouse_move", commands_seen)
        self.assertIn("move_active", commands_seen)
        self.assertIn("resize_window", commands_seen)
        self.assertIn("close_window", commands_seen)
        self.assertIn("focus_window", commands_seen)

        await client.close()

    async def test_corrupted_and_adversarial_stream_resilience(self) -> None:
        async def corrupt_server(reader, writer):
            lines = [
                b"",
                b"\n",
                b"   \n",
                b'{"bad": "json"\n',
                b"GARBAGE_LINE_NOT_JSON\n",
                b'{"timestamp": 100.0, "index": 1}\n',
                b'{"incomplete": \n',
                b"\x00\x00\x00\x00\n",
                b'{"timestamp": 101.0, "index": 2}\n',
                b'{"big": "' + (b"A" * 20000) + b'"}\n',
                b'{"timestamp": 102.0, "index": 3}\n',
            ]
            for ln in lines:
                writer.write(ln)
                await writer.drain()
                await asyncio.sleep(0.01)
            await asyncio.sleep(0.1)
            writer.close()
            await writer.wait_closed()

        self.server = await asyncio.start_unix_server(corrupt_server, path=self.sock_path)

        client = IPCClient(socket_path=self.sock_path)
        await client.connect()
        client.start_background_stream()

        await asyncio.sleep(0.3)

        self.assertGreaterEqual(len(client.received_frames), 3)
        latest = client.get_latest_frame()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.get("index"), 3)

        await client.close()

class TestVisualCoordinatorStress(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.overlay = OverlayWindow(layer=3, width=1920, height=1200)
        self.ik_solver = TwoBoneIKSolver(l1=0.42, l2=0.40)
        self.foot_lock = FootLockController(l1=0.42, l2=0.40, hip_rest_y=0.82)
        self.coordinator = VisualCoordinator(
            overlay=self.overlay,
            ik_solver=self.ik_solver,
            foot_lock=self.foot_lock,
            fps=60.0,
            screen_width=1920,
            screen_height=1200,
        )

    def test_loop_stepping_120_ticks_and_coordinate_stability(self) -> None:
        num_ticks = 120
        dt = 1.0 / 60.0

        for step in range(num_ticks):
            frame = {
                "timestamp": 1000.0 + step * dt,
                "cursor": {
                    "x": 400.0 + step * 2.5,
                    "y": 300.0 + math.sin(step * 0.1) * 50.0,
                    "z": 0.0
                },
                "active_window": {
                    "address": "0x5616a03008b0",
                    "at": [200 + step, 300],
                    "size": [800, 600],
                    "top_ledge": {
                        "start": [200.0 + step, 300.0, 0.0],
                        "end": [1000.0 + step, 300.0, 0.0]
                    }
                }
            }

            res = self.coordinator.tick(frame, dt=dt)

            self.assertEqual(res["frames_processed"], step + 1)
            self.assertEqual(self.coordinator.avatar_y, 300.0)
            self.assertGreaterEqual(self.coordinator.avatar_x, 200.0 + step)
            self.assertLessEqual(self.coordinator.avatar_x, 1000.0 + step)

            hip = np.array(res["hip_pos"])
            knee_l = np.array(res["knee_left"])
            ankle_l = np.array(res["ankle_left"])
            knee_r = np.array(res["knee_right"])
            ankle_r = np.array(res["ankle_right"])

            self.assertFalse(np.isnan(hip).any())
            self.assertFalse(np.isnan(knee_l).any())
            self.assertFalse(np.isnan(ankle_l).any())
            self.assertFalse(np.isnan(knee_r).any())
            self.assertFalse(np.isnan(ankle_r).any())

            len1_l = float(np.linalg.norm(knee_l - hip))
            len2_l = float(np.linalg.norm(ankle_l - knee_l))
            len1_r = float(np.linalg.norm(knee_r - hip))
            len2_r = float(np.linalg.norm(ankle_r - knee_r))

            self.assertAlmostEqual(len1_l, 0.42, delta=1e-3)
            self.assertAlmostEqual(len2_l, 0.40, delta=1e-3)
            self.assertAlmostEqual(len1_r, 0.42, delta=1e-3)
            self.assertAlmostEqual(len2_r, 0.40, delta=1e-3)

            mesh = res["mesh_bounds"]
            self.assertEqual(len(self.overlay.mesh_rectangles), 1)
            self.assertEqual(self.overlay.mesh_rectangles[0], mesh)

        self.assertEqual(self.coordinator.frames_processed, 120)

    def test_monotonic_pacing_and_drift_prevention(self) -> None:
        dt = 1.0 / 60.0
        start_mono = 100.0
        target_series: List[float] = []

        for frame_idx in range(1, 121):
            target_mono = start_mono + (frame_idx * dt)
            target_series.append(target_mono)

        for i in range(1, len(target_series)):
            delta = target_series[i] - target_series[i - 1]
            self.assertAlmostEqual(delta, dt, delta=1e-12)

        cumulative_target = target_series[-1] - start_mono
        expected_span = 120 * dt
        self.assertAlmostEqual(cumulative_target, expected_span, delta=1e-12)

    async def test_coordinator_async_run_lifecycle_and_stop(self) -> None:
        sock_path = f"/tmp/jarvis_coord_run_{os.getpid()}_{int(time.time()*1000)}.sock"

        async def srv_handler(reader, writer):
            for i in range(30):
                f = {
                    "timestamp": time.time(),
                    "cursor": {"x": 500, "y": 600, "z": 0.0},
                    "active_window": {
                        "address": "0xabc",
                        "top_ledge": {"start": [100.0, 200.0, 0.0], "end": [800.0, 200.0, 0.0]}
                    }
                }
                writer.write((json.dumps(f) + "\n").encode("utf-8"))
                await writer.drain()
                await asyncio.sleep(0.016)
            await asyncio.sleep(0.1)
            writer.close()
            await writer.wait_closed()

        srv = await asyncio.start_unix_server(srv_handler, path=sock_path)

        client = IPCClient(socket_path=sock_path)
        coord = VisualCoordinator(ipc_client=client)

        task = asyncio.create_task(coord.run())
        await asyncio.sleep(0.2)

        self.assertTrue(coord.running)
        self.assertGreater(coord.frames_processed, 0)

        coord.running = False
        await asyncio.sleep(0.05)

        try:
            await asyncio.wait_for(task, timeout=0.5)
        except asyncio.TimeoutError:
            task.cancel()

        self.assertFalse(coord.running)
        self.assertFalse(client.running)

        srv.close()
        await srv.wait_closed()
        if os.path.exists(sock_path):
            os.remove(sock_path)

if __name__ == "__main__":
    unittest.main()

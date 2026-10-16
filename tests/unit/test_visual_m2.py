import asyncio
import json
import math
import os
import time
import unittest
import numpy as np

from src.visual.overlay_window import OverlayWindow
from src.visual.two_bone_ik import TwoBoneIKSolver
from src.visual.foot_lock import FootLockController
from src.visual.ipc_client import IPCClient
from src.visual.visual_main import VisualCoordinator

class TestOverlayWindowUnit(unittest.TestCase):
    def setUp(self):
        self.overlay = OverlayWindow(layer=3, width=1920, height=1200)

    def test_overlay_initialization(self):
        self.assertEqual(self.overlay.layer, 3)
        self.assertEqual(self.overlay.width, 1920)
        self.assertEqual(self.overlay.height, 1200)
        self.assertEqual(self.overlay.background_rgba, (0.0, 0.0, 0.0, 0.0))
        self.assertTrue(self.overlay.click_through_enabled)
        self.assertEqual(self.overlay.mesh_rectangles, [])

    def test_overlay_set_layer(self):
        self.overlay.set_layer(1)
        self.assertEqual(self.overlay.layer, 1)
        self.overlay.set_layer(3)
        self.assertEqual(self.overlay.layer, 3)

    def test_overlay_set_click_through(self):
        self.overlay.set_click_through(False)
        self.assertFalse(self.overlay.click_through_enabled)
        self.overlay.set_click_through(True)
        self.assertTrue(self.overlay.click_through_enabled)

    def test_overlay_click_through_empty_region(self):
        self.overlay.set_click_through(True)
        self.overlay.update_avatar_mesh_bounds([])
        self.assertFalse(self.overlay.test_point_intercepts_click(500, 500))

    def test_overlay_click_through_disabled_intercepts_anywhere(self):
        self.overlay.set_click_through(False)
        self.overlay.update_avatar_mesh_bounds([])
        self.assertTrue(self.overlay.test_point_intercepts_click(0, 0))
        self.assertTrue(self.overlay.test_point_intercepts_click(1919, 1199))
        self.assertTrue(self.overlay.test_point_intercepts_click(500, 500))

    def test_overlay_mesh_rectangles_interception(self):
        self.overlay.set_click_through(True)
        self.overlay.update_avatar_mesh_bounds([(200, 300, 100, 150)])
        self.assertTrue(self.overlay.test_point_intercepts_click(250, 350))
        self.assertFalse(self.overlay.test_point_intercepts_click(100, 100))
        self.assertTrue(self.overlay.test_point_intercepts_click(200, 300))
        self.assertTrue(self.overlay.test_point_intercepts_click(300, 450))
        self.assertFalse(self.overlay.test_point_intercepts_click(301, 450))

    def test_overlay_zero_size_rectangle(self):
        self.overlay.update_avatar_mesh_bounds([(100, 100, 0, 0)])
        self.assertTrue(self.overlay.test_point_intercepts_click(100, 100))
        self.assertFalse(self.overlay.test_point_intercepts_click(101, 100))

    def test_overlay_negative_coordinates(self):
        self.overlay.update_avatar_mesh_bounds([(10, 10, 50, 50)])
        self.assertFalse(self.overlay.test_point_intercepts_click(-100, -200))

    def test_overlay_lifecycle_methods(self):
        self.overlay.show()
        self.overlay.hide()
        self.overlay.poll_events()
        self.overlay.destroy()
        self.assertFalse(self.overlay.is_real)

class TestTwoBoneIKSolverUnit(unittest.TestCase):
    def setUp(self):
        self.solver = TwoBoneIKSolver(l1=0.42, l2=0.40)
        self.p_root = np.array([0.0, 0.82, 0.0], dtype=np.float64)
        self.v_pole = np.array([0.0, 0.40, 1.0], dtype=np.float64)

    def test_ik_solver_initialization(self):
        self.assertAlmostEqual(self.solver.l1, 0.42)
        self.assertAlmostEqual(self.solver.l2, 0.40)
        self.assertAlmostEqual(self.solver.total_len, 0.82)

    def test_ik_reachable_target_accuracy(self):
        targets = [
            np.array([0.1, 0.05, 0.05]),
            np.array([0.0, 0.10, 0.20]),
            np.array([-0.10, 0.25, 0.05]),
            np.array([0.0, 0.05, 0.0]),
        ]
        for t in targets:
            _, _, p_ankle = self.solver.solve(self.p_root, t, self.v_pole)
            err = float(np.linalg.norm(p_ankle - t))
            self.assertLess(err, 1e-4)

    def test_ik_bone_lengths_preservation(self):
        t = np.array([0.2, 0.15, 0.1])
        p_root, p_knee, p_ankle = self.solver.solve(self.p_root, t, self.v_pole)
        len1 = float(np.linalg.norm(p_knee - p_root))
        len2 = float(np.linalg.norm(p_ankle - p_knee))
        self.assertAlmostEqual(len1, self.solver.l1, delta=1e-3)
        self.assertAlmostEqual(len2, self.solver.l2, delta=1e-3)

    def test_ik_overextended_target_clamping(self):
        t_far = np.array([0.0, -100.0, 0.0])
        p_root, p_knee, p_ankle = self.solver.solve(self.p_root, t_far, self.v_pole)
        self.assertFalse(np.isnan(p_knee).any())
        self.assertFalse(np.isnan(p_ankle).any())
        dist = float(np.linalg.norm(p_ankle - p_root))
        max_reach = self.solver.total_len * 0.9999
        self.assertAlmostEqual(dist, max_reach, delta=1e-3)

    def test_ik_target_at_root(self):
        t_root = np.copy(self.p_root)
        p_root, p_knee, p_ankle = self.solver.solve(self.p_root, t_root, self.v_pole)
        self.assertFalse(np.isnan(p_knee).any())
        self.assertFalse(np.isnan(p_ankle).any())
        self.assertTrue(np.array_equal(p_root, self.p_root))

    def test_ik_collinear_pole_fallback(self):
        t = np.array([0.0, 0.10, 0.0])
        v_collinear = np.array([0.0, 0.50, 0.0])
        _, p_knee, p_ankle = self.solver.solve(self.p_root, t, v_collinear)
        self.assertFalse(np.isnan(p_knee).any())
        self.assertFalse(np.isnan(p_ankle).any())
        err = float(np.linalg.norm(p_ankle - t))
        self.assertLess(err, 1e-4)

    def test_ik_zero_pole_vector(self):
        t = np.array([0.1, 0.1, 0.1])
        _, p_knee, p_ankle = self.solver.solve(self.p_root, t, [0.0, 0.0, 0.0])
        self.assertFalse(np.isnan(p_knee).any())
        self.assertFalse(np.isnan(p_ankle).any())

    def test_ik_under_reach_target(self):
        t_close = self.p_root + np.array([0.0, -0.005, 0.0])
        _, p_knee, p_ankle = self.solver.solve(self.p_root, t_close, self.v_pole)
        self.assertFalse(np.isnan(p_knee).any())
        self.assertFalse(np.isnan(p_ankle).any())

class TestFootLockControllerUnit(unittest.TestCase):
    def setUp(self):
        self.controller = FootLockController(l1=0.42, l2=0.40, hip_rest_y=0.82)

    def test_foot_lock_initialization(self):
        self.assertEqual(self.controller.state, "STANCE")
        self.assertAlmostEqual(self.controller.total_len, 0.82)
        self.assertAlmostEqual(self.controller.hip_rest_y, 0.82)
        self.assertEqual(list(self.controller.local_anchor), [0.0, 0.0, 0.0])

    def test_foot_lock_plant_foot(self):
        self.controller.plant_foot([150.0, 200.0, 0.0], [100.0, 200.0, 0.0])
        self.assertEqual(self.controller.state, "STANCE")
        self.assertEqual(list(self.controller.local_anchor), [50.0, 0.0, 0.0])

    def test_foot_lock_zero_sliding_world_pos(self):
        win_pos = np.array([100.0, 200.0, 0.0])
        initial_foot = np.array([150.0, 200.0, 0.0])
        self.controller.plant_foot(initial_foot, win_pos)

        for _ in range(60):
            win_pos[0] += 3.5
            win_pos[1] -= 1.2
            world_foot = self.controller.get_world_foot_pos(win_pos)
            slip = float(np.linalg.norm((world_foot - win_pos) - self.controller.local_anchor))
            self.assertEqual(slip, 0.0)

    def test_foot_lock_hip_drop_compensation(self):
        win_pos = np.array([0.0, 0.0, 0.0])
        initial_foot = np.array([0.0, 0.0, 0.0])
        self.controller.plant_foot(initial_foot, win_pos)
        rest_hip_y = self.controller.hip_pos[1]

        for step in range(30):
            pelvis_x = float(step) * 0.03
            self.controller.update_hip_position(win_pos, pelvis_x)

        self.assertLess(self.controller.hip_pos[1], rest_hip_y)

    def test_foot_lock_hip_drop_dt_clamping(self):
        win_pos = [0.0, 0.0, 0.0]
        self.controller.plant_foot([0.0, 0.0, 0.0], win_pos)
        hip = self.controller.update_hip_position(win_pos, pelvis_x=0.5, dt=10.0)
        self.assertFalse(np.isnan(hip).any())
        self.assertGreater(hip[1], 0.0)

    def test_foot_lock_liftoff_and_swing_transition(self):
        win_pos = np.array([0.0, 0.0, 0.0])
        self.controller.plant_foot([0.0, 0.0, 0.0], win_pos)
        self.assertEqual(self.controller.state, "STANCE")

        self.controller.update_hip_position(win_pos, pelvis_x=0.2)
        lifted = self.controller.check_liftoff(win_pos, step_distance_threshold=0.50)
        self.assertFalse(lifted)
        self.assertEqual(self.controller.state, "STANCE")

        self.controller.update_hip_position(win_pos, pelvis_x=0.6)
        lifted = self.controller.check_liftoff(win_pos, step_distance_threshold=0.50)
        self.assertTrue(lifted)
        self.assertEqual(self.controller.state, "SWING")

    def test_foot_lock_plant_foot_resets_swing(self):
        self.controller.state = "SWING"
        self.controller.plant_foot([10.0, 20.0, 0.0], [5.0, 10.0, 0.0])
        self.assertEqual(self.controller.state, "STANCE")
        self.assertEqual(list(self.controller.local_anchor), [5.0, 10.0, 0.0])

    def test_foot_lock_negative_anchor(self):
        self.controller.plant_foot([-1000.0, -2000.0, 0.0], [0.0, 0.0, 0.0])
        world_foot = self.controller.get_world_foot_pos([10.0, 20.0, 0.0])
        self.assertEqual(world_foot[0], -990.0)
        self.assertEqual(world_foot[1], -1980.0)

class TestIPCClientUnit(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.sock_path = f"/tmp/jarvis_unit_ipc_{os.getpid()}_{int(time.time()*1000)}.sock"
        self.server = None
        self.server_commands = []

    async def _start_mock_server(self):
        async def handle_client(reader, writer):
            while True:
                line = await reader.readline()
                if not line:
                    break
                try:
                    cmd = json.loads(line.decode("utf-8").strip())
                    self.server_commands.append(cmd)
                except Exception:
                    pass
            writer.close()
            await writer.wait_closed()

        self.server = await asyncio.start_unix_server(handle_client, path=self.sock_path)

    async def asyncTearDown(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        if os.path.exists(self.sock_path):
            try:
                os.remove(self.sock_path)
            except OSError:
                pass

    def test_ipc_client_default_socket_path(self):
        client = IPCClient()
        self.assertIn("perception_engine.sock", client.socket_path)

    def test_ipc_client_custom_socket_path(self):
        client = IPCClient(socket_path="/custom/path.sock")
        self.assertEqual(client.socket_path, "/custom/path.sock")

    async def test_ipc_client_connect_failure(self):
        client = IPCClient(socket_path="/tmp/nonexistent_socket_99999.sock")
        with self.assertRaises(Exception):
            await client.connect()

    async def test_ipc_client_command_dispatchers(self):
        await self._start_mock_server()
        client = IPCClient(socket_path=self.sock_path)
        await client.connect()

        await client.push_window("0x123", 40, 20)
        await client.push_window_impulse("0x123", 5.0, 2.5, mass=40.0, friction=6.0)
        await client.inject_click("0xC0")
        await client.inject_mouse_move(100, 200, absolute=True)
        await client.move_active(15, -10)
        await client.resize_window("0x123", 50, 60)
        await client.close_window("0x123")
        await client.focus_window("0x123")

        await asyncio.sleep(0.05)
        self.assertEqual(len(self.server_commands), 8)
        self.assertEqual(self.server_commands[0]["command"], "push_window")
        self.assertEqual(self.server_commands[1]["command"], "push_window_impulse")
        self.assertEqual(self.server_commands[2]["command"], "inject_click")
        self.assertEqual(self.server_commands[3]["command"], "inject_mouse_move")
        self.assertEqual(self.server_commands[4]["command"], "move_active")
        self.assertEqual(self.server_commands[5]["command"], "resize_window")
        self.assertEqual(self.server_commands[6]["command"], "close_window")
        self.assertEqual(self.server_commands[7]["command"], "focus_window")

        await client.close()

    def test_ipc_client_jitter_calculation(self):
        client = IPCClient()
        self.assertEqual(client.calculate_jitter_ms(), 0.0)
        client.frame_timestamps = [10.0]
        self.assertEqual(client.calculate_jitter_ms(), 0.0)
        client.frame_timestamps = [10.0, 10.016, 10.033, 10.050]
        jitter = client.calculate_jitter_ms()
        self.assertGreaterEqual(jitter, 0.0)

    async def test_ipc_client_background_stream_and_queue(self):
        broadcast_path = f"/tmp/jarvis_bcast_{os.getpid()}_{int(time.time()*1000)}.sock"
        async def bcast_handler(reader, writer):
            for i in range(5):
                packet = json.dumps({"timestamp": time.time(), "index": i}) + "\n"
                writer.write(packet.encode("utf-8"))
                await writer.drain()
                await asyncio.sleep(0.01)
            await asyncio.sleep(0.1)
            writer.close()
            await writer.wait_closed()

        bcast_server = await asyncio.start_unix_server(bcast_handler, path=broadcast_path)
        client = IPCClient(socket_path=broadcast_path)
        await client.connect()

        received_cbs = []
        client.register_callback(lambda frame: received_cbs.append(frame))
        client.start_background_stream()

        await asyncio.sleep(0.15)
        self.assertIsNotNone(client.get_latest_frame())
        self.assertGreater(len(received_cbs), 0)

        await client.close()
        bcast_server.close()
        await bcast_server.wait_closed()
        if os.path.exists(broadcast_path):
            os.remove(broadcast_path)

class TestVisualCoordinatorUnit(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.coordinator = VisualCoordinator(
            socket_path="/tmp/jarvis_coordinator_mock.sock",
            fps=60.0,
            screen_width=1920,
            screen_height=1200,
        )

    def test_coordinator_initialization(self):
        self.assertAlmostEqual(self.coordinator.fps, 60.0)
        self.assertAlmostEqual(self.coordinator.dt, 1.0 / 60.0)
        self.assertEqual(self.coordinator.screen_width, 1920)
        self.assertEqual(self.coordinator.screen_height, 1200)
        self.assertFalse(self.coordinator.running)
        self.assertEqual(self.coordinator.avatar_x, 960.0)
        self.assertEqual(self.coordinator.avatar_y, 600.0)

    def test_coordinator_tick_without_frame(self):
        res = self.coordinator.tick(frame=None, dt=1.0 / 60.0)
        self.assertEqual(res["frames_processed"], 1)
        self.assertIn("avatar_pos", res)
        self.assertIn("hip_pos", res)
        self.assertIn("knee_left", res)
        self.assertIn("ankle_left", res)
        self.assertIn("mesh_bounds", res)
        self.assertIn("gaze", res)

    def test_coordinator_tick_with_telemetry_frame(self):
        frame = {
            "timestamp": 123456.78,
            "cursor": {"x": 800, "y": 450, "z": 0.0},
            "active_window": {
                "address": "0x5616a03008b0",
                "at": [200, 300],
                "size": [800, 600],
                "top_ledge": {
                    "start": [200.0, 300.0, 0.0],
                    "end": [1000.0, 300.0, 0.0],
                },
            },
        }
        res = self.coordinator.tick(frame=frame, dt=1.0 / 60.0)
        self.assertEqual(self.coordinator.gaze_x, 800.0)
        self.assertEqual(self.coordinator.gaze_y, 450.0)
        self.assertEqual(self.coordinator.avatar_y, 300.0)
        self.assertEqual(self.coordinator.current_window_address, "0x5616a03008b0")
        self.assertGreaterEqual(self.coordinator.avatar_x, 200.0)
        self.assertLessEqual(self.coordinator.avatar_x, 1000.0)
        self.assertEqual(res["frames_processed"], 1)

    async def test_coordinator_interact_push_and_click(self):
        sock_path = f"/tmp/jarvis_coord_cmd_{os.getpid()}_{int(time.time()*1000)}.sock"
        received_commands = []

        async def cmd_server_handler(reader, writer):
            while True:
                line = await reader.readline()
                if not line:
                    break
                try:
                    cmd = json.loads(line.decode("utf-8").strip())
                    received_commands.append(cmd)
                except Exception:
                    pass
            writer.close()
            await writer.wait_closed()

        srv = await asyncio.start_unix_server(cmd_server_handler, path=sock_path)
        client = IPCClient(socket_path=sock_path)
        await client.connect()

        coord = VisualCoordinator(ipc_client=client)
        coord.current_window_address = "0x999"
        await coord.interact_push_window(30, -10)
        await coord.interact_click("0xC0")

        await asyncio.sleep(0.05)
        self.assertEqual(len(received_commands), 2)
        self.assertEqual(received_commands[0]["command"], "push_window")
        self.assertEqual(received_commands[0]["target_address"], "0x999")
        self.assertEqual(received_commands[1]["command"], "inject_click")

        await client.close()
        srv.close()
        await srv.wait_closed()
        if os.path.exists(sock_path):
            os.remove(sock_path)

if __name__ == "__main__":
    unittest.main()

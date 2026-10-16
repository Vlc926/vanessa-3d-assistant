import unittest
import asyncio
import os
import time
import math
import numpy as np
from tests.test_doubles.loader import (
    get_socket_reader_class,
    get_hypr_client_class,
    get_geometry_projector_class,
    get_actuator_class,
    get_ipc_server_class,
    get_ipc_client_class,
    get_two_bone_ik_class,
    get_foot_lock_class,
    get_ledge_physics_class,
    get_procedural_motion_class,
    get_overlay_window_class
)

class TestTier4DesktopSessions(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.sock_path = f"/tmp/jarvis_test_t4_{os.getpid()}_{int(time.time()*1000)}.sock"
        server_cls = get_ipc_server_class()
        self.server = server_cls(socket_path=self.sock_path, fps=60)
        await self.server.start()

    async def asyncTearDown(self):
        await self.server.stop()
        if os.path.exists(self.sock_path):
            try:
                os.remove(self.sock_path)
            except OSError:
                pass

    def test_tier4_scenario1_desktop_startup_and_window_perching(self):
        reader_cls = get_socket_reader_class()
        projector_cls = get_geometry_projector_class()
        ik_cls = get_two_bone_ik_class()
        lock_cls = get_foot_lock_class()
        physics_cls = get_ledge_physics_class()

        reader = reader_cls()
        projector = projector_cls(screen_w=1920, screen_h=1200)
        solver = ik_cls(l1=0.42, l2=0.40)
        lock = lock_cls(l1=0.42, l2=0.40)
        physics = physics_cls()

        event_str = "openwindow>>5616a03008b0,1,foot,foot terminal\nactivewindowv2>>5616a03008b0\n"
        events = reader.feed_data(event_str)
        self.assertEqual(len(events), 2)

        client = {
            "address": "0x5616a03008b0",
            "at": [300, 200],
            "size": [800, 600],
            "title": "foot terminal",
            "floating": False,
            "focusHistoryID": 0
        }
        proj = projector.project_client(client, is_active=True)
        ledge = proj["top_ledge"]
        rail_y = ledge["start"][1]
        rail_x = (ledge["start"][0] + ledge["end"][0]) / 2.0

        platforms = [{"x_min": ledge["start"][0], "x_max": ledge["end"][0], "y_top": rail_y}]
        physics.pos = np.array([rail_x, rail_y, 0.0])
        physics.state = "GROUNDED"
        physics.step(1.0/60.0, platforms)
        self.assertEqual(physics.state, "GROUNDED")

        foot_target = np.array([rail_x, rail_y, 0.0])
        hip_root = np.array([rail_x, rail_y + 0.78, 0.0])
        _, _, foot_pos = solver.solve(hip_root, foot_target, [0.0, 0.0, 1.0])
        self.assertAlmostEqual(foot_pos[1], rail_y, delta=1e-3)

        lock.plant_foot(foot_pos, [rail_x, rail_y, 0.0])
        self.assertEqual(lock.state, "STANCE")

    def test_tier4_scenario2_interactive_window_dragging_and_foot_locking(self):
        lock_cls = get_foot_lock_class()
        ik_cls = get_two_bone_ik_class()

        lock = lock_cls(l1=0.42, l2=0.40, hip_rest_y=0.82)
        solver = ik_cls(l1=0.42, l2=0.40)

        window_pos = np.array([200.0, 300.0, 0.0])
        initial_foot = np.array([250.0, 300.0, 0.0])
        lock.plant_foot(initial_foot, window_pos)
        self.assertEqual(lock.state, "STANCE")

        for tick in range(120):
            window_pos[0] += 2.0 * math.sin(tick * 0.05)
            window_pos[1] += 0.5 * math.cos(tick * 0.05)

            world_foot = lock.get_world_foot_pos(window_pos)
            expected_foot = window_pos + lock.local_anchor
            slip = float(np.linalg.norm(world_foot - expected_foot))
            self.assertEqual(slip, 0.0)

            hip = lock.update_hip_position(window_pos, pelvis_x=window_pos[0] + 50.0)
            self.assertFalse(np.isnan(hip).any())

            _, p_knee, p_ankle = solver.solve(hip, world_foot, [0.0, 0.0, 1.0])
            self.assertFalse(np.isnan(p_knee).any())
            self.assertFalse(np.isnan(p_ankle).any())

    def test_tier4_scenario3_sudden_window_kill_imbalance_free_fall_and_crouch_landing(self):
        reader_cls = get_socket_reader_class()
        physics_cls = get_ledge_physics_class()
        reader = reader_cls()
        physics = physics_cls(gravity=-18.5)

        platforms = [{"x_min": -2.0, "x_max": 2.0, "y_top": 5.0}]
        physics.pos = np.array([0.0, 5.0, 0.0])
        physics.state = "GROUNDED"
        physics.step(1.0/60.0, platforms)
        self.assertEqual(physics.state, "GROUNDED")

        events = reader.feed_data("closewindow>>5616a03008b0\n")
        self.assertEqual(len(events), 1)
        platforms.clear()

        physics.step(1.0/60.0, platforms)
        self.assertEqual(physics.state, "IMBALANCE")

        for _ in range(30):
            physics.step(1.0/60.0, platforms)
        self.assertEqual(physics.state, "FREE_FALL")

        while physics.state == "FREE_FALL":
            physics.step(1.0/60.0, platforms)

        self.assertEqual(physics.state, "LANDING")
        self.assertEqual(physics.pos[1], 0.0)
        self.assertGreaterEqual(physics.landing_impact_speed, 8.0)

        for _ in range(30):
            physics.step(1.0/60.0, platforms)
        self.assertEqual(physics.state, "GROUNDED")

    def test_tier4_scenario4_cursor_wandering_and_procedural_head_eye_tracking(self):
        motion_cls = get_procedural_motion_class()
        motion = motion_cls(omega=8.0)

        screen_positions = [
            (960, 600),
            (200, 200),
            (1800, 300),
            (100, 1000),
            (1700, 1100),
            (960, 600)
        ]

        for (cx, cy) in screen_positions:
            norm_x = (cx - 960) / 960.0
            target_angle = norm_x * math.radians(60.0)

            for step in range(20):
                t = float(step) * (1.0 / 60.0)
                gaze = motion.update_gaze_spring(target_angle, dt=1.0/60.0)
                jx, jy = motion.update_ocular_saccades(t)
                chest, clavicle = motion.update_breathing(dt=1.0/60.0)

                self.assertFalse(math.isnan(gaze))
                self.assertFalse(math.isnan(jx))
                self.assertFalse(math.isnan(jy))
                self.assertFalse(math.isnan(chest))
                self.assertFalse(math.isnan(clavicle))

        self.assertAlmostEqual(motion.gaze_angle, 0.0, delta=0.1)

    async def test_tier4_scenario5_full_60hz_client_server_telemetry_and_push_interaction(self):
        client_cls = get_ipc_client_class()
        actuator_cls = get_actuator_class()
        client = client_cls(socket_path=self.sock_path)
        actuator = actuator_cls(execute_real=False)

        await client.connect()

        window_addr = "0x5616a03008b0"
        win_x = 200
        win_y = 150

        for frame_idx in range(60):
            if frame_idx == 20:
                push_cmd = {
                    "command": "push_window",
                    "target_address": window_addr,
                    "delta": [50, 0]
                }
                await client.send_command(push_cmd)

            if len(self.server.received_commands) > 0:
                latest = self.server.received_commands.pop(0)
                if latest.get("command") == "push_window":
                    actuator.push_window(latest["target_address"], latest["delta"][0], latest["delta"][1])
                    win_x += latest["delta"][0]
                    win_y += latest["delta"][1]

            active_win = {
                "address": window_addr,
                "at": [win_x, win_y],
                "size": [800, 600],
                "top_ledge": {
                    "start": [float(win_x), float(win_y), 0.0],
                    "end": [float(win_x + 800), float(win_y), 0.0]
                }
            }
            packet = self.server.build_telemetry_packet(active_window=active_win)
            await self.server.broadcast_frame(packet)

            received = await client.read_next_frame(timeout=0.5)
            self.assertIsNotNone(received)
            await asyncio.sleep(0.005)

        self.assertEqual(win_x, 250)
        self.assertGreater(len(actuator.recorded_dispatches), 0)
        self.assertIn("50 0,address:0x5616a03008b0", actuator.recorded_dispatches[0]["args"])
        await client.close()

if __name__ == "__main__":
    unittest.main()

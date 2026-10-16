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
    get_vision_services_class
)

class TestTier3CrossFeatures(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.sock_path = f"/tmp/jarvis_test_t3_{os.getpid()}_{int(time.time()*1000)}.sock"
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

    def test_pairwise_socket2_event_to_geometry_projection(self):
        reader_cls = get_socket_reader_class()
        projector_cls = get_geometry_projector_class()
        reader = reader_cls()
        projector = projector_cls(screen_w=1920, screen_h=1200)

        raw_event = "openwindow>>5616a03008b0,1,foot,foot terminal\n"
        events = reader.feed_data(raw_event)
        self.assertEqual(len(events), 1)
        ev = events[0]

        client_mock = {
            "address": ev["address"],
            "at": [200, 150],
            "size": [800, 600],
            "title": ev["title"],
            "floating": False,
            "focusHistoryID": 0
        }
        proj = projector.project_client(client_mock, is_active=True)
        self.assertEqual(proj["address"], "0x5616a03008b0")
        self.assertIn("top_ledge", proj)
        self.assertAlmostEqual(proj["top_ledge"]["start"][1], proj["top_ledge"]["end"][1], delta=1e-3)

    def test_pairwise_geometry_projection_to_ik_and_foot_lock(self):
        projector_cls = get_geometry_projector_class()
        ik_cls = get_two_bone_ik_class()
        lock_cls = get_foot_lock_class()

        projector = projector_cls(screen_w=1920, screen_h=1200)
        solver = ik_cls(l1=0.42, l2=0.40)
        lock = lock_cls(l1=0.42, l2=0.40)

        client = {"address": "0x1", "at": [400, 200], "size": [600, 400], "floating": True}
        proj = projector.project_client(client, is_active=True)
        ledge_y = proj["top_ledge"]["start"][1]
        ledge_x = proj["top_ledge"]["start"][0] + 0.1

        target_foot = np.array([ledge_x, ledge_y, 0.0])
        hip_root = np.array([ledge_x, ledge_y + 0.75, 0.0])
        _, _, p_ankle = solver.solve(hip_root, target_foot, [0.0, 0.0, 1.0])
        self.assertAlmostEqual(float(p_ankle[1]), ledge_y, delta=1e-3)

        lock.plant_foot(p_ankle, [ledge_x, ledge_y, 0.0])
        self.assertEqual(lock.state, "STANCE")

    def test_pairwise_moving_window_to_strict_foot_locking(self):
        lock_cls = get_foot_lock_class()
        lock = lock_cls(l1=0.42, l2=0.40)

        window_pos = np.array([300.0, 200.0, 0.0])
        foot_world = np.array([350.0, 200.0, 0.0])
        lock.plant_foot(foot_world, window_pos)

        for step in range(60):
            window_pos[0] += 5.0
            window_pos[1] += 2.0
            current_foot = lock.get_world_foot_pos(window_pos)
            slip = float(np.linalg.norm(current_foot - (window_pos + lock.local_anchor)))
            self.assertEqual(slip, 0.0)

    def test_pairwise_window_close_event_to_ledge_free_fall(self):
        reader_cls = get_socket_reader_class()
        physics_cls = get_ledge_physics_class()
        reader = reader_cls()
        physics = physics_cls()

        platforms = [{"x_min": -1.0, "x_max": 1.0, "y_top": 2.0}]
        physics.pos = np.array([0.0, 2.0, 0.0])
        physics.state = "GROUNDED"
        physics.step(1.0/60.0, platforms)
        self.assertEqual(physics.state, "GROUNDED")

        close_event = "closewindow>>5616a03008b0\n"
        reader.feed_data(close_event)
        platforms.clear()

        physics.step(1.0/60.0, platforms)
        self.assertEqual(physics.state, "IMBALANCE")

        physics.step(0.50, platforms)
        self.assertEqual(physics.state, "FREE_FALL")

    def test_pairwise_cursor_query_to_cervical_gaze_tracking(self):
        client_cls = get_hypr_client_class()
        motion_cls = get_procedural_motion_class()
        hypr = client_cls()
        motion = motion_cls(omega=8.0)

        hypr.set_mock_cursor(1440, 600)
        cx, cy = hypr.get_cursor_position()
        norm_x = (cx - 960) / 960.0
        target_yaw = norm_x * math.radians(45.0)

        for _ in range(60):
            motion.update_gaze_spring(target_yaw, dt=1.0/60.0)

        self.assertAlmostEqual(motion.gaze_angle, target_yaw, delta=0.05)

    async def test_pairwise_ipc_streaming_server_to_client(self):
        client_cls = get_ipc_client_class()
        client = client_cls(socket_path=self.sock_path)
        await client.connect()

        packet = self.server.build_telemetry_packet(cursor={"x": 512, "y": 384, "z": 0.0})
        await self.server.broadcast_frame(packet)

        frame = await client.read_next_frame(timeout=1.0)
        self.assertIsNotNone(frame)
        self.assertEqual(frame["cursor"]["x"], 512)
        self.assertEqual(frame["cursor"]["y"], 384)
        await client.close()

    async def test_pairwise_engine_command_to_actuator_dispatch(self):
        client_cls = get_ipc_client_class()
        actuator_cls = get_actuator_class()
        client = client_cls(socket_path=self.sock_path)
        actuator = actuator_cls(execute_real=False)

        await client.connect()
        cmd = {
            "command": "push_window",
            "target_address": "0x5616a03008b0",
            "delta": [40, 15]
        }
        await client.send_command(cmd)
        await asyncio.sleep(0.05)

        self.assertGreater(len(self.server.received_commands), 0)
        received = self.server.received_commands[-1]
        act_res = actuator.push_window(received["target_address"], received["delta"][0], received["delta"][1])
        self.assertEqual(act_res["status"], "ok")
        self.assertIn("40 15,address:0x5616a03008b0", act_res["executed"])
        await client.close()

    def test_pairwise_vision_capture_deduplication_and_behavior_state(self):
        vision_cls = get_vision_services_class()
        vision = vision_cls(offline_mode=True)

        cmd = vision.build_grim_command(0, 0, 1920, 1080)
        self.assertEqual(cmd[0], "grim")

        h_code = 0x1111222233334444
        skip1 = vision.should_skip_ai_analysis(h_code)
        self.assertFalse(skip1)
        summary1 = vision.generate_context_summary(activity="coding", mood="deep_focus")
        self.assertEqual(summary1["recommended_state"], "perch")

        h_video = 0x9999888877776666
        skip2 = vision.should_skip_ai_analysis(h_video)
        self.assertFalse(skip2)
        summary2 = vision.generate_context_summary(activity="video", mood="leisure")
        self.assertEqual(summary2["recommended_state"], "wander")

if __name__ == "__main__":
    unittest.main()

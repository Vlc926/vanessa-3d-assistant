import math
import random
import unittest
from typing import Any, Dict, List
from src.perception.geometry_projector import GeometryProjector
from src.perception.actuator import Actuator

class TestChallengerM12Stress(unittest.TestCase):
    def setUp(self) -> None:
        random.seed(1337)
        self.resolutions = [
            (1280, 720),
            (1920, 1080),
            (1920, 1200),
            (2560, 1440),
            (3840, 2160),
            (3440, 1440),
            (5120, 1440)
        ]

    def test_stress_10000_topologies_across_resolutions(self) -> None:
        total_topologies = 10000
        total_planes_checked = 0
        total_windows_created = 0

        for i in range(total_topologies):
            w, h = self.resolutions[i % len(self.resolutions)]
            gp = GeometryProjector(w, h)
            num_clients = random.randint(0, 6)
            clients: List[Dict[str, Any]] = []

            for j in range(num_clients):
                client = {
                    "address": f"0x{random.randint(0, 0xFFFFFFFF):x}",
                    "title": f"win_{i}_{j}",
                    "class": f"class_{i}_{j}",
                    "at": [random.randint(-500, w + 500), random.randint(-500, h + 500)],
                    "size": [random.randint(0, w + 200), random.randint(0, h + 200)],
                    "workspace": {"id": random.randint(1, 5)} if (j % 2 == 0) else random.randint(1, 5),
                    "floating": bool(j % 2),
                    "pinned": bool(j % 3 == 0),
                    "fullscreen": j % 3,
                    "focusHistoryID": j,
                    "mapped": True,
                    "hidden": False
                }
                clients.append(client)

            total_windows_created += num_clients
            active_addr = clients[0]["address"] if clients else ""
            cursor_pos = {
                "x": random.uniform(-100.0, float(w + 100)),
                "y": random.uniform(-100.0, float(h + 100)),
                "z": 0.0
            }

            frame = gp.project_frame(
                clients=clients,
                cursor=cursor_pos,
                active_address=active_addr,
                include_borders=True,
                include_scrollbar=True
            )

            self.assertIn("timestamp", frame)
            self.assertIn("cursor", frame)
            self.assertIn("collision_planes", frame)
            self.assertIn("action_feedback", frame)

            for plane in frame["collision_planes"]:
                total_planes_checked += 1
                bounds = plane["bounds"]
                self.assertLessEqual(bounds[0], bounds[1])
                self.assertLessEqual(bounds[2], bounds[3])
                self.assertLessEqual(bounds[4], bounds[5])

                eqn = plane["plane"]
                self.assertEqual(len(eqn), 4)
                norm_len = math.hypot(eqn[0], eqn[1], eqn[2])
                self.assertAlmostEqual(norm_len, 1.0, delta=1e-4)
                self.assertFalse(math.isnan(eqn[3]))
                self.assertFalse(math.isinf(eqn[3]))

            if frame["active_window"] and "top_ledge" in frame["active_window"]:
                ledge = frame["active_window"]["top_ledge"]
                self.assertAlmostEqual(ledge["start"][1], ledge["end"][1], delta=1e-4)
                self.assertLessEqual(ledge["start"][0], ledge["end"][0])
                self.assertAlmostEqual(ledge["start"][2], ledge["end"][2], delta=1e-4)

        self.assertGreater(total_planes_checked, total_topologies)
        self.assertGreater(total_windows_created, total_topologies)

    def test_mathematical_bijectivity_continuous_and_discrete(self) -> None:
        max_forward_error = 0.0
        max_inverse_error = 0.0

        for w, h in self.resolutions:
            gp = GeometryProjector(w, h)

            for _ in range(1500):
                px = random.uniform(0.0, float(w))
                py = random.uniform(0.0, float(h))

                x3d = ((px / gp.screen_w) - 0.5) * gp.w3d
                y3d = (0.5 - (py / gp.screen_h)) * gp.h3d

                r_px = ((x3d / gp.w3d) + 0.5) * gp.screen_w
                r_py = (0.5 - (y3d / gp.h3d)) * gp.screen_h

                err_x = abs(px - r_px)
                err_y = abs(py - r_py)
                max_forward_error = max(max_forward_error, err_x, err_y)
                self.assertLess(err_x, 1e-10)
                self.assertLess(err_y, 1e-10)

                rx3d = ((r_px / gp.screen_w) - 0.5) * gp.w3d
                ry3d = (0.5 - (r_py / gp.screen_h)) * gp.h3d

                inv_err_x = abs(x3d - rx3d)
                inv_err_y = abs(y3d - ry3d)
                max_inverse_error = max(max_inverse_error, inv_err_x, inv_err_y)
                self.assertLess(inv_err_x, 1e-10)
                self.assertLess(inv_err_y, 1e-10)

            step_x = max(1, w // 40)
            step_y = max(1, h // 40)
            for ipx in range(0, w + 1, step_x):
                for ipy in range(0, h + 1, step_y):
                    p3d = gp.pixel_to_3d(ipx, ipy)
                    rec_px, rec_py = gp.point_3d_to_pixel(p3d[0], p3d[1])
                    self.assertEqual(ipx, rec_px)
                    self.assertEqual(ipy, rec_py)

        self.assertLess(max_forward_error, 1e-10)
        self.assertLess(max_inverse_error, 1e-10)

    def test_physics_impulse_decay_monotonicity_and_stopping(self) -> None:
        act = Actuator(execute_real=False)
        dt = 1.0 / 60.0

        for trial in range(50):
            act.active_impulses.clear()
            addr = f"0x{trial:04x}"
            impulse_x = random.uniform(-4000.0, 4000.0)
            impulse_y = random.uniform(-4000.0, 4000.0)
            if math.hypot(impulse_x, impulse_y) < 50.0:
                impulse_x = 500.0
                impulse_y = 500.0

            mass = random.uniform(15.0, 90.0)
            friction = random.uniform(4.0, 14.0)

            expected_disp = act.compute_impulse_displacement(
                (impulse_x, impulse_y),
                window_mass=mass,
                friction=friction
            )

            act.add_window_impulse(
                addr,
                (impulse_x, impulse_y),
                window_mass=mass,
                friction=friction
            )

            prev_speed = math.hypot(
                act.active_impulses[addr].vx,
                act.active_impulses[addr].vy
            )

            total_dx = 0
            total_dy = 0
            stopped = False
            stopped_at_step = 0

            for step in range(1000):
                displacements = act.step_physics(dt)
                for d_addr, dx, dy in displacements:
                    if d_addr == addr:
                        total_dx += dx
                        total_dy += dy

                if addr in act.active_impulses:
                    cur_speed = math.hypot(
                        act.active_impulses[addr].vx,
                        act.active_impulses[addr].vy
                    )
                    self.assertLessEqual(cur_speed, prev_speed + 1e-12)
                    prev_speed = cur_speed
                else:
                    stopped = True
                    stopped_at_step = step + 1
                    break

            self.assertTrue(stopped)
            self.assertLess(stopped_at_step, 1000)
            self.assertAlmostEqual(float(total_dx), expected_disp[0], delta=2.0)
            self.assertAlmostEqual(float(total_dy), expected_disp[1], delta=2.0)

    def test_actuator_edge_cases_and_variable_dt(self) -> None:
        act = Actuator(execute_real=False)

        act.add_window_impulse("0xsafe", (100.0, 50.0), window_mass=-5.0, friction=-2.0)
        self.assertIn("0xsafe", act.active_impulses)
        st = act.active_impulses["0xsafe"]
        self.assertGreaterEqual(st.mass, 1.0)
        self.assertGreaterEqual(st.friction, 0.1)

        act.active_impulses.clear()
        act.add_window_impulse("0xjitter", (1000.0, 1000.0), 50.0, 8.0)
        prev_spd = math.hypot(act.active_impulses["0xjitter"].vx, act.active_impulses["0xjitter"].vy)
        for _ in range(500):
            var_dt = random.uniform(0.005, 0.040)
            act.step_physics(var_dt)
            if "0xjitter" in act.active_impulses:
                cur_spd = math.hypot(act.active_impulses["0xjitter"].vx, act.active_impulses["0xjitter"].vy)
                self.assertLessEqual(cur_spd, prev_spd + 1e-12)
                prev_spd = cur_spd
            else:
                break
        self.assertNotIn("0xjitter", act.active_impulses)

if __name__ == "__main__":
    unittest.main()

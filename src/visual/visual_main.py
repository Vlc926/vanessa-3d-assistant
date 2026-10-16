import argparse
import asyncio
import os
import signal
import sys
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

try:
    from src.visual.overlay_window import OverlayWindow
except Exception:
    from tests.test_doubles.double_overlay_window import OverlayWindowDouble as OverlayWindow

try:
    from src.visual.two_bone_ik import TwoBoneIKSolver
except Exception:
    from tests.test_doubles.double_two_bone_ik import TwoBoneIKSolverDouble as TwoBoneIKSolver

try:
    from src.visual.foot_lock import FootLockController
except Exception:
    from tests.test_doubles.double_foot_lock import FootLockControllerDouble as FootLockController

from src.visual.ipc_client import IPCClient

class VisualCoordinator:
    def __init__(
        self,
        ipc_client: Optional[IPCClient] = None,
        overlay: Optional[OverlayWindow] = None,
        ik_solver: Optional[TwoBoneIKSolver] = None,
        foot_lock: Optional[FootLockController] = None,
        socket_path: Optional[str] = None,
        fps: float = 60.0,
        screen_width: int = 1920,
        screen_height: int = 1200,
    ) -> None:
        self.fps = float(fps)
        self.dt = 1.0 / self.fps
        self.screen_width = int(screen_width)
        self.screen_height = int(screen_height)
        self.running: bool = False

        self.ipc_client = ipc_client if ipc_client is not None else IPCClient(socket_path=socket_path)
        self.overlay = overlay if overlay is not None else OverlayWindow(layer=3, width=self.screen_width, height=self.screen_height)
        self.ik_solver = ik_solver if ik_solver is not None else TwoBoneIKSolver(l1=0.42, l2=0.40)
        self.foot_lock = foot_lock if foot_lock is not None else FootLockController(l1=0.42, l2=0.40, hip_rest_y=0.82)

        self.avatar_x: float = float(screen_width) / 2.0
        self.avatar_y: float = float(screen_height) / 2.0
        self.avatar_width: float = 80.0
        self.avatar_height: float = 120.0
        self.gaze_x: float = self.avatar_x
        self.gaze_y: float = self.avatar_y

        self.current_window_address: str = ""
        self.frames_processed: int = 0
        self.last_tick_time: float = 0.0

    def tick(
        self,
        frame: Optional[Dict[str, Any]] = None,
        dt: Optional[float] = None,
    ) -> Dict[str, Any]:
        delta_t = self.dt if dt is None else float(dt)
        self.last_tick_time = time.time()

        if frame is not None:
            cursor = frame.get("cursor", {})
            if cursor:
                self.gaze_x = float(cursor.get("x", self.gaze_x))
                self.gaze_y = float(cursor.get("y", self.gaze_y))

            active_win = frame.get("active_window", {})
            if active_win:
                self.current_window_address = str(active_win.get("address", ""))
                top_ledge = active_win.get("top_ledge", {})
                start = top_ledge.get("start", [0.0, 0.0, 0.0])
                end = top_ledge.get("end", [100.0, 0.0, 0.0])

                ledge_y = float(start[1])
                self.avatar_y = ledge_y

                min_x = min(float(start[0]), float(end[0]))
                max_x = max(float(start[0]), float(end[0]))
                if self.avatar_x < min_x:
                    self.avatar_x = min_x
                elif self.avatar_x > max_x:
                    self.avatar_x = max_x

                win_pos = np.array([start[0], start[1], start[2]], dtype=np.float64)
                current_foot = self.foot_lock.get_world_foot_pos(win_pos)
                hip_pos = self.foot_lock.update_hip_position(win_pos, self.avatar_x, dt=delta_t)

                v_pole = np.array([0.0, 0.40, 1.0], dtype=np.float64)
                target_left = current_foot + np.array([-0.05, 0.0, 0.0])
                target_right = current_foot + np.array([0.05, 0.0, 0.0])
                _, knee_l, ankle_l = self.ik_solver.solve(hip_pos, target_left, v_pole)
                _, knee_r, ankle_r = self.ik_solver.solve(hip_pos, target_right, v_pole)
            else:
                hip_pos = np.array([self.avatar_x, self.avatar_y - 0.82, 0.0], dtype=np.float64)
                knee_l = hip_pos + np.array([-0.05, -0.42, 0.1])
                ankle_l = knee_l + np.array([0.0, -0.40, -0.1])
                knee_r = hip_pos + np.array([0.05, -0.42, 0.1])
                ankle_r = knee_r + np.array([0.0, -0.40, -0.1])
        else:
            hip_pos = np.array([self.avatar_x, self.avatar_y - 0.82, 0.0], dtype=np.float64)
            knee_l = hip_pos + np.array([-0.05, -0.42, 0.1])
            ankle_l = knee_l + np.array([0.0, -0.40, -0.1])
            knee_r = hip_pos + np.array([0.05, -0.42, 0.1])
            ankle_r = knee_r + np.array([0.0, -0.40, -0.1])

        mesh_x = int(self.avatar_x - self.avatar_width / 2.0)
        mesh_y = int(self.avatar_y - self.avatar_height)
        mesh_w = int(self.avatar_width)
        mesh_h = int(self.avatar_height)
        self.overlay.update_avatar_mesh_bounds([(mesh_x, mesh_y, mesh_w, mesh_h)])
        self.overlay.poll_events()

        self.frames_processed += 1
        return {
            "avatar_pos": (self.avatar_x, self.avatar_y),
            "hip_pos": list(hip_pos),
            "knee_left": list(knee_l),
            "ankle_left": list(ankle_l),
            "knee_right": list(knee_r),
            "ankle_right": list(ankle_r),
            "mesh_bounds": (mesh_x, mesh_y, mesh_w, mesh_h),
            "gaze": (self.gaze_x, self.gaze_y),
            "frames_processed": self.frames_processed,
        }

    async def interact_push_window(self, delta_x: int, delta_y: int) -> None:
        if self.current_window_address:
            await self.ipc_client.push_window(self.current_window_address, delta_x, delta_y)

    async def interact_click(self, button: str = "0xC0") -> None:
        await self.ipc_client.inject_click(button)

    async def run(self) -> None:
        self.running = True
        loop = asyncio.get_running_loop()
        stop_event = asyncio.Event()

        def signal_handler() -> None:
            stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, signal_handler)
            except (NotImplementedError, RuntimeError):
                pass

        await self.ipc_client.connect()
        self.ipc_client.start_background_stream()

        start_mono = time.monotonic()
        frame_idx = 0

        while self.running and not stop_event.is_set():
            frame_idx += 1
            target_mono = start_mono + (frame_idx * self.dt)

            frame = self.ipc_client.get_latest_frame()
            if frame is not None:
                self.tick(frame, dt=self.dt)

            delay = target_mono - time.monotonic()
            if delay > 0.001:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=delay)
                    break
                except (asyncio.TimeoutError, TimeoutError):
                    pass
            else:
                await asyncio.sleep(0)

        self.running = False
        await self.ipc_client.close()

def main() -> None:
    parser = argparse.ArgumentParser(description="Jarvis Visual Engine Coordinator")
    parser.add_argument("--socket-path", type=str, default=None)
    parser.add_argument("--fps", type=float, default=60.0)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1200)
    args = parser.parse_args()

    coordinator = VisualCoordinator(
        socket_path=args.socket_path,
        fps=args.fps,
        screen_width=args.width,
        screen_height=args.height,
    )
    asyncio.run(coordinator.run())

if __name__ == "__main__":
    main()

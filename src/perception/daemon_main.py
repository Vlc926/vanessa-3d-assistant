import argparse
import asyncio
import os
import signal
import sys
from typing import Any, Dict, Optional

from src.perception.actuator import Actuator
from src.perception.geometry_projector import GeometryProjector, normalize_address
from src.perception.hypr_client import HyprClient
from src.perception.ipc_server import IPCServer
from src.perception.socket_reader import SocketReader
from src.perception.ai_connector import SemanticVisionConnector

class PerceptionDaemon:
    def __init__(
        self,
        ipc_socket_path: Optional[str] = None,
        target_fps: float = 60.0,
        execute_real: bool = True,
    ) -> None:
        self.target_fps = float(target_fps)
        self.dt = 1.0 / self.target_fps
        self.running: bool = False

        self.hypr_client = HyprClient()
        self.actuator = Actuator(execute_real=execute_real)
        self.projector = GeometryProjector()
        self.socket_reader = SocketReader(event_callback=self.on_hypr_event)
        self.ai_connector = SemanticVisionConnector()

        self.ipc_server = IPCServer(
            socket_path=ipc_socket_path,
            target_fps=self.target_fps,
            frame_provider=self.produce_frame,
            control_handler=self.handle_control_request,
        )

        self.cached_cursor: Dict[str, Any] = {"x": 0, "y": 0, "z": 0.0}
        self.cached_active_address: str = ""

    def on_hypr_event(self, event_name: str, event_data: str) -> None:
        if event_name in (
            "openwindow",
            "closewindow",
            "movewindow",
            "movewindowv2",
            "changefloatingmode",
            "fullscreen",
        ):
            self.projector.mark_dirty()
        elif event_name in ("activewindow", "activewindowv2"):
            if event_name == "activewindowv2":
                addr = event_data.strip()
                if addr:
                    addr_norm = normalize_address(addr)
                    self.cached_active_address = addr_norm
                    self.projector.set_active_address(addr_norm)
                else:
                    self.cached_active_address = ""
                    self.projector.set_active_address("")
            self.projector.mark_dirty()

    async def handle_control_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        cmd = message.get("command", "")
        if cmd == "push_window":
            target = message.get("target_address", "") or message.get("address", "")
            delta = message.get("delta", [0, 0])
            res = self.actuator.push_window(target, delta[0], delta[1])
            return {"status": "ok", "command": cmd, "result": res}

        elif cmd == "push_window_impulse":
            target = message.get("target_address", "") or message.get("address", "")
            impulse = message.get("impulse", [0.0, 0.0])
            mass = float(message.get("mass", 50.0))
            friction = float(message.get("friction", 8.0))
            self.actuator.add_window_impulse(target, (impulse[0], impulse[1]), mass, friction)
            return {"status": "ok", "command": cmd}

        elif cmd == "move_active":
            delta = message.get("delta", [0, 0])
            res = self.actuator.move_active(delta[0], delta[1])
            return {"status": "ok", "command": cmd, "result": res}

        elif cmd == "move_window_exact":
            target = message.get("target_address", "") or message.get("address", "")
            pos = message.get("pos", [0, 0])
            res = self.actuator.move_window_exact(target, pos[0], pos[1])
            return {"status": "ok", "command": cmd, "result": res}

        elif cmd == "resize_window":
            target = message.get("target_address", "") or message.get("address", "")
            delta = message.get("delta", [0, 0])
            res = self.actuator.resize_window(target, delta[0], delta[1])
            return {"status": "ok", "command": cmd, "result": res}

        elif cmd == "close_window":
            target = message.get("target_address", "") or message.get("address", "")
            res = self.actuator.close_window(target)
            return {"status": "ok", "command": cmd, "result": res}

        elif cmd == "focus_window":
            target = message.get("target_address", "") or message.get("address", "")
            res = self.actuator.focus_window(target)
            return {"status": "ok", "command": cmd, "result": res}

        elif cmd == "inject_mouse_move":
            x = int(message.get("x", 0))
            y = int(message.get("y", 0))
            absolute = bool(message.get("absolute", True))
            res = self.actuator.inject_pointer_move(x, y, absolute=absolute)
            return {"status": res.get("status", "ok"), "command": cmd}

        elif cmd == "inject_click":
            mask = str(message.get("button", "0xC0"))
            res = self.actuator.inject_pointer_click(mask)
            return {"status": res.get("status", "ok"), "command": cmd}

        return {"status": "error", "message": f"unknown_command_{cmd}"}

    async def produce_frame(self) -> Dict[str, Any]:
        cursor_data = self.hypr_client.get_cursor_pos()
        if cursor_data:
            self.cached_cursor = {
                "x": cursor_data.get("x", 0),
                "y": cursor_data.get("y", 0),
                "z": 0.0,
            }

        if self.projector.is_dirty:
            clients = self.hypr_client.get_clients()
            self.projector.update_clients(clients)

        displacements = self.actuator.step_physics(self.dt)
        for addr, dx, dy in displacements:
            self.actuator.push_window(addr, dx, dy)

        frame = self.projector.build_frame(self.cached_cursor)
        frame["action_feedback"] = self.actuator.get_action_feedback()
        active_w = frame.get("active_window")
        if active_w and isinstance(active_w, dict):
            sem = self.ai_connector.infer_intent_from_window(
                active_w.get("title", ""),
                active_w.get("class", "")
            )
            frame["intent"] = sem
        return frame

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

        clients = self.hypr_client.get_clients()
        self.projector.update_clients(clients)

        cursor = self.hypr_client.get_cursor_pos()
        if cursor:
            self.cached_cursor = {
                "x": cursor.get("x", 0),
                "y": cursor.get("y", 0),
                "z": 0.0,
            }

        socket_task = asyncio.create_task(self.socket_reader.listen())
        await self.ipc_server.start()

        await stop_event.wait()

        self.running = False
        socket_task.cancel()
        try:
            await socket_task
        except asyncio.CancelledError:
            pass

        await self.ipc_server.stop()

def main() -> None:
    parser = argparse.ArgumentParser(description="Jarvis Perception Daemon")
    parser.add_argument("--socket-path", type=str, default=None)
    parser.add_argument("--fps", type=float, default=60.0)
    args = parser.parse_args()

    daemon = PerceptionDaemon(
        ipc_socket_path=args.socket_path,
        target_fps=args.fps,
    )
    asyncio.run(daemon.run())

if __name__ == "__main__":
    main()

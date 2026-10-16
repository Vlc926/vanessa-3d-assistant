import asyncio
import json
import os
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

class IPCServer:
    def __init__(
        self,
        socket_path: Optional[str] = None,
        fps: float = 60.0,
        target_fps: float = 60.0,
        frame_provider: Optional[Callable[[], Awaitable[Dict[str, Any]]]] = None,
        control_handler: Optional[Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None,
    ) -> None:
        if socket_path is None:
            xdg = os.environ.get("XDG_RUNTIME_DIR", "/run/user/1000")
            self.socket_path = os.path.join(xdg, "jarvis", "perception_engine.sock")
        else:
            self.socket_path = socket_path

        self.fps = float(fps or target_fps)
        self.target_fps = self.fps
        self.interval = 1.0 / self.fps
        self.frame_interval = self.interval
        self.frame_provider = frame_provider
        self.control_handler = control_handler

        self.server: Optional[asyncio.Server] = None
        self.clients: Set[asyncio.StreamWriter] = set()
        self.running: bool = False
        self.is_running: bool = False
        self.broadcast_task: Optional[asyncio.Task[None]] = None

        self.latest_payload: Dict[str, Any] = {}
        self.received_commands: List[Dict[str, Any]] = []
        self.frames_sent: int = 0
        self.bytes_sent: int = 0
        self.last_broadcast_fps: float = 0.0

    def build_telemetry_packet(
        self,
        cursor: Optional[Dict[str, Any]] = None,
        active_window: Optional[Dict[str, Any]] = None,
        collision_planes: Optional[List[Dict[str, Any]]] = None,
        feedback: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ts = time.time()
        c = cursor if cursor is not None else {"x": 265, "y": 725, "z": 0.0}
        w = active_window if active_window is not None else {
            "address": "0x5616a03008b0",
            "title": "foot",
            "class": "foot",
            "at": [100, 150],
            "size": [800, 600],
            "workspace": 1,
            "z_depth": 0.0,
            "top_ledge": {
                "start": [100.0, 150.0, 0.0],
                "end": [900.0, 150.0, 0.0],
            },
        }
        cp = collision_planes if collision_planes is not None else [
            {
                "id": "0x5616a03008b0",
                "type": "window_top",
                "plane": [0.0, 1.0, 0.0, -150.0],
                "bounds": [100.0, 900.0, 150.0, 150.0, -0.1, 0.1],
            }
        ]
        fb = feedback if feedback is not None else {"last_action": "none", "status": "ok"}
        return {
            "timestamp": ts,
            "cursor": c,
            "active_window": w,
            "collision_planes": cp,
            "action_feedback": fb,
        }

    async def start(self) -> None:
        socket_dir = os.path.dirname(os.path.abspath(self.socket_path))
        os.makedirs(socket_dir, exist_ok=True)
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except OSError:
                pass

        self.server = await asyncio.start_unix_server(
            self._handle_client,
            path=self.socket_path,
        )
        self.running = True
        self.is_running = True

        if self.frame_provider is not None:
            self.broadcast_task = asyncio.create_task(self._broadcast_loop())

    async def stop(self) -> None:
        self.running = False
        self.is_running = False

        if self.broadcast_task is not None:
            self.broadcast_task.cancel()
            try:
                await self.broadcast_task
            except asyncio.CancelledError:
                pass
            self.broadcast_task = None

        for writer in list(self.clients):
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
        self.clients.clear()

        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()
            self.server = None

        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except OSError:
                pass

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        self.clients.add(writer)
        try:
            while self.running:
                line = await reader.readline()
                if not line:
                    break
                line_str = line.decode("utf-8", errors="replace").strip()
                if not line_str:
                    continue
                try:
                    payload = json.loads(line_str)
                    self.received_commands.append(payload)
                except json.JSONDecodeError:
                    writer.write(b'{"status":"error","message":"invalid_json"}\n')
                    await writer.drain()
                    continue

                if self.control_handler is not None:
                    try:
                        response = await self.control_handler(payload)
                        if response:
                            resp_bytes = json.dumps(response, separators=(",", ":")).encode("utf-8") + b"\n"
                            writer.write(resp_bytes)
                            await writer.drain()
                    except Exception as ex:
                        err_bytes = json.dumps({"status": "error", "error": str(ex)}, separators=(",", ":")).encode("utf-8") + b"\n"
                        writer.write(err_bytes)
                        await writer.drain()
        except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
            pass
        finally:
            self.clients.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def broadcast_frame(self, frame_dict: Dict[str, Any]) -> None:
        self.latest_payload = frame_dict
        if not self.clients:
            await asyncio.sleep(0.02)
        if not self.clients:
            return

        payload = json.dumps(frame_dict, separators=(",", ":")).encode("utf-8") + b"\n"
        dead_clients: Set[asyncio.StreamWriter] = set()

        for writer in list(self.clients):
            try:
                writer.write(payload)
            except Exception:
                dead_clients.add(writer)

        for writer in list(self.clients):
            if writer not in dead_clients:
                try:
                    await writer.drain()
                except Exception:
                    dead_clients.add(writer)

        for writer in dead_clients:
            self.clients.discard(writer)
            try:
                writer.close()
            except Exception:
                pass

        self.frames_sent += 1
        self.bytes_sent += len(payload)

    async def _broadcast_loop(self) -> None:
        start_mono = time.monotonic()
        frame_idx = 0
        stat_time = start_mono
        stat_frames = 0

        while self.running:
            frame_idx += 1
            target_mono = start_mono + (frame_idx * self.frame_interval)

            if self.frame_provider is not None:
                try:
                    frame = await self.frame_provider()
                    if frame:
                        await self.broadcast_frame(frame)
                except Exception:
                    pass

            stat_frames += 1
            now_mono = time.monotonic()
            if now_mono - stat_time >= 1.0:
                self.last_broadcast_fps = stat_frames / (now_mono - stat_time)
                stat_frames = 0
                stat_time = now_mono

            delay = target_mono - time.monotonic()
            if delay > 0.0005:
                await asyncio.sleep(delay)
            else:
                await asyncio.sleep(0)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "clients_connected": len(self.clients),
            "frames_sent": self.frames_sent,
            "bytes_sent": self.bytes_sent,
            "last_fps": round(self.last_broadcast_fps, 2),
            "socket_path": self.socket_path,
        }

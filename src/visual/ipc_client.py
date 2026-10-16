import asyncio
import json
import os
import time
from typing import Any, Callable, Dict, List, Optional

class IPCClient:
    def __init__(self, socket_path: Optional[str] = None) -> None:
        if socket_path is None:
            xdg = os.environ.get("XDG_RUNTIME_DIR", "/run/user/1000")
            self.socket_path = os.path.join(xdg, "jarvis", "perception_engine.sock")
        else:
            self.socket_path = socket_path

        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.running: bool = False
        self.received_frames: List[Dict[str, Any]] = []
        self.frame_timestamps: List[float] = []
        self.latest_frame: Optional[Dict[str, Any]] = None
        self.frame_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._stream_task: Optional[asyncio.Task[None]] = None
        self._frame_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=1)

    async def connect(self) -> None:
        self.reader, self.writer = await asyncio.open_unix_connection(self.socket_path)
        self.running = True
        await asyncio.sleep(0.02)

    async def send_command(self, cmd_dict: Dict[str, Any]) -> None:
        if not self.writer:
            raise RuntimeError("Not connected")
        payload = (json.dumps(cmd_dict) + "\n").encode("utf-8")
        self.writer.write(payload)
        await self.writer.drain()

    async def push_window(self, target_address: str, delta_x: int, delta_y: int) -> None:
        await self.send_command({
            "command": "push_window",
            "target_address": target_address,
            "delta": [int(delta_x), int(delta_y)],
        })

    async def push_window_impulse(
        self,
        target_address: str,
        impulse_x: float,
        impulse_y: float,
        mass: float = 50.0,
        friction: float = 8.0,
    ) -> None:
        await self.send_command({
            "command": "push_window_impulse",
            "target_address": target_address,
            "impulse": [float(impulse_x), float(impulse_y)],
            "mass": float(mass),
            "friction": float(friction),
        })

    async def inject_click(self, button: str = "0xC0") -> None:
        await self.send_command({
            "command": "inject_click",
            "button": str(button),
        })

    async def inject_mouse_move(self, x: int, y: int, absolute: bool = True) -> None:
        await self.send_command({
            "command": "inject_mouse_move",
            "x": int(x),
            "y": int(y),
            "absolute": bool(absolute),
        })

    async def move_active(self, delta_x: int, delta_y: int) -> None:
        await self.send_command({
            "command": "move_active",
            "delta": [int(delta_x), int(delta_y)],
        })

    async def resize_window(self, target_address: str, delta_w: int, delta_h: int) -> None:
        await self.send_command({
            "command": "resize_window",
            "target_address": target_address,
            "delta": [int(delta_w), int(delta_h)],
        })

    async def close_window(self, target_address: str) -> None:
        await self.send_command({
            "command": "close_window",
            "target_address": target_address,
        })

    async def focus_window(self, target_address: str) -> None:
        await self.send_command({
            "command": "focus_window",
            "target_address": target_address,
        })

    async def read_next_frame(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        if not self.reader:
            raise RuntimeError("Not connected")
        try:
            line = await asyncio.wait_for(self.reader.readline(), timeout=timeout)
        except (asyncio.TimeoutError, TimeoutError):
            return None
        if not line:
            return None
        now = time.time()
        try:
            parsed = json.loads(line.decode("utf-8", errors="replace").strip())
        except json.JSONDecodeError:
            return None
        self.latest_frame = parsed
        self.received_frames.append(parsed)
        self.frame_timestamps.append(now)
        return parsed

    async def read_frames_stream(
        self,
        count: int = 10,
        timeout_per_frame: float = 1.0,
    ) -> List[Dict[str, Any]]:
        frames: List[Dict[str, Any]] = []
        for _ in range(count):
            f = await self.read_next_frame(timeout=timeout_per_frame)
            if f is None:
                break
            frames.append(f)
        return frames

    async def _stream_worker(self) -> None:
        while self.running and self.reader:
            try:
                line = await self.reader.readline()
                if not line:
                    break
                now = time.time()
                raw = line.decode("utf-8", errors="replace").strip()
                if not raw:
                    continue
                parsed = json.loads(raw)
                self.latest_frame = parsed
                self.received_frames.append(parsed)
                self.frame_timestamps.append(now)

                if self._frame_queue.full():
                    try:
                        self._frame_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                self._frame_queue.put_nowait(parsed)

                for cb in self.frame_callbacks:
                    try:
                        cb(parsed)
                    except Exception:
                        pass
            except (asyncio.CancelledError, ConnectionResetError, BrokenPipeError):
                break
            except Exception:
                continue

    def start_background_stream(self) -> None:
        if self._stream_task is None and self.running:
            self._stream_task = asyncio.create_task(self._stream_worker())

    def get_latest_frame(self) -> Optional[Dict[str, Any]]:
        return self.latest_frame

    def register_callback(self, cb: Callable[[Dict[str, Any]], None]) -> None:
        self.frame_callbacks.append(cb)

    def calculate_jitter_ms(self) -> float:
        if len(self.frame_timestamps) < 2:
            return 0.0
        intervals = [
            (self.frame_timestamps[i] - self.frame_timestamps[i - 1]) * 1000.0
            for i in range(1, len(self.frame_timestamps))
        ]
        mean_interval = sum(intervals) / len(intervals)
        variances = [abs(iv - mean_interval) for iv in intervals]
        return sum(variances) / len(variances)

    async def close(self) -> None:
        self.running = False
        if self._stream_task is not None:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
            self._stream_task = None
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
            self.writer = None
        self.reader = None

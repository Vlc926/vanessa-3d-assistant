import asyncio
import os
from typing import Any, Callable, Dict, List, Optional

def normalize_address(addr: str) -> str:
    cleaned = str(addr).strip().lower()
    if not cleaned:
        return ""
    if cleaned.startswith("0x"):
        return cleaned
    return f"0x{cleaned}"

def parse_event_line(line: str) -> Optional[Dict[str, Any]]:
    stripped = line.rstrip("\r\n")
    if not stripped or ">>" not in stripped:
        return None
    name, _, data = stripped.partition(">>")
    name = name.strip()
    parsed: Dict[str, Any] = {"event": name, "raw": stripped}
    if name == "openwindow":
        parts = data.split(",", 3)
        if len(parts) > 0:
            parsed["address"] = normalize_address(parts[0])
        if len(parts) > 1:
            parsed["workspace"] = parts[1].strip()
        if len(parts) > 2:
            parsed["window_class"] = parts[2].strip()
        if len(parts) > 3:
            parsed["title"] = parts[3]
    elif name == "closewindow":
        parsed["address"] = normalize_address(data)
    elif name == "activewindowv2":
        raw_addr = data.strip()
        parsed["address"] = normalize_address(raw_addr) if raw_addr else ""
    elif name == "activewindow":
        parts = data.split(",", 1)
        parsed["window_class"] = parts[0].strip() if len(parts) > 0 else ""
        parsed["title"] = parts[1].strip() if len(parts) > 1 else ""
    elif name == "movewindowv2":
        parts = data.split(",", 2)
        if len(parts) > 0:
            parsed["address"] = normalize_address(parts[0])
        if len(parts) > 1:
            p1 = parts[1].strip()
            parsed["workspace_id"] = int(p1) if p1.isdigit() else p1
        if len(parts) > 2:
            parsed["workspace_name"] = parts[2].strip()
    elif name == "movewindow":
        parts = data.split(",", 1)
        if len(parts) > 0:
            parsed["address"] = normalize_address(parts[0])
        if len(parts) > 1:
            parsed["workspace_name"] = parts[1].strip()
    elif name == "changefloatingmode":
        parts = data.split(",", 1)
        if len(parts) > 0:
            parsed["address"] = normalize_address(parts[0])
        if len(parts) > 1:
            parsed["floating"] = (parts[1].strip() == "1")
    elif name == "fullscreen":
        parsed["fullscreen"] = (data.strip() == "1")
    elif name == "windowtitlev2":
        parts = data.split(",", 1)
        if len(parts) > 0:
            parsed["address"] = normalize_address(parts[0])
        if len(parts) > 1:
            parsed["title"] = parts[1]
    elif name == "windowtitle":
        parsed["address"] = normalize_address(data.strip())
    elif name == "workspacev2":
        parts = data.split(",", 1)
        if len(parts) > 0 and parts[0].strip().isdigit():
            parsed["workspace_id"] = int(parts[0].strip())
        if len(parts) > 1:
            parsed["workspace_name"] = parts[1].strip()
    elif name == "workspace":
        parsed["workspace_name"] = data.strip()
    elif name == "focusedmonv2":
        parts = data.split(",", 1)
        if len(parts) > 0:
            parsed["mon_name"] = parts[0].strip()
        if len(parts) > 1 and parts[1].strip().isdigit():
            parsed["workspace_id"] = int(parts[1].strip())
    elif name == "focusedmon":
        parts = data.split(",", 1)
        if len(parts) > 0:
            parsed["mon_name"] = parts[0].strip()
        if len(parts) > 1:
            parsed["workspace_name"] = parts[1].strip()
    elif name == "pin":
        parts = data.split(",", 1)
        if len(parts) > 0:
            parsed["address"] = normalize_address(parts[0])
        if len(parts) > 1:
            parsed["pinned"] = (parts[1].strip() == "1")
    elif name == "minimized":
        parts = data.split(",", 1)
        if len(parts) > 0:
            parsed["address"] = normalize_address(parts[0])
        if len(parts) > 1:
            parsed["minimized"] = (parts[1].strip() == "1")
    return parsed

def resolve_socket2_path(explicit_path: Optional[str] = None) -> str:
    if explicit_path:
        return explicit_path
    his = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    xdg_runtime = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    if his:
        candidate = os.path.join(xdg_runtime, "hypr", his, ".socket2.sock")
        if os.path.exists(candidate):
            return candidate
    hypr_dir = os.path.join(xdg_runtime, "hypr")
    if os.path.isdir(hypr_dir):
        for entry in os.listdir(hypr_dir):
            candidate = os.path.join(hypr_dir, entry, ".socket2.sock")
            if os.path.exists(candidate):
                return candidate
    raise FileNotFoundError("Could not resolve Hyprland .socket2.sock")

class SocketReader:
    def __init__(
        self,
        callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
        event_callback: Optional[Callable[..., Any]] = None,
        socket_path: Optional[str] = None,
        reconnect_delay: float = 0.5,
        max_reconnect_delay: float = 5.0,
    ) -> None:
        self.callback = callback or event_callback
        self.event_callback = event_callback
        self.explicit_socket_path = socket_path
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self.running: bool = False
        self.connected: bool = False
        self.buffer: str = ""
        self.events_received: List[Dict[str, Any]] = []
        self._listen_task: Optional[asyncio.Task[None]] = None
        self._callbacks: Dict[str, List[Callable[[Dict[str, Any]], Any]]] = {}
        self._global_callbacks: List[Callable[[Dict[str, Any]], Any]] = []
        if self.callback:
            self._global_callbacks.append(self.callback)
        self._event_queues: List[asyncio.Queue[Dict[str, Any]]] = []
        self._geometry_dirty: bool = True
        self._active_window_address: str = ""

    @property
    def is_connected(self) -> bool:
        return self.connected

    @property
    def is_geometry_dirty(self) -> bool:
        return self._geometry_dirty

    @property
    def is_dirty(self) -> bool:
        return self._geometry_dirty

    @property
    def active_window_address(self) -> str:
        return self._active_window_address

    def clear_geometry_dirty(self) -> None:
        self._geometry_dirty = False

    def mark_geometry_dirty(self) -> None:
        self._geometry_dirty = True

    def clear_dirty(self) -> None:
        self._geometry_dirty = False

    def mark_dirty(self) -> None:
        self._geometry_dirty = True

    def normalize_address(self, addr: str) -> str:
        return normalize_address(addr)

    def parse_event_line(self, line: str) -> Optional[Dict[str, Any]]:
        return parse_event_line(line)

    def add_callback(
        self,
        callback: Callable[[Dict[str, Any]], Any],
        event_filter: Optional[str] = None,
    ) -> None:
        if event_filter is None:
            if callback not in self._global_callbacks:
                self._global_callbacks.append(callback)
        else:
            lst = self._callbacks.setdefault(event_filter, [])
            if callback not in lst:
                lst.append(callback)

    def remove_callback(
        self,
        callback: Callable[[Dict[str, Any]], Any],
        event_filter: Optional[str] = None,
    ) -> None:
        if event_filter is None:
            if callback in self._global_callbacks:
                self._global_callbacks.remove(callback)
        elif event_filter in self._callbacks:
            if callback in self._callbacks[event_filter]:
                self._callbacks[event_filter].remove(callback)

    def create_queue(self, maxsize: int = 1000) -> asyncio.Queue[Dict[str, Any]]:
        q: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=maxsize)
        self._event_queues.append(q)
        return q

    def remove_queue(self, q: asyncio.Queue[Dict[str, Any]]) -> None:
        if q in self._event_queues:
            self._event_queues.remove(q)

    def feed_data(self, chunk: str) -> List[Dict[str, Any]]:
        self.buffer += chunk
        lines = self.buffer.split("\n")
        self.buffer = lines[-1]
        results: List[Dict[str, Any]] = []
        for line in lines[:-1]:
            ev = self.parse_event_line(line)
            if ev:
                self.events_received.append(ev)
                results.append(ev)
                self._dispatch(ev)
        return results

    def _dispatch(self, event: Dict[str, Any]) -> None:
        name = event.get("event", "")
        if name in (
            "openwindow",
            "closewindow",
            "movewindow",
            "movewindowv2",
            "changefloatingmode",
            "fullscreen",
        ):
            self._geometry_dirty = True
        if name == "activewindowv2":
            self._active_window_address = event.get("address", "")
            self._geometry_dirty = True

        for q in self._event_queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

        if self.event_callback is not None:
            try:
                raw_data = event.get("raw", "")
                if ">>" in raw_data:
                    _, _, d = raw_data.partition(">>")
                else:
                    d = ""
                res = self.event_callback(name, d)
                if asyncio.iscoroutine(res):
                    asyncio.create_task(res)
            except Exception:
                pass

        callbacks = list(self._global_callbacks)
        if name in self._callbacks:
            callbacks.extend(self._callbacks[name])

        for cb in callbacks:
            if cb is self.event_callback:
                continue
            try:
                res = cb(event)
                if asyncio.iscoroutine(res):
                    asyncio.create_task(res)
            except Exception:
                pass

    async def start(self) -> None:
        if self.running:
            return
        self.running = True
        self._listen_task = asyncio.create_task(self._listen_loop())

    async def stop(self) -> None:
        self.running = False
        if self._listen_task and not self._listen_task.done():
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
        self.connected = False

    async def listen(self) -> None:
        await self._listen_loop()

    async def run_stream(self, reader: asyncio.StreamReader) -> None:
        self.running = True
        try:
            while self.running:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                self.feed_data(chunk.decode("utf-8", errors="replace"))
        finally:
            self.running = False

    async def _listen_loop(self) -> None:
        current_delay = self.reconnect_delay
        while self.running:
            writer = None
            try:
                sock_path = resolve_socket2_path(self.explicit_socket_path)
                reader, writer = await asyncio.open_unix_connection(sock_path)
                self.connected = True
                current_delay = self.reconnect_delay
                while self.running:
                    line = await reader.readline()
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace")
                    if not text:
                        continue
                    self.feed_data(text)
            except asyncio.CancelledError:
                break
            except Exception:
                pass
            finally:
                self.connected = False
                if writer:
                    try:
                        writer.close()
                        await writer.wait_closed()
                    except Exception:
                        pass
            if self.running:
                try:
                    await asyncio.sleep(current_delay)
                except asyncio.CancelledError:
                    break
                current_delay = min(current_delay * 1.5, self.max_reconnect_delay)

HyprSocketReader = SocketReader

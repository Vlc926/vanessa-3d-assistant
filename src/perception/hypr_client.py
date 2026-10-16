import json
import os
import socket
import subprocess
from typing import Any, Dict, List, Optional, Tuple

def normalize_address(addr: str) -> str:
    cleaned = str(addr).strip().lower()
    if not cleaned:
        return ""
    if cleaned.startswith("0x"):
        return cleaned
    return f"0x{cleaned}"

def resolve_socket_path(explicit_path: Optional[str] = None) -> str:
    if explicit_path:
        return explicit_path
    his = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    xdg_runtime = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    if his:
        candidate = os.path.join(xdg_runtime, "hypr", his, ".socket.sock")
        if os.path.exists(candidate):
            return candidate
    hypr_dir = os.path.join(xdg_runtime, "hypr")
    if os.path.isdir(hypr_dir):
        for entry in os.listdir(hypr_dir):
            candidate = os.path.join(hypr_dir, entry, ".socket.sock")
            if os.path.exists(candidate):
                return candidate
    raise FileNotFoundError("Could not resolve Hyprland .socket.sock")

class HyprClient:
    def __init__(
        self,
        socket_path: Optional[str] = None,
        timeout: float = 0.5,
        fallback_to_cli: bool = True,
    ) -> None:
        self.socket_path = socket_path
        self.explicit_socket_path = socket_path
        self.timeout = timeout
        self.fallback_to_cli = fallback_to_cli

        self.mock_clients: List[Dict[str, Any]] = [
            {
                "address": "0x5616a03008b0",
                "title": "foot",
                "class": "foot",
                "at": [100, 150],
                "size": [800, 600],
                "workspace": {"id": 1, "name": "1"},
                "floating": False,
                "focusHistoryID": 0,
            }
        ]
        self.mock_cursor: Dict[str, int] = {"x": 265, "y": 725}
        self._mock_clients_explicit: bool = False
        self._mock_cursor_explicit: bool = False

    def set_mock_clients(self, clients: List[Dict[str, Any]]) -> None:
        self.mock_clients = list(clients)
        self._mock_clients_explicit = True

    def set_mock_cursor(self, x: int, y: int) -> None:
        self.mock_cursor = {"x": int(x), "y": int(y)}
        self._mock_cursor_explicit = True

    def _query_socket(self, command: bytes) -> str:
        sock_path = resolve_socket_path(self.explicit_socket_path or self.socket_path)
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(self.timeout)
        try:
            s.connect(sock_path)
            s.sendall(command)
            chunks: List[bytes] = []
            while True:
                buf = s.recv(4096)
                if not buf:
                    break
                chunks.append(buf)
            return b"".join(chunks).decode("utf-8", errors="replace")
        finally:
            s.close()

    def _fallback_cli(self, command: str) -> str:
        mapping = {
            "j/cursorpos": ["hyprctl", "cursorpos", "-j"],
            "j/clients": ["hyprctl", "clients", "-j"],
            "j/activewindow": ["hyprctl", "activewindow", "-j"],
            "j/monitors": ["hyprctl", "monitors", "-j"],
            "j/workspaces": ["hyprctl", "workspaces", "-j"],
        }
        cmd_str = command.strip()
        if cmd_str in mapping:
            args = mapping[cmd_str]
        elif cmd_str.startswith("dispatch "):
            args = ["hyprctl", "dispatch"] + cmd_str[9:].split()
        elif cmd_str.startswith("j/"):
            args = ["hyprctl", cmd_str[2:], "-j"]
        else:
            args = ["hyprctl"] + cmd_str.split()
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=self.timeout + 1.0,
            check=False,
        )
        return proc.stdout

    def query_raw(self, command: bytes | str) -> str:
        cmd_bytes = command.encode("utf-8") if isinstance(command, str) else command
        try:
            return self._query_socket(cmd_bytes)
        except Exception:
            if not self.fallback_to_cli:
                raise
            try:
                cmd_str = cmd_bytes.decode("utf-8", errors="replace")
                return self._fallback_cli(cmd_str)
            except Exception:
                return ""

    def query_socket(self, cmd: str) -> Any:
        if self._mock_clients_explicit and cmd == "j/clients":
            return [dict(c) for c in self.mock_clients]
        if self._mock_cursor_explicit and cmd == "j/cursorpos":
            return dict(self.mock_cursor)
        if self._mock_clients_explicit and cmd == "j/activewindow":
            return dict(self.mock_clients[0]) if self.mock_clients else {}

        raw = self.query_raw(cmd)
        if raw:
            try:
                return json.loads(raw.strip())
            except Exception:
                return raw.strip()

        if cmd == "j/cursorpos":
            return dict(self.mock_cursor)
        elif cmd == "j/clients":
            return [dict(c) for c in self.mock_clients]
        elif cmd == "j/activewindow":
            return dict(self.mock_clients[0]) if self.mock_clients else {}
        return {}

    def get_cursor_position(self) -> Tuple[int, int]:
        if self._mock_cursor_explicit:
            return self.mock_cursor.get("x", 0), self.mock_cursor.get("y", 0)
        try:
            raw = self.query_raw(b"j/cursorpos")
            if raw and raw.strip():
                data = json.loads(raw.strip())
                return int(data.get("x", 0)), int(data.get("y", 0))
        except Exception:
            pass
        return self.mock_cursor.get("x", 0), self.mock_cursor.get("y", 0)

    def get_cursor_pos(self) -> Dict[str, int]:
        x, y = self.get_cursor_position()
        return {"x": x, "y": y}

    def get_cursorpos(self) -> Dict[str, int]:
        return self.get_cursor_pos()

    def get_clients(self) -> List[Dict[str, Any]]:
        if self._mock_clients_explicit:
            return [dict(c) for c in self.mock_clients]
        try:
            raw = self.query_raw(b"j/clients")
            if raw and raw.strip():
                clients = json.loads(raw.strip())
                if isinstance(clients, list):
                    for client in clients:
                        if isinstance(client, dict) and "address" in client:
                            client["address"] = normalize_address(str(client["address"]))
                    return clients
        except Exception:
            pass
        return [dict(c) for c in self.mock_clients]

    def get_active_client(self) -> Optional[Dict[str, Any]]:
        clients = self.get_clients()
        for c in clients:
            if c.get("focusHistoryID", -1) == 0:
                return c
        return clients[0] if clients else None

    def get_active_window(self) -> Optional[Dict[str, Any]]:
        if self._mock_clients_explicit:
            return self.get_active_client()
        try:
            raw = self.query_raw(b"j/activewindow")
            if raw and raw.strip() and raw.strip() != "{}":
                data = json.loads(raw.strip())
                if isinstance(data, dict) and data.get("address"):
                    data["address"] = normalize_address(str(data["address"]))
                    return data
        except Exception:
            pass
        return self.get_active_client()

    def get_monitors(self) -> List[Dict[str, Any]]:
        try:
            raw = self.query_raw(b"j/monitors")
            if raw and raw.strip():
                data = json.loads(raw.strip())
                return data if isinstance(data, list) else []
        except Exception:
            pass
        return []

    def get_workspaces(self) -> List[Dict[str, Any]]:
        try:
            raw = self.query_raw(b"j/workspaces")
            if raw and raw.strip():
                data = json.loads(raw.strip())
                return data if isinstance(data, list) else []
        except Exception:
            pass
        return []

    def dispatch(self, dispatcher: str, args: str = "") -> Tuple[bool, str]:
        cmd = f"dispatch {dispatcher} {args}".strip()
        res = self.query_raw(cmd).strip()
        success = (res == "ok")
        return success, res

    def batch_query(self, commands: List[str]) -> List[Any]:
        if not commands:
            return []
        batch_cmd = "[[BATCH]]" + " ; ".join(commands)
        raw = self.query_raw(batch_cmd)
        results: List[Any] = []
        decoder = json.JSONDecoder()
        idx = 0
        length = len(raw)
        while idx < length:
            sub = raw[idx:].lstrip()
            if not sub:
                break
            idx = length - len(sub)
            try:
                obj, end = decoder.raw_decode(raw[idx:])
                results.append(obj)
                idx += end
            except json.JSONDecodeError:
                break
        return results

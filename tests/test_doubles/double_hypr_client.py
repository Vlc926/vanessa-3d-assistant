import json
import os
import socket

class HyprClientDouble:
    def __init__(self, socket_path=None):
        self.socket_path = socket_path
        self.mock_clients = [
            {
                "address": "0x5616a03008b0",
                "title": "foot",
                "class": "foot",
                "at": [100, 150],
                "size": [800, 600],
                "workspace": {"id": 1, "name": "1"},
                "floating": False,
                "focusHistoryID": 0
            }
        ]
        self.mock_cursor = {"x": 265, "y": 725}

    def set_mock_clients(self, clients):
        self.mock_clients = list(clients)

    def set_mock_cursor(self, x, y):
        self.mock_cursor = {"x": int(x), "y": int(y)}

    def query_socket(self, cmd):
        if self.socket_path and os.path.exists(self.socket_path):
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.settimeout(0.5)
                s.connect(self.socket_path)
                s.sendall(cmd.encode("utf-8"))
                chunks = []
                while True:
                    data = s.recv(4096)
                    if not data:
                        break
                    chunks.append(data)
                s.close()
                raw = b"".join(chunks).decode("utf-8", errors="replace")
                return json.loads(raw)
            except Exception:
                pass

        if cmd == "j/cursorpos":
            return dict(self.mock_cursor)
        elif cmd == "j/clients":
            return [dict(c) for c in self.mock_clients]
        elif cmd == "j/activewindow":
            return dict(self.mock_clients[0]) if self.mock_clients else {}
        return {}

    def get_cursor_position(self):
        data = self.query_socket("j/cursorpos")
        return data.get("x", 0), data.get("y", 0)

    def get_clients(self):
        return self.query_socket("j/clients")

    def get_active_client(self):
        clients = self.get_clients()
        for c in clients:
            if c.get("focusHistoryID", -1) == 0:
                return c
        return clients[0] if clients else None

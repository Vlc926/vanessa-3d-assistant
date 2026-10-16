import asyncio
import json
import os
import time

class IPCServerDouble:
    def __init__(self, socket_path="/tmp/jarvis_test_perception.sock", fps=60):
        self.socket_path = socket_path
        self.fps = fps
        self.interval = 1.0 / float(fps)
        self.clients = set()
        self.server = None
        self.running = False
        self.latest_payload = {}
        self.received_commands = []

    def build_telemetry_packet(self, cursor=None, active_window=None, collision_planes=None, feedback=None):
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
                "end": [900.0, 150.0, 0.0]
            }
        }
        cp = collision_planes if collision_planes is not None else [
            {
                "id": "0x5616a03008b0",
                "type": "window_top",
                "plane": [0.0, 1.0, 0.0, -150.0],
                "bounds": [100.0, 900.0, 150.0, 150.0, -0.1, 0.1]
            }
        ]
        fb = feedback if feedback is not None else {"last_action": "none", "status": "ok"}
        return {
            "timestamp": ts,
            "cursor": c,
            "active_window": w,
            "collision_planes": cp,
            "action_feedback": fb
        }

    async def handle_client(self, reader, writer):
        self.clients.add(writer)
        try:
            while self.running:
                data = await reader.readline()
                if not data:
                    break
                line = data.decode("utf-8", errors="replace").strip()
                if line:
                    try:
                        cmd = json.loads(line)
                        self.received_commands.append(cmd)
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass
        finally:
            self.clients.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def start(self):
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)
        os.makedirs(os.path.dirname(os.path.abspath(self.socket_path)), exist_ok=True)
        self.server = await asyncio.start_unix_server(self.handle_client, self.socket_path)
        self.running = True

    async def broadcast_frame(self, frame_dict):
        self.latest_payload = frame_dict
        line = (json.dumps(frame_dict) + "\n").encode("utf-8")
        dead_writers = []
        for writer in list(self.clients):
            try:
                writer.write(line)
                await writer.drain()
            except Exception:
                dead_writers.append(writer)
        for w in dead_writers:
            self.clients.discard(w)

    async def stop(self):
        self.running = False
        for writer in list(self.clients):
            try:
                writer.close()
            except Exception:
                pass
        self.clients.clear()
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
        if os.path.exists(self.socket_path):
            try:
                os.remove(self.socket_path)
            except OSError:
                pass

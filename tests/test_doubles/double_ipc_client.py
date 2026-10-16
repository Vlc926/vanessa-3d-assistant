import asyncio
import json
import time

class IPCClientDouble:
    def __init__(self, socket_path="/tmp/jarvis_test_perception.sock"):
        self.socket_path = socket_path
        self.reader = None
        self.writer = None
        self.running = False
        self.received_frames = []
        self.frame_timestamps = []

    async def connect(self):
        self.reader, self.writer = await asyncio.open_unix_connection(self.socket_path)
        self.running = True
        await asyncio.sleep(0.05)

    async def send_command(self, cmd_dict):
        if not self.writer:
            raise RuntimeError("Not connected")
        payload = (json.dumps(cmd_dict) + "\n").encode("utf-8")
        self.writer.write(payload)
        await self.writer.drain()

    async def read_next_frame(self, timeout=1.0):
        if not self.reader:
            raise RuntimeError("Not connected")
        try:
            line = await asyncio.wait_for(self.reader.readline(), timeout=timeout)
        except (asyncio.TimeoutError, TimeoutError):
            return None
        if not line:
            return None
        now = time.time()
        parsed = json.loads(line.decode("utf-8", errors="replace").strip())
        self.received_frames.append(parsed)
        self.frame_timestamps.append(now)
        return parsed

    async def read_frames_stream(self, count=10, timeout_per_frame=1.0):
        frames = []
        for _ in range(count):
            f = await self.read_next_frame(timeout=timeout_per_frame)
            if f is None:
                break
            frames.append(f)
        return frames

    def calculate_jitter_ms(self):
        if len(self.frame_timestamps) < 2:
            return 0.0
        intervals = [
            (self.frame_timestamps[i] - self.frame_timestamps[i-1]) * 1000.0
            for i in range(1, len(self.frame_timestamps))
        ]
        mean_interval = sum(intervals) / len(intervals)
        variances = [abs(iv - mean_interval) for iv in intervals]
        return sum(variances) / len(variances)

    async def close(self):
        self.running = False
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
            self.writer = None
        self.reader = None

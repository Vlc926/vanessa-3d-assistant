import asyncio

class SocketReaderDouble:
    def __init__(self, callback=None):
        self.callback = callback
        self.running = False
        self.events_received = []
        self.buffer = ""

    def normalize_address(self, addr):
        addr_clean = addr.strip()
        if not addr_clean:
            return ""
        if not addr_clean.startswith("0x"):
            return "0x" + addr_clean
        return addr_clean

    def parse_event_line(self, line):
        line = line.strip()
        if not line or ">>" not in line:
            return None
        parts = line.split(">>", 1)
        event_name = parts[0].strip()
        raw_data = parts[1].strip()
        data_parts = [p.strip() for p in raw_data.split(",")] if raw_data else []
        
        parsed = {"event": event_name, "raw": line}
        if event_name == "openwindow":
            if len(data_parts) >= 4:
                parsed["address"] = self.normalize_address(data_parts[0])
                parsed["workspace"] = data_parts[1]
                parsed["window_class"] = data_parts[2]
                parsed["title"] = data_parts[3]
        elif event_name == "closewindow":
            if len(data_parts) >= 1:
                parsed["address"] = self.normalize_address(data_parts[0])
        elif event_name in ("movewindow", "movewindowv2"):
            if len(data_parts) >= 1:
                parsed["address"] = self.normalize_address(data_parts[0])
            if event_name == "movewindowv2" and len(data_parts) >= 3:
                parsed["workspace_id"] = data_parts[1]
                parsed["workspace_name"] = data_parts[2]
            elif len(data_parts) >= 2:
                parsed["workspace_name"] = data_parts[1]
        elif event_name in ("activewindow", "activewindowv2"):
            if event_name == "activewindowv2":
                parsed["address"] = self.normalize_address(data_parts[0]) if data_parts else ""
            else:
                parsed["window_class"] = data_parts[0] if len(data_parts) > 0 else ""
                parsed["title"] = data_parts[1] if len(data_parts) > 1 else ""
        elif event_name == "changefloatingmode":
            if len(data_parts) >= 2:
                parsed["address"] = self.normalize_address(data_parts[0])
                parsed["floating"] = (data_parts[1] == "1")
        return parsed

    def feed_data(self, chunk):
        self.buffer += chunk
        lines = self.buffer.split("\n")
        self.buffer = lines[-1]
        results = []
        for line in lines[:-1]:
            ev = self.parse_event_line(line)
            if ev:
                self.events_received.append(ev)
                results.append(ev)
                if self.callback:
                    if asyncio.iscoroutinefunction(self.callback):
                        asyncio.create_task(self.callback(ev))
                    else:
                        self.callback(ev)
        return results

    async def run_stream(self, reader):
        self.running = True
        try:
            while self.running:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                self.feed_data(chunk.decode("utf-8", errors="replace"))
        finally:
            self.running = False

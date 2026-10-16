import asyncio
import json
import math
import os
import sys

class HeadlessPhysicsEngine:
    def __init__(self):
        self.chains = {
            "shark_tail": [],
            "skirt": [],
            "hair": []
        }
        self.time_step = 1.0 / 60.0
        self.gravity = -9.81
        self.drag = 0.94
        self._init_default_chains()

    def _init_default_chains(self):
        for i in range(6):
            self.chains["shark_tail"].append({
                "pos": [0.0, 0.8 - i * 0.12, -0.15 - i * 0.1],
                "prev_pos": [0.0, 0.8 - i * 0.12, -0.15 - i * 0.1]
            })
        for i in range(8):
            self.chains["skirt"].append({
                "pos": [math.sin(i * math.pi / 4) * 0.25, 0.7, math.cos(i * math.pi / 4) * 0.25],
                "prev_pos": [math.sin(i * math.pi / 4) * 0.25, 0.7, math.cos(i * math.pi / 4) * 0.25]
            })
        for i in range(4):
            self.chains["hair"].append({
                "pos": [0.0, 1.4 - i * 0.08, -0.1],
                "prev_pos": [0.0, 1.4 - i * 0.08, -0.1]
            })

    def step(self, root_dx=0.0, root_dy=0.0, root_dz=0.0):
        result = {}
        for chain_name, particles in self.chains.items():
            chain_pts = []
            for p in particles:
                pos = p["pos"]
                prev = p["prev_pos"]
                vel_x = (pos[0] - prev[0]) * self.drag
                vel_y = (pos[1] - prev[1]) * self.drag
                vel_z = (pos[2] - prev[2]) * self.drag
                new_x = pos[0] + vel_x + root_dx * 0.25
                new_y = pos[1] + vel_y + (self.gravity * 0.001) + root_dy * 0.25
                new_z = pos[2] + vel_z + root_dz * 0.25
                p["prev_pos"] = list(pos)
                p["pos"] = [new_x, new_y, new_z]
                chain_pts.append(p["pos"])
            result[chain_name] = chain_pts
        return result

async def handler(reader, writer):
    engine = HeadlessPhysicsEngine()

    while True:
        line = await reader.readline()
        if not line:
            break
        try:
            req = json.loads(line.decode().strip())
        except Exception:
            continue
        dx = float(req.get("dx", 0.0))
        dy = float(req.get("dy", 0.0))
        dz = float(req.get("dz", 0.0))
        pts = engine.step(dx, dy, dz)
        resp = json.dumps({"status": "ok", "chains": pts}) + "\n"
        writer.write(resp.encode())
        await writer.drain()

async def main():
    port = int(os.environ.get("SIMULATION_PORT", 9876))
    server = await asyncio.start_server(handler, "0.0.0.0", port)
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

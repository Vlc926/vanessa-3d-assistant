import math

class GeometryProjectorDouble:
    def __init__(self, screen_w=1920, screen_h=1200, fov_deg=30.0, z_ref=2.8):
        self.screen_w = float(screen_w)
        self.screen_h = float(screen_h)
        self.aspect = self.screen_w / self.screen_h
        fov_rad = math.radians(fov_deg)
        self.h3d = 2.0 * z_ref * math.tan(fov_rad / 2.0)
        self.w3d = self.h3d * self.aspect
        self.z_ref = float(z_ref)

    def pixel_to_3d(self, px, py, z_depth=0.0):
        x3d = ((float(px) / self.screen_w) - 0.5) * self.w3d
        y3d = (0.5 - (float(py) / self.screen_h)) * self.h3d
        return [round(x3d, 4), round(y3d, 4), round(float(z_depth), 4)]

    def point_3d_to_pixel(self, x3d, y3d):
        px = int(round(((x3d / self.w3d) + 0.5) * self.screen_w))
        py = int(round((0.5 - (y3d / self.h3d)) * self.screen_h))
        return px, py

    def calculate_z_depth(self, client, is_active=False):
        floating = client.get("floating", False)
        focus_id = client.get("focusHistoryID", 0)
        base_z = 0.10 * (1 + max(0, 5 - focus_id)) if floating else 0.00
        if is_active:
            base_z += 0.08
        return round(base_z, 4)

    def extract_top_ledge(self, client, z_depth):
        at = client.get("at", [0, 0])
        size = client.get("size", [0, 0])
        x, y = at[0], at[1]
        w, _ = size[0], size[1]
        p_start = self.pixel_to_3d(x, y, z_depth)
        p_end = self.pixel_to_3d(x + w, y, z_depth)
        return {
            "start": p_start,
            "end": p_end
        }

    def project_client(self, client, is_active=False):
        at = client.get("at", [0, 0])
        size = client.get("size", [0, 0])
        x, y = at[0], at[1]
        w, h = size[0], size[1]
        z = self.calculate_z_depth(client, is_active)
        addr = client.get("address", "")
        top_ledge = self.extract_top_ledge(client, z)

        p_tl = self.pixel_to_3d(x, y, z)
        p_br = self.pixel_to_3d(x + w, y + h, z)
        x_min = min(p_tl[0], p_br[0])
        x_max = max(p_tl[0], p_br[0])
        y_min = min(p_tl[1], p_br[1])
        y_max = max(p_tl[1], p_br[1])

        planes = [
            {
                "id": addr,
                "type": "window_top",
                "plane": [0.0, 1.0, 0.0, -y_max],
                "bounds": [x_min, x_max, y_max - 0.03, y_max, z - 0.05, z + 0.05]
            },
            {
                "id": addr + "_left",
                "type": "window_border_left",
                "plane": [1.0, 0.0, 0.0, -x_min],
                "bounds": [x_min - 0.02, x_min, y_min, y_max, z - 0.05, z + 0.05]
            },
            {
                "id": addr + "_right",
                "type": "window_border_right",
                "plane": [-1.0, 0.0, 0.0, x_max],
                "bounds": [x_max, x_max + 0.02, y_min, y_max, z - 0.05, z + 0.05]
            },
            {
                "id": addr + "_scrollbar",
                "type": "window_scrollbar",
                "plane": [0.0, 0.0, 1.0, -z],
                "bounds": [x_max - 0.04, x_max, y_min, y_max, z - 0.02, z + 0.02]
            }
        ]
        return {
            "address": addr,
            "title": client.get("title", ""),
            "class": client.get("class", ""),
            "at": at,
            "size": size,
            "workspace": client.get("workspace", {}).get("id", 1) if isinstance(client.get("workspace"), dict) else client.get("workspace", 1),
            "z_depth": z,
            "top_ledge": top_ledge,
            "planes": planes
        }

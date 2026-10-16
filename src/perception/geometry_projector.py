import math
import time
from typing import Any, Dict, List, Optional, Tuple

def normalize_address(address: Optional[str]) -> str:
    if not address:
        return ""
    addr_clean = str(address).strip().lower()
    if not addr_clean.startswith("0x"):
        return "0x" + addr_clean
    return addr_clean

class GeometryProjector:
    def __init__(
        self,
        screen_w: float = 1920.0,
        screen_h: float = 1200.0,
        fov_deg: float = 30.0,
        z_ref: float = 2.8,
        scrollbar_width: float = 14.0,
    ) -> None:
        self.screen_w = max(1.0, float(screen_w))
        self.screen_h = max(1.0, float(screen_h))
        self.aspect = self.screen_w / self.screen_h
        self.fov_deg = float(fov_deg)
        self.z_ref = float(z_ref)
        self.scrollbar_width = float(scrollbar_width)

        fov_rad = math.radians(self.fov_deg)
        self.h3d = 2.0 * self.z_ref * math.tan(fov_rad / 2.0)
        self.w3d = self.h3d * self.aspect

        self.cached_clients: List[Dict[str, Any]] = []
        self.active_address: str = ""
        self._dirty: bool = True

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def mark_dirty(self) -> None:
        self._dirty = True

    def clear_dirty(self) -> None:
        self._dirty = False

    def update_clients(self, clients: List[Dict[str, Any]]) -> None:
        self.cached_clients = list(clients)
        self._dirty = True

    def set_active_address(self, address: str) -> None:
        self.active_address = normalize_address(address)
        self._dirty = True

    def set_screen_dimensions(self, width: float, height: float) -> None:
        self.screen_w = max(1.0, float(width))
        self.screen_h = max(1.0, float(height))
        self.aspect = self.screen_w / self.screen_h
        self.w3d = self.h3d * self.aspect

    def normalize_address(self, address: Optional[str]) -> str:
        return normalize_address(address)

    def pixel_to_3d(self, px: float, py: float, z_depth: float = 0.0) -> List[float]:
        x3d = ((float(px) / self.screen_w) - 0.5) * self.w3d
        y3d = (0.5 - (float(py) / self.screen_h)) * self.h3d
        return [round(x3d, 4), round(y3d, 4), round(float(z_depth), 4)]

    def point_3d_to_pixel(self, x3d: float, y3d: float) -> Tuple[int, int]:
        px = int(round(((float(x3d) / self.w3d) + 0.5) * self.screen_w))
        py = int(round((0.5 - (float(y3d) / self.h3d)) * self.screen_h))
        return px, py

    def screen_to_metric(self, px: float, py: float, z: float = 0.0) -> List[float]:
        return self.pixel_to_3d(px, py, z)

    def metric_to_screen(self, x3d: float, y3d: float) -> List[int]:
        px, py = self.point_3d_to_pixel(x3d, y3d)
        return [px, py]

    def calculate_z_depth(self, client: Dict[str, Any], is_active: bool = False) -> float:
        fullscreen = bool(client.get("fullscreen", 0))
        pinned = bool(client.get("pinned", False))
        floating = bool(client.get("floating", False))
        focus_id = int(client.get("focusHistoryID", 0) or 0)

        if fullscreen:
            base_z = 1.0
        elif pinned:
            base_z = 0.9
        elif floating:
            base_z = 0.10 * (1 + max(0, 5 - focus_id))
        else:
            base_z = 0.00

        if is_active:
            base_z += 0.08

        return round(base_z, 4)

    def compute_z_depth(self, client: Dict[str, Any], is_active: bool = False) -> float:
        return self.calculate_z_depth(client, is_active)

    def extract_top_ledge(self, *args: Any, **kwargs: Any) -> Dict[str, List[float]]:
        if len(args) == 1 or (len(args) >= 1 and isinstance(args[0], dict)):
            client = args[0]
            z_depth = args[1] if len(args) > 1 else kwargs.get("z_depth", 0.0)
            at = client.get("at", [0, 0])
            size = client.get("size", [0, 0])
            x, y = at[0], at[1]
            w = size[0]
            z = z_depth
        else:
            x, y, w, z = args[0], args[1], args[2], args[3]

        p_start = self.pixel_to_3d(x, y, z)
        p_end = self.pixel_to_3d(x + w, y, z)
        return {
            "start": p_start,
            "end": p_end,
        }

    def project_client(self, client: Dict[str, Any], is_active: bool = False) -> Dict[str, Any]:
        at = client.get("at", [0, 0])
        size = client.get("size", [0, 0])
        x, y = at[0], at[1]
        w, h = size[0], size[1]
        z = self.calculate_z_depth(client, is_active)
        addr = normalize_address(client.get("address", ""))
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
                "bounds": [x_min, x_max, round(y_max - 0.03, 4), y_max, round(z - 0.05, 4), round(z + 0.05, 4)],
            },
            {
                "id": addr + "_left",
                "type": "window_border_left",
                "plane": [1.0, 0.0, 0.0, -x_min],
                "bounds": [round(x_min - 0.02, 4), x_min, y_min, y_max, round(z - 0.05, 4), round(z + 0.05, 4)],
            },
            {
                "id": addr + "_right",
                "type": "window_border_right",
                "plane": [-1.0, 0.0, 0.0, x_max],
                "bounds": [x_max, round(x_max + 0.02, 4), y_min, y_max, round(z - 0.05, 4), round(z + 0.05, 4)],
            },
            {
                "id": addr + "_scrollbar",
                "type": "window_scrollbar",
                "plane": [0.0, 0.0, 1.0, -z],
                "bounds": [round(x_max - 0.04, 4), x_max, y_min, y_max, round(z - 0.02, 4), round(z + 0.02, 4)],
            },
        ]

        ws = client.get("workspace", {})
        ws_id = ws.get("id", 1) if isinstance(ws, dict) else ws

        return {
            "address": addr,
            "title": client.get("title", ""),
            "class": client.get("class", ""),
            "at": at,
            "size": size,
            "workspace": ws_id,
            "z_depth": z,
            "top_ledge": top_ledge,
            "planes": planes,
        }

    def project_frame(
        self,
        clients: Optional[List[Dict[str, Any]]] = None,
        cursor: Optional[Dict[str, Any]] = None,
        active_address: Optional[str] = None,
        current_workspace: Optional[int] = None,
        action_feedback: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None,
        include_borders: bool = False,
        include_scrollbar: bool = False,
    ) -> Dict[str, Any]:
        if timestamp is None:
            timestamp = time.time()
        if action_feedback is None:
            action_feedback = {"last_action": "none", "status": "ok"}

        cursor_dict = cursor or {}
        cursor_x = float(cursor_dict.get("x", 0.0))
        cursor_y = float(cursor_dict.get("y", 0.0))
        cursor_z = float(cursor_dict.get("z", 0.0))

        active_addr = normalize_address(active_address or self.active_address)
        active_window_obj: Optional[Dict[str, Any]] = None
        collision_planes: List[Dict[str, Any]] = []

        safe_clients = clients if clients is not None else self.cached_clients
        for c in safe_clients:
            if not isinstance(c, dict):
                continue
            if not c.get("mapped", True) or c.get("hidden", False):
                continue

            ws = c.get("workspace", {})
            ws_id = ws.get("id", ws) if isinstance(ws, dict) else ws
            if current_workspace is not None and ws_id != current_workspace:
                continue

            addr = normalize_address(c.get("address", ""))
            is_active = bool(active_addr and addr == active_addr)

            proj = self.project_client(c, is_active=is_active)
            for p in proj["planes"]:
                if p["type"] == "window_top":
                    collision_planes.append(p)
                elif include_borders and p["type"] in ("window_border_left", "window_border_right"):
                    collision_planes.append(p)
                elif include_scrollbar and p["type"] == "window_scrollbar":
                    collision_planes.append(p)

            if is_active:
                active_window_obj = {
                    "address": addr,
                    "title": c.get("title", ""),
                    "class": c.get("class", ""),
                    "at": proj["at"],
                    "size": proj["size"],
                    "workspace": ws_id,
                    "z_depth": proj["z_depth"],
                    "top_ledge": proj["top_ledge"],
                }

        floor_plane = {
            "id": "screen_floor",
            "type": "floor",
            "plane": [0.0, 1.0, 0.0, -self.screen_h],
            "bounds": [0.0, self.screen_w, self.screen_h, self.screen_h, -1.0, 1.0],
        }
        collision_planes.append(floor_plane)

        self._dirty = False

        return {
            "timestamp": timestamp,
            "cursor": {"x": cursor_x, "y": cursor_y, "z": cursor_z},
            "active_window": active_window_obj,
            "collision_planes": collision_planes,
            "action_feedback": action_feedback,
        }

    def build_frame(
        self,
        cursor: Optional[Dict[str, Any]] = None,
        active_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.project_frame(
            clients=self.cached_clients,
            cursor=cursor,
            active_address=active_address or self.active_address,
        )

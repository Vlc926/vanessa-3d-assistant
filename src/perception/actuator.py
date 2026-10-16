import math
import os
import socket
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

def normalize_address(addr: str) -> str:
    cleaned = str(addr).strip().lower()
    if not cleaned:
        return ""
    if cleaned.startswith("0x"):
        return cleaned
    return f"0x{cleaned}"

@dataclass
class WindowImpulseState:
    address: str
    vx: float
    vy: float
    mass: float
    friction: float
    accum_x: float = 0.0
    accum_y: float = 0.0

class Actuator:
    def __init__(
        self,
        execute_real: bool = False,
        hypr_socket_path: Optional[str] = None,
        ydotool_socket: Optional[str] = None,
    ) -> None:
        self.execute_real = execute_real

        if hypr_socket_path is None:
            sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
            xdg = os.environ.get("XDG_RUNTIME_DIR", "/run/user/1000")
            self.hypr_socket_path = os.path.join(xdg, "hypr", sig, ".socket.sock")
        else:
            self.hypr_socket_path = hypr_socket_path

        if ydotool_socket is None:
            xdg = os.environ.get("XDG_RUNTIME_DIR", "/run/user/1000")
            default_ydo = os.path.join(xdg, ".ydotool_socket")
            self.ydotool_socket = os.environ.get("YDOTOOL_SOCKET", default_ydo)
        else:
            self.ydotool_socket = ydotool_socket

        self.recorded_dispatches: List[Dict[str, str]] = []
        self.recorded_pointer_events: List[Dict[str, Any]] = []
        self.active_impulses: Dict[str, WindowImpulseState] = {}
        self.last_action: str = "none"
        self.last_status: str = "ok"

    def normalize_address(self, address: str) -> str:
        return normalize_address(address)

    def dispatch_hyprctl(self, command: str, args: str = "") -> Dict[str, str]:
        full_cmd = f"{command} {args}".strip()
        self.recorded_dispatches.append({"cmd": command, "args": args, "full": full_cmd})
        self.last_action = full_cmd
        status = "ok"

        if self.execute_real:
            executed_ok = False
            if os.path.exists(self.hypr_socket_path):
                try:
                    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    s.settimeout(0.5)
                    s.connect(self.hypr_socket_path)
                    s.sendall(f"dispatch {full_cmd}".encode("utf-8"))
                    res = s.recv(4096).decode("utf-8", errors="replace").strip()
                    s.close()
                    status = "ok" if (res == "ok" or not res) else res
                    executed_ok = True
                except Exception as ex:
                    status = str(ex)

            if not executed_ok:
                try:
                    cmd_parts = ["hyprctl", "dispatch"] + full_cmd.split()
                    proc = subprocess.run(
                        cmd_parts,
                        capture_output=True,
                        text=True,
                        timeout=1.5,
                        check=False,
                    )
                    status = "ok" if proc.returncode == 0 else "error"
                except Exception as ex:
                    status = str(ex)

        self.last_status = status
        return {"status": status, "executed": full_cmd}

    def push_window(self, address: str, delta_x: int | float, delta_y: int | float) -> Dict[str, str]:
        addr = self.normalize_address(address)
        args = f"{int(delta_x)} {int(delta_y)},address:{addr}"
        return self.dispatch_hyprctl("movewindowpixel", args)

    def resize_window(self, address: str, delta_w: int | float, delta_h: int | float) -> Dict[str, str]:
        addr = self.normalize_address(address)
        args = f"{int(delta_w)} {int(delta_h)},address:{addr}"
        return self.dispatch_hyprctl("resizewindowpixel", args)

    def move_window_exact(self, address: str, x: int, y: int) -> Dict[str, str]:
        addr = self.normalize_address(address)
        args = f"exact {int(x)} {int(y)},address:{addr}"
        return self.dispatch_hyprctl("movewindowpixel", args)

    def resize_window_exact(self, address: str, w: int, h: int) -> Dict[str, str]:
        addr = self.normalize_address(address)
        args = f"exact {int(w)} {int(h)},address:{addr}"
        return self.dispatch_hyprctl("resizewindowpixel", args)

    def close_window(self, address: str) -> Dict[str, str]:
        addr = self.normalize_address(address)
        return self.dispatch_hyprctl("closewindow", f"address:{addr}")

    def focus_window(self, address: str) -> Dict[str, str]:
        addr = self.normalize_address(address)
        return self.dispatch_hyprctl("focuswindow", f"address:{addr}")

    def move_active(self, dx: int | float, dy: int | float) -> Dict[str, str]:
        return self.dispatch_hyprctl("moveactive", f"{int(dx)} {int(dy)}")

    def _run_ydotool(self, args: List[str]) -> bool:
        if not os.path.exists(self.ydotool_socket):
            self.last_status = "ydotool_socket_missing"
            return False
        env = os.environ.copy()
        env["YDOTOOL_SOCKET"] = self.ydotool_socket
        try:
            proc = subprocess.run(
                ["ydotool"] + args,
                env=env,
                capture_output=True,
                timeout=1.5,
                check=False,
            )
            success = (proc.returncode == 0)
            self.last_status = "ok" if success else f"code_{proc.returncode}"
            return success
        except Exception as ex:
            self.last_status = str(ex)
            return False

    def inject_pointer_move(self, x: int, y: int, absolute: bool = True) -> Dict[str, Any]:
        entry = {"action": "mousemove", "x": int(x), "y": int(y), "absolute": bool(absolute)}
        self.recorded_pointer_events.append(entry)
        self.last_action = f"mousemove {x} {y}"
        status = "ok"
        if self.execute_real:
            if absolute:
                ok = self._run_ydotool(["mousemove", "-a", "-x", str(int(x)), "-y", str(int(y))])
            else:
                ok = self._run_ydotool(["mousemove", "--", str(int(x)), str(int(y))])
            status = "ok" if ok else self.last_status
        self.last_status = status
        return {"status": status, "event": entry}

    def inject_pointer_click(self, button_code: int | str = 0xC0) -> Dict[str, Any]:
        entry = {"action": "click", "button": button_code}
        self.recorded_pointer_events.append(entry)
        self.last_action = f"click {button_code}"
        status = "ok"
        if self.execute_real:
            mask_str = f"0x{button_code:02X}" if isinstance(button_code, int) else str(button_code).strip()
            ok = self._run_ydotool(["click", mask_str])
            status = "ok" if ok else self.last_status
        self.last_status = status
        return {"status": status, "event": entry}

    def mouse_move_absolute(self, x: int, y: int) -> bool:
        res = self.inject_pointer_move(x, y, absolute=True)
        return res["status"] == "ok"

    def mouse_move_relative(self, dx: int, dy: int) -> bool:
        res = self.inject_pointer_move(dx, dy, absolute=False)
        return res["status"] == "ok"

    def mouse_click(self, button_mask: str = "0xC0") -> bool:
        res = self.inject_pointer_click(button_mask)
        return res["status"] == "ok"

    def mouse_down(self, button: str = "0x40") -> bool:
        return self.mouse_click(button)

    def mouse_up(self, button: str = "0x80") -> bool:
        return self.mouse_click(button)

    def compute_push_displacement(
        self,
        impulse_force: float,
        avatar_mass: float = 1.0,
        friction: float = 0.2,
    ) -> float:
        if avatar_mass <= 0:
            return 0.0
        accel = float(impulse_force) / float(avatar_mass)
        disp = max(0.0, accel * (1.0 - float(friction)))
        return round(disp, 2)

    def compute_impulse_displacement(
        self,
        impulse: Tuple[float, float],
        window_mass: float = 50.0,
        friction: float = 8.0,
    ) -> Tuple[float, float]:
        m = max(1.0, float(window_mass))
        mu = max(0.1, float(friction))
        return (impulse[0] / (m * mu), impulse[1] / (m * mu))

    def compute_collision_impulse(
        self,
        avatar_velocity: Tuple[float, float],
        avatar_mass: float,
        window_mass: float,
        normal: Tuple[float, float],
        restitution: float = 0.2,
    ) -> Tuple[float, float]:
        norm_len = math.hypot(normal[0], normal[1])
        if norm_len < 1e-6:
            return (0.0, 0.0)
        nx = normal[0] / norm_len
        ny = normal[1] / norm_len
        v_rel_n = (avatar_velocity[0] * nx) + (avatar_velocity[1] * ny)
        if v_rel_n <= 0.0:
            return (0.0, 0.0)
        inv_mass_sum = (1.0 / max(0.1, float(avatar_mass))) + (1.0 / max(1.0, float(window_mass)))
        j_mag = ((1.0 + float(restitution)) * v_rel_n) / inv_mass_sum
        return (j_mag * nx, j_mag * ny)

    def add_window_impulse(
        self,
        address: str,
        impulse: Tuple[float, float],
        window_mass: float = 50.0,
        friction: float = 8.0,
    ) -> None:
        addr = self.normalize_address(address)
        m = max(1.0, float(window_mass))
        vx0 = impulse[0] / m
        vy0 = impulse[1] / m
        if addr in self.active_impulses:
            cur = self.active_impulses[addr]
            cur.vx += vx0
            cur.vy += vy0
            cur.mass = m
            cur.friction = max(0.1, float(friction))
        else:
            self.active_impulses[addr] = WindowImpulseState(
                address=addr,
                vx=vx0,
                vy=vy0,
                mass=m,
                friction=max(0.1, float(friction)),
            )

    def step_physics(self, dt: float) -> List[Tuple[str, int, int]]:
        displacements: List[Tuple[str, int, int]] = []
        stopped: List[str] = []

        for addr, state in self.active_impulses.items():
            state.accum_x += state.vx * dt
            state.accum_y += state.vy * dt
            dx = int(round(state.accum_x))
            dy = int(round(state.accum_y))
            if dx != 0 or dy != 0:
                displacements.append((addr, dx, dy))
                state.accum_x -= dx
                state.accum_y -= dy

            damping = max(0.0, 1.0 - (state.friction * dt))
            state.vx *= damping
            state.vy *= damping

            if math.hypot(state.vx, state.vy) < 0.5:
                stopped.append(addr)

        for addr in stopped:
            del self.active_impulses[addr]

        return displacements

    def get_action_feedback(self) -> Dict[str, str]:
        return {
            "last_action": self.last_action,
            "status": self.last_status,
        }

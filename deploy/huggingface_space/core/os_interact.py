"""
OS & Application Interaction Module for Vanessa.
Full integration with Wayland, Hyprland, and desktop applications:
- Type text into active windows (wtype)
- Open/close tabs (Ctrl+T, Ctrl+W)
- Save documents (Ctrl+S)
- Close/kill active windows (hyprctl dispatch killactive)
- Switch focus between windows (hyprctl dispatch cyclenext)
- Hyprland Multi-workspace management (switch, query, move window)
- Launch applications into specific or current workspaces
- Complete system process management and telemetry via psutil (CPU, RAM, Disk, Battery)
- Safe shell command execution
- Desktop screenshot capture via grim
"""
import os
import json
import shutil
import subprocess
import time
from typing import Dict, Any, Optional, List, Tuple

try:
    import psutil
except ImportError:
    psutil = None


class OSInteractor:
    def __init__(self):
        # Known common application binary mappings
        self.app_aliases = {
            "firefox": "firefox",
            "navegador": "firefox",
            "browser": "firefox",
            "chrome": "google-chrome-stable",
            "brave": "brave",
            "terminal": "kitty",
            "consola": "kitty",
            "kitty": "kitty",
            "alacritty": "alacritty",
            "konsole": "konsole",
            "vscode": "code",
            "code": "code",
            "codigo": "code",
            "antigravity": "antigravity",
            "dolphin": "dolphin",
            "archivos": "dolphin",
            "carpetas": "dolphin",
            "explorador": "dolphin",
            "spotify": "spotify",
            "musica": "spotify",
            "discord": "discord",
            "steam": "steam",
            "juegos": "steam",
            "telegram": "telegram-desktop",
            "calc": "kcalc",
            "calculadora": "kcalc",
            "vlc": "vlc",
            "gimp": "gimp",
            "obs": "obs",
            "writer": "libreoffice --writer",
            "word": "libreoffice --writer",
            "calc_office": "libreoffice --calc",
            "excel": "libreoffice --calc"
        }

    # === SHELL & COMMAND EXECUTION (Open-Interpreter style) ===
    def run_shell_command(self, command: str, timeout_sec: int = 15) -> Dict[str, Any]:
        """
        Executes a shell command safely in bash with output capture, returncode, and timeout handling.
        """
        clean_cmd = command.strip()
        if not clean_cmd:
            return {"success": False, "output": "Comando vacío.", "returncode": -1}

        # Safety filters for dangerous operations
        lower_cmd = clean_cmd.lower()
        if "rm -rf /" in lower_cmd or "mkfs" in lower_cmd or "dd if=" in lower_cmd and "of=/dev" in lower_cmd:
            return {"success": False, "output": "Comando bloqueado por políticas de seguridad de Vanessa.", "returncode": -1}

        try:
            proc = subprocess.run(
                ["bash", "-c", clean_cmd],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False
            )
            out = proc.stdout.strip()
            err = proc.stderr.strip()
            combined = out if not err else (f"{out}\n{err}".strip() if out else err)

            return {
                "success": proc.returncode == 0,
                "output": combined or "(Sin salida)",
                "returncode": proc.returncode,
                "command": clean_cmd
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": f"Tiempo de espera agotado ({timeout_sec}s).", "returncode": -1}
        except Exception as e:
            return {"success": False, "output": f"Error ejecutando comando: {e}", "returncode": -1}

    # === SYSTEM TELEMETRY & PROCESS CONTROL (psutil) ===
    def get_system_telemetry(self) -> Dict[str, Any]:
        """Returns comprehensive real-time system metrics (CPU, RAM, Disk, Battery, Uptime)."""
        if not psutil:
            return {"error": "psutil no está disponible."}

        cpu_pct = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count(logical=True)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        battery_info = "Sin batería / Conectado a corriente"
        battery_pct = None
        if hasattr(psutil, "sensors_battery"):
            bat = psutil.sensors_battery()
            if bat:
                status = "Cargando" if bat.power_plugged else "En batería"
                battery_pct = round(bat.percent, 1)
                battery_info = f"{battery_pct}% ({status})"

        uptime_sec = time.time() - psutil.boot_time()
        uptime_str = f"{int(uptime_sec // 3600)}h {int((uptime_sec % 3600) // 60)}m"

        return {
            "cpu_percent": cpu_pct,
            "cpu_cores": cpu_count,
            "ram_used_gb": round(mem.used / (1024**3), 2),
            "ram_total_gb": round(mem.total / (1024**3), 2),
            "ram_percent": mem.percent,
            "disk_used_gb": round(disk.used / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_percent": disk.percent,
            "battery": battery_info,
            "battery_percent": battery_pct,
            "uptime": uptime_str,
            "processes_count": len(psutil.pids())
        }

    def list_running_processes(self, limit: int = 15, sort_by: str = "memory") -> List[Dict[str, Any]]:
        """Lists top running processes sorted by memory or CPU usage."""
        if not psutil:
            return []

        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'username']):
            try:
                info = p.info
                procs.append({
                    "pid": info['pid'],
                    "name": info['name'] or "desconocido",
                    "cpu_percent": round(info['cpu_percent'] or 0.0, 1),
                    "memory_percent": round(info['memory_percent'] or 0.0, 1),
                    "user": info['username'] or ""
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        sort_key = "cpu_percent" if sort_by.lower() == "cpu" else "memory_percent"
        procs.sort(key=lambda x: x[sort_key], reverse=True)
        return procs[:limit]

    def terminate_process(self, pid: Optional[int] = None, name: Optional[str] = None) -> Dict[str, Any]:
        """Safely terminates a process by PID or name."""
        if not psutil:
            return {"success": False, "error": "psutil no disponible"}

        if pid is not None:
            try:
                p = psutil.Process(pid)
                pname = p.name()
                p.terminate()
                return {"success": True, "message": f"Proceso '{pname}' (PID {pid}) terminado con éxito."}
            except Exception as e:
                return {"success": False, "error": f"Error terminando PID {pid}: {e}"}

        if name:
            killed = 0
            for p in psutil.process_iter(['pid', 'name']):
                try:
                    if name.lower() in (p.info['name'] or '').lower():
                        p.terminate()
                        killed += 1
                except Exception:
                    continue
            return {
                "success": killed > 0,
                "message": f"Se terminaron {killed} proceso(s) coincidente(s) con '{name}'." if killed > 0 else f"No se encontró proceso '{name}'."
            }

        return {"success": False, "error": "Debe especificar un PID o nombre de proceso."}

    def take_screenshot(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Captures full screen using grim (native Wayland screenshot tool)."""
        path = output_path or f"/tmp/vanessa_screenshot_{int(time.time())}.png"
        try:
            res = subprocess.run(["grim", path], capture_output=True, text=True, check=False)
            if res.returncode == 0 and os.path.exists(path):
                return {"success": True, "path": path}
            return {"success": False, "error": res.stderr.strip() or "Error al capturar pantalla con grim."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # === KEYBOARD & TEXT AUTOMATION (wtype) ===
    def execute_wtype(self, args: list) -> bool:
        try:
            res = subprocess.run(["wtype"] + args, capture_output=True, text=True, check=False, timeout=5)
            return res.returncode == 0
        except Exception as e:
            print(f"[OSInteractor] Error en wtype: {e}")
            return False

    def type_text(self, text: str) -> str:
        """Types text directly into whatever window currently has focus."""
        success = self.execute_wtype(["-d", "20", text])
        return f"Texto escrito en pantalla: '{text}'" if success else "No se pudo escribir en la aplicación activa."

    def close_current_tab(self) -> str:
        """Closes active tab (Ctrl+W) in browsers, editors, etc."""
        success = self.execute_wtype(["-M", "ctrl", "-k", "w", "-m", "ctrl"])
        return "Pestaña cerrada, Amo Víctor." if success else "Error al cerrar pestaña."

    def open_new_tab(self) -> str:
        """Opens a new tab (Ctrl+T)."""
        success = self.execute_wtype(["-M", "ctrl", "-k", "t", "-m", "ctrl"])
        return "Nueva pestaña abierta." if success else "Error al abrir pestaña."

    def save_file(self) -> str:
        """Saves current document (Ctrl+S)."""
        success = self.execute_wtype(["-M", "ctrl", "-k", "s", "-m", "ctrl"])
        return "Archivo guardado." if success else "Error al guardar archivo."

    def send_shortcut(self, shortcut: str) -> bool:
        """Sends a key combination via wtype, e.g. 'ctrl+a', 'ctrl+c', 'shift+End'."""
        parts = [p.strip() for p in shortcut.split("+")]
        modifiers = []
        key = parts[-1]
        for m in parts[:-1]:
            m_lower = m.lower()
            if m_lower in ("ctrl", "control"):
                modifiers.append("ctrl")
            elif m_lower in ("alt", "mod1"):
                modifiers.append("alt")
            elif m_lower in ("shift",):
                modifiers.append("shift")
            elif m_lower in ("super", "win", "mod4"):
                modifiers.append("logo")

        args = []
        for mod in modifiers:
            args.extend(["-M", mod])
        args.extend(["-k", key])
        for mod in reversed(modifiers):
            args.extend(["-m", mod])

        return self.execute_wtype(args)

    def select_all_text(self) -> bool:
        return self.send_shortcut("ctrl+a")

    def copy_selected_text(self) -> bool:
        return self.send_shortcut("ctrl+c")

    def highlight_line(self) -> bool:
        self.send_shortcut("Home")
        time.sleep(0.04)
        return self.send_shortcut("shift+End")

    def close_active_window(self) -> str:
        """Closes active window via Hyprland dispatcher."""
        try:
            res = subprocess.run(["hyprctl", "dispatch", "killactive"], capture_output=True, text=True, check=False)
            return "Ventana activa cerrada." if res.returncode == 0 else "Error cerrando ventana."
        except Exception as e:
            return f"Error: {e}"

    def switch_window(self) -> str:
        """Switches focus to next window."""
        try:
            subprocess.run(["hyprctl", "dispatch", "cyclenext"], check=False)
            return "Cambiando a la siguiente ventana."
        except Exception as e:
            return f"Error: {e}"

    def focus_window_by_name(self, title_or_class: str) -> str:
        """Focuses window matching title or class."""
        try:
            res = subprocess.run(["hyprctl", "dispatch", "focuswindow", title_or_class], capture_output=True, text=True, check=False)
            if res.returncode == 0:
                return f"Ventana '{title_or_class}' enfocada con éxito."
            return f"No se encontró ventana con nombre '{title_or_class}'."
        except Exception as e:
            return f"Error: {e}"

    # === MOUSE CURSOR & DESKTOP MANIPULATION (ydotool) ===
    def get_cursor_position(self) -> Tuple[int, int]:
        """Gets current cursor coordinates via hyprctl."""
        try:
            out = subprocess.check_output(["hyprctl", "cursorpos"], stderr=subprocess.DEVNULL, text=True)
            parts = [int(p.strip()) for p in out.strip().split(",")]
            if len(parts) == 2:
                return parts[0], parts[1]
        except Exception:
            pass
        return (960, 540)

    def move_mouse_smooth(self, target_x: int, target_y: int, steps: int = 15) -> bool:
        """Smoothly moves cursor towards destination using ydotool."""
        cur_x, cur_y = self.get_cursor_position()
        try:
            for s in range(1, steps + 1):
                t = s / float(steps)
                # Cubic easing
                ease = 4 * (t**3) if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2
                ix = int(cur_x + (target_x - cur_x) * ease)
                iy = int(cur_y + (target_y - cur_y) * ease)
                ux = int(ix / 2.0)
                uy = int(iy / 2.0)
                subprocess.run(["ydotool", "mousemove", "-a", "-x", str(ux), "-y", str(uy)], check=False, timeout=1)
                time.sleep(0.015)
            return True
        except Exception as e:
            print(f"[OSInteractor] Error moviendo cursor: {e}")
            return False

    def click_mouse(self, button: str = "left", double: bool = False) -> str:
        btn_code = "0xC1" if button.lower() == "right" else "0xC0"
        try:
            subprocess.run(["ydotool", "click", btn_code], check=False, timeout=2)
            if double:
                time.sleep(0.08)
                subprocess.run(["ydotool", "click", btn_code], check=False, timeout=2)
            action_desc = "Doble clic" if double else f"Clic {button}"
            return f"{action_desc} realizado con éxito, Amo Víctor."
        except Exception as e:
            return f"Error ejecutando clic: {e}"

    def click_at(self, target_x: int, target_y: int, button: str = "left", double: bool = False, smooth: bool = True) -> str:
        if smooth:
            self.move_mouse_smooth(target_x, target_y)
        else:
            ux = int(target_x / 2.0)
            uy = int(target_y / 2.0)
            subprocess.run(["ydotool", "mousemove", "-a", "-x", str(ux), "-y", str(uy)], check=False)
            time.sleep(0.05)
        return self.click_mouse(button=button, double=double)

    def click_active_window(self, part: str = "center") -> str:
        win = self.get_active_window()
        if not win:
            return "No hay ninguna ventana activa detectada."
        at = win.get("at", [0, 0])
        size = win.get("size", [400, 300])

        if part == "close":
            tx = at[0] + size[0] - 25
            ty = at[1] + 18
            return self.click_at(tx, ty)
        elif part == "tabs":
            tx = at[0] + min(250, size[0] // 2)
            ty = at[1] + 45
            return self.click_at(tx, ty)
        else:
            tx = at[0] + size[0] // 2
            ty = at[1] + size[1] // 2
            return self.click_at(tx, ty)

    def get_all_windows(self) -> List[Dict[str, Any]]:
        try:
            res = subprocess.run(["hyprctl", "clients", "-j"], capture_output=True, text=True, check=False)
            if res.returncode == 0 and res.stdout.strip():
                return json.loads(res.stdout)
        except Exception:
            pass
        return []

    def get_monitor_geometry(self) -> Dict[str, Any]:
        """Returns monitor resolution and coordinates from Hyprland."""
        try:
            res = subprocess.run(["hyprctl", "monitors", "-j"], capture_output=True, text=True, check=False)
            if res.returncode == 0 and res.stdout.strip():
                monitors = json.loads(res.stdout)
                if isinstance(monitors, list) and monitors:
                    for m in monitors:
                        if m.get("focused"):
                            return {"width": m.get("width", 1920), "height": m.get("height", 1200), "name": m.get("name", "eDP-1")}
                    m = monitors[0]
                    return {"width": m.get("width", 1920), "height": m.get("height", 1200), "name": m.get("name", "eDP-1")}
        except Exception:
            pass
        return {"width": 1920, "height": 1200, "name": "default"}

    # === HYPRLAND MULTI-WORKSPACE CONTROLS ===
    def get_active_window(self) -> Dict[str, Any]:
        try:
            res = subprocess.run(["hyprctl", "activewindow", "-j"], capture_output=True, text=True, check=False)
            if res.returncode == 0 and res.stdout.strip():
                return json.loads(res.stdout)
        except Exception:
            pass
        return {}

    def get_active_workspace(self) -> Dict[str, Any]:
        try:
            res = subprocess.run(["hyprctl", "activeworkspace", "-j"], capture_output=True, text=True, check=False)
            if res.returncode == 0 and res.stdout.strip():
                return json.loads(res.stdout)
        except Exception:
            pass
        return {"id": 1, "name": "1"}

    def get_workspaces(self) -> List[Dict[str, Any]]:
        try:
            res = subprocess.run(["hyprctl", "workspaces", "-j"], capture_output=True, text=True, check=False)
            if res.returncode == 0 and res.stdout.strip():
                return json.loads(res.stdout)
        except Exception:
            pass
        return []

    def switch_workspace(self, workspace_num: int) -> str:
        try:
            cmd = ["hyprctl", "dispatch", "workspace", str(workspace_num)]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode == 0:
                return f"Cambiado al escritorio {workspace_num}, Amo Víctor."
            return f"No se pudo cambiar al escritorio {workspace_num}."
        except Exception as e:
            return f"Error cambiando de escritorio: {e}"

    def move_window_to_workspace(self, workspace_num: int) -> str:
        try:
            cmd = ["hyprctl", "dispatch", "movetoworkspace", str(workspace_num)]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode == 0:
                return f"Ventana trasladada al escritorio {workspace_num}."
            return f"Error al mover ventana al escritorio {workspace_num}."
        except Exception as e:
            return f"Error moviendo ventana: {e}"

    def launch_app(self, app_name: str, workspace_id: Optional[int] = None) -> str:
        clean_app = app_name.lower().strip()
        binary_cmd = self.app_aliases.get(clean_app, clean_app)

        first_bin = binary_cmd.split()[0]
        if not shutil.which(first_bin):
            if clean_app in ("terminal", "consola"):
                for term in ["kitty", "alacritty", "konsole", "xterm"]:
                    if shutil.which(term):
                        binary_cmd = term
                        break

        try:
            if workspace_id is not None:
                dispatch_cmd = ["hyprctl", "dispatch", "exec", f"[workspace {workspace_id}] {binary_cmd}"]
                res = subprocess.run(dispatch_cmd, capture_output=True, text=True, check=False)
                if res.returncode == 0:
                    return f"Abriendo {app_name} en el escritorio {workspace_id}, Amo Víctor."
                else:
                    self.switch_workspace(workspace_id)
                    subprocess.Popen(binary_cmd.split())
                    return f"Cambiado al escritorio {workspace_id} y abriendo {app_name}."
            else:
                subprocess.Popen(binary_cmd.split())
                return f"Abriendo {app_name} en el escritorio actual, Amo Víctor."
        except Exception as e:
            return f"No se pudo abrir '{app_name}': {e}"

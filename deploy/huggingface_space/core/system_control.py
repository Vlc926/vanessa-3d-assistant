"""
Linux System Automation & Hardware Controller.
Handles:
- Keyboard Backlight (brightnessctl)
- Wi-Fi (nmcli)
- Bluetooth (bluetoothctl)
- Audio Volume (pactl)
- Web Browser & YouTube launch
- Word Document (.docx) creation
"""
import os
import subprocess
import webbrowser
from typing import Dict, Any, Optional
from datetime import datetime
from docx import Document

class SystemController:
    def __init__(self, kbd_device: str = "asus::kbd_backlight"):
        self.kbd_device = kbd_device

    def execute_command(self, cmd: list) -> Dict[str, Any]:
        """Runs a safe Linux shell command and captures return code and output."""
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=10
            )
            return {
                "success": res.returncode == 0,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # === KEYBOARD LIGHTING ===
    def set_keyboard_backlight(self, state_or_val: str) -> str:
        """
        Controls keyboard lighting.
        Supports: 'on', 'off', 'max', 'min', or a numeric value (0 to 3).
        """
        val_map = {
            "on": "3",
            "max": "3",
            "encender": "3",
            "prender": "3",
            "off": "0",
            "apagar": "0",
            "min": "1",
            "medio": "2"
        }
        val = val_map.get(str(state_or_val).lower(), str(state_or_val))
        cmd = ["brightnessctl", f"--device={self.kbd_device}", "set", val]
        res = self.execute_command(cmd)
        if res.get("success"):
            return f"Luces del teclado ajustadas a nivel {val}."
        else:
            # Fallback to wildcard device if asus is not matching
            fallback_cmd = ["brightnessctl", "--device=*kbd*", "set", val]
            fb_res = self.execute_command(fallback_cmd)
            if fb_res.get("success"):
                return f"Luces del teclado ajustadas."
            return f"No se pudo cambiar la luz del teclado: {res.get('stderr') or res.get('error')}"

    # === WI-FI CONTROLS ===
    def set_wifi(self, enabled: bool) -> str:
        state = "on" if enabled else "off"
        cmd = ["nmcli", "radio", "wifi", state]
        res = self.execute_command(cmd)
        if res.get("success"):
            return f"Wi-Fi {'activado' if enabled else 'desactivado'} correctamente."
        return f"Error al cambiar Wi-Fi: {res.get('stderr')}"

    def get_wifi_status(self) -> str:
        cmd = ["nmcli", "radio", "wifi"]
        res = self.execute_command(cmd)
        if res.get("success"):
            status = "conectado/activo" if "enabled" in res["stdout"] else "desactivado"
            return f"El estado del Wi-Fi es: {status}."
        return "No se pudo obtener el estado del Wi-Fi."

    # === BLUETOOTH CONTROLS ===
    def set_bluetooth(self, enabled: bool) -> str:
        state = "on" if enabled else "off"
        cmd = ["bluetoothctl", "power", state]
        res = self.execute_command(cmd)
        if res.get("success"):
            return f"Bluetooth {'encendido' if enabled else 'apagado'} correctamente."
        return f"Error al cambiar Bluetooth: {res.get('stderr')}"

    # === VOLUME CONTROLS ===
    def adjust_volume(self, action: str) -> str:
        """action: 'up', 'down', 'mute', 'unmute'"""
        if action == "up":
            cmd = ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"]
        elif action == "down":
            cmd = ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-10%"]
        elif action == "mute":
            cmd = ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1"]
        elif action == "unmute":
            cmd = ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"]
        else:
            return "Acción de volumen no reconocida."

        res = self.execute_command(cmd)
        return "Volumen ajustado." if res.get("success") else "Error ajustando volumen."

    # === SCREEN BRIGHTNESS CONTROLS ===
    def adjust_screen_brightness(self, action: str) -> str:
        """action: 'up', 'down', 'max', 'min' or percentage"""
        if action == "up":
            cmd = ["brightnessctl", "set", "+10%"]
        elif action == "down":
            cmd = ["brightnessctl", "set", "10%-"]
        elif action == "max":
            cmd = ["brightnessctl", "set", "100%"]
        elif action == "min":
            cmd = ["brightnessctl", "set", "15%"]
        else:
            cmd = ["brightnessctl", "set", f"{action}%"]
        res = self.execute_command(cmd)
        return "Brillo de pantalla ajustado." if res.get("success") else "Error ajustando brillo de pantalla."

    # === HYPRLAND DESKTOP & WINDOW MANAGEMENT ===
    def hyprland_dispatch(self, dispatcher: str, arg: str = "") -> str:
        """Dispatches commands directly to Hyprland compositor (workspaces, full screen, tiling, close window)."""
        cmd = ["hyprctl", "dispatch", dispatcher]
        if arg:
            cmd.append(str(arg))
        res = self.execute_command(cmd)
        if res.get("success"):
            return f"Acción '{dispatcher}' ejecutada en Hyprland."
        return f"Error ejecutando '{dispatcher}': {res.get('stderr')}"

    # === APP LAUNCHER ===
    def launch_app(self, app: str) -> str:
        """Launches desktop applications smoothly in background."""
        app_map = {
            "terminal": ["kitty"],
            "consola": ["kitty"],
            "navegador": ["google-chrome-stable"],
            "chrome": ["google-chrome-stable"],
            "firefox": ["firefox"],
            "vscode": ["code"],
            "codigo": ["code"],
            "código": ["code"],
            "editor": ["code"],
            "archivos": ["thunar"],
            "explorador": ["thunar"],
            "spotify": ["spotify"],
            "discord": ["discord"]
        }
        cmd = app_map.get(app.lower().strip(), [app])
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Abriendo {app} en tu sistema, Amo Víctor."
        except Exception as e:
            # Fallback to xdg-open or command directly
            try:
                subprocess.Popen([app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"Iniciando {app}."
            except Exception:
                return f"No se pudo iniciar {app}: {e}"

    # === SYSTEM STATS (CPU, RAM, BATTERY) ===
    def get_system_stats(self) -> str:
        """Gathers system health metrics (RAM, CPU, Battery)."""
        metrics = []
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            ram = psutil.virtual_memory()
            metrics.append(f"CPU: {cpu}%")
            metrics.append(f"RAM: {ram.percent}% ({ram.used // (1024*1024)}MB / {ram.total // (1024*1024)}MB)")
            bat = psutil.sensors_battery()
            if bat:
                status = "cargando" if bat.power_plugged else "en batería"
                metrics.append(f"Batería: {bat.percent:.0f}% ({status})")
        except ImportError:
            try:
                res = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=2)
                lines = res.stdout.strip().split("\n")
                if len(lines) > 1:
                    parts = lines[1].split()
                    total, used = parts[1], parts[2]
                    metrics.append(f"RAM: {used}MB usados de {total}MB")
            except Exception:
                pass
        return " | ".join(metrics) if metrics else "Sistema funcionando con normalidad."

    # === BROWSER & APPS ===
    def open_youtube(self, search_query: Optional[str] = None) -> str:
        if search_query:
            url = f"https://www.youtube.com/results?search_query={search_query.replace(' ', '+')}"
            webbrowser.open(url)
            return f"Abriendo YouTube con la búsqueda: '{search_query}'."
        else:
            webbrowser.open("https://www.youtube.com")
            return "Abriendo YouTube en tu navegador."

    def open_website(self, url: str) -> str:
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)
        return f"Abriendo {url} en tu navegador."

    # === WORD DOCUMENT CREATION ===
    def create_word_document(self, title: str, content: str = "", filename: Optional[str] = None) -> str:
        """Creates a .docx file in the user's Documents or desktop directory."""
        try:
            doc = Document()
            doc.add_heading(title, level=0)
            
            # Add metadata timestamp
            doc.add_paragraph(f"Generado por tu asistente el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}")
            doc.add_paragraph("--------------------------------------------------")
            
            if content:
                for paragraph in content.split("\n\n"):
                    if paragraph.strip():
                        doc.add_paragraph(paragraph.strip())
            else:
                doc.add_paragraph("Documento creado listo para editar.")

            # Save in ~/Documents or home
            docs_dir = os.path.expanduser("~/Documentos")
            if not os.path.exists(docs_dir):
                docs_dir = os.path.expanduser("~/Documents")
            if not os.path.exists(docs_dir):
                docs_dir = os.path.expanduser("~")

            safe_name = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).rstrip()
            if not safe_name:
                safe_name = f"Documento_{int(datetime.now().timestamp())}"
            
            if filename:
                final_name = filename if filename.endswith(".docx") else f"{filename}.docx"
            else:
                final_name = f"{safe_name}.docx"

            file_path = os.path.join(docs_dir, final_name)
            doc.save(file_path)
            return f"¡Listo! Archivo Word creado con éxito en: {file_path}"
        except Exception as e:
            return f"Hubo un problema al crear el archivo Word: {str(e)}"

    # === COMPUTER SHUTDOWN ===
    def shutdown_computer(self) -> str:
        """Shuts down the Linux computer."""
        try:
            # We schedule shutdown in 5 seconds to give time for verbal confirmation
            subprocess.Popen(["systemctl", "poweroff"])
            return "Entendido, Amo. Apagando el equipo inmediatamente. Que descanse."
        except Exception as e:
            return f"No se pudo apagar el equipo: {str(e)}"

    # === DESKTOP NOTIFICATIONS ===
    def show_desktop_notification(self, title: str, message: str):
        """Sends native desktop notification via notify-send."""
        try:
            subprocess.Popen(["notify-send", "-a", "Vanessa", title, message])
        except Exception:
            pass

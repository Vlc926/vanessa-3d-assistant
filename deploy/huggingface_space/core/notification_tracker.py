"""
Notification Tracker & Real-Time D-Bus Monitor for Vanessa.
Intercepts desktop notifications via org.freedesktop.Notifications
and coordinates curious, gossiping ('chismosa'), and jealous reactions.
"""
import time
import subprocess
import threading
import re
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal


class NotificationTracker(QObject):
    notification_received = pyqtSignal(str, str, str)  # app_name, title, body

    def __init__(self, parent=None, min_interval_sec: float = 12.0):
        super().__init__(parent)
        self.min_interval_sec = min_interval_sec
        self.last_reaction_time = 0.0
        self._is_running = True
        self._thread: Optional[threading.Thread] = None

    def start_monitoring(self):
        """Starts background D-Bus listener thread."""
        self._is_running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        print("[NotificationTracker] Monitor D-Bus de notificaciones iniciado.")

    def stop_monitoring(self):
        self._is_running = False

    def _monitor_loop(self):
        cmd = ["dbus-monitor", "--session", "path=/org/freedesktop/Notifications,member=Notify"]
        while self._is_running:
            proc = None
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    bufsize=1
                )

                collecting_strings = []
                in_notify = False

                for line in iter(proc.stdout.readline, ''):
                    if not self._is_running:
                        break

                    line_str = line.strip()

                    if "member=Notify" in line_str:
                        in_notify = True
                        collecting_strings = []
                        continue

                    if in_notify:
                        # Capture strings following Notify signature: app_name, replaces_id (uint), icon (string), summary (string), body (string)
                        match = re.match(r'string\s+"(.*)"', line_str)
                        if match:
                            collecting_strings.append(match.group(1))

                        # When we have app_name, icon, summary, body (at least 3-4 strings)
                        if len(collecting_strings) >= 4 or "array [" in line_str:
                            in_notify = False
                            if len(collecting_strings) >= 3:
                                app_name = collecting_strings[0] if collecting_strings else "Sistema"
                                title = collecting_strings[2] if len(collecting_strings) > 2 else ""
                                body = collecting_strings[3] if len(collecting_strings) > 3 else ""

                                # Filter out self notifications
                                if app_name.lower() in ("vanessa", "vanessa maid", "vanessa desktop"):
                                    continue

                                now = time.time()
                                if now - self.last_reaction_time >= self.min_interval_sec:
                                    self.last_reaction_time = now
                                    print(f"[NotificationTracker] Notificación detectada: [{app_name}] {title} - {body}")
                                    self.notification_received.emit(app_name, title, body)

            except Exception as e:
                print(f"[NotificationTracker] Error en loop D-Bus: {e}")
                time.sleep(3)
            finally:
                if proc:
                    try:
                        proc.terminate()
                        proc.wait(timeout=0.5)
                    except Exception:
                        pass

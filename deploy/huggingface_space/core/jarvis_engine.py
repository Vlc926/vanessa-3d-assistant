"""
Jarvis Super-Intelligence Engine for Vanessa.
Inspired by top open-source Jarvis assistants (sukeesh/Jarvis, Microsoft JARVIS, Leon AI, AutoGPT):
- Proactive reminders, timers, and scheduled alerts with voice dispatch
- Knowledge retrieval: live weather (wttr.in/open-meteo), Wikipedia summaries, network diagnostics
- Multi-step execution routines / Iron Man Protocols (Trabajo, Descanso, Multimedia, Diagnóstico)
- Associative memory vault for user preferences and facts
"""
import os
import json
import time
import urllib.request
import urllib.parse
import threading
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from PyQt6.QtCore import QObject, pyqtSignal


class JarvisEngine(QObject):
    reminder_due_signal = pyqtSignal(str)  # Emitted when a scheduled reminder is due

    def __init__(self, memory_mgr, os_interact, sys_ctrl, tts=None):
        super().__init__()
        self.memory_mgr = memory_mgr
        self.os_interact = os_interact
        self.sys_ctrl = sys_ctrl
        self.tts = tts

        # Active reminders in-memory queue: list of dicts
        self.reminders: List[Dict[str, Any]] = []
        self._init_reminders_table()
        self._load_pending_reminders()

        # Start background reminder daemon thread
        self._reminder_thread_running = True
        self._reminder_thread = threading.Thread(target=self._reminder_worker_loop, daemon=True)
        self._reminder_thread.start()

    def _init_reminders_table(self):
        try:
            with self.memory_mgr._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS jarvis_reminders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        text TEXT,
                        due_timestamp REAL,
                        is_completed INTEGER DEFAULT 0,
                        created_at REAL
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS jarvis_knowledge_vault (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        topic TEXT UNIQUE,
                        fact TEXT,
                        updated_at REAL
                    )
                ''')
                conn.commit()
        except Exception as e:
            print(f"[JarvisEngine] Error inicializando tablas: {e}")

    def _load_pending_reminders(self):
        try:
            with self.memory_mgr._get_connection() as conn:
                cursor = conn.cursor()
                now = time.time()
                cursor.execute(
                    "SELECT id, text, due_timestamp FROM jarvis_reminders WHERE is_completed = 0 AND due_timestamp > ?",
                    (now,)
                )
                rows = cursor.fetchall()
                for r in rows:
                    self.reminders.append({
                        "id": r[0],
                        "text": r[1],
                        "due_timestamp": r[2]
                    })
        except Exception as e:
            print(f"[JarvisEngine] Error cargando recordatorios pendientes: {e}")

    def _reminder_worker_loop(self):
        while self._reminder_thread_running:
            now = time.time()
            due_items = [r for r in self.reminders if r["due_timestamp"] <= now]
            for item in due_items:
                self.reminders.remove(item)
                # Mark as completed in DB
                try:
                    with self.memory_mgr._get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE jarvis_reminders SET is_completed = 1 WHERE id = ?", (item["id"],))
                        conn.commit()
                except Exception:
                    pass

                print(f"[JarvisEngine] Recordatorio activado: '{item['text']}'")
                self.reminder_due_signal.emit(item["text"])

            time.sleep(1.0)

    # === REMINDERS & SCHEDULER ===
    def set_reminder(self, text: str, delay_seconds: int) -> Dict[str, Any]:
        """Schedules a proactive reminder after delay_seconds."""
        now = time.time()
        due = now + max(1, delay_seconds)
        rem_id = 0
        try:
            with self.memory_mgr._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO jarvis_reminders (text, due_timestamp, is_completed, created_at) VALUES (?, ?, 0, ?)",
                    (text, due, now)
                )
                conn.commit()
                rem_id = cursor.lastrowid
        except Exception as e:
            print(f"[JarvisEngine] Error guardando recordatorio: {e}")

        item = {"id": rem_id, "text": text, "due_timestamp": due}
        self.reminders.append(item)

        mins = delay_seconds // 60
        secs = delay_seconds % 60
        time_str = f"{mins} minuto(s)" if mins > 0 else f"{secs} segundo(s)"
        return {
            "success": True,
            "id": rem_id,
            "text": text,
            "delay_str": time_str,
            "message": f"Recordatorio programado para dentro de {time_str}: «{text}»"
        }

    def get_pending_reminders(self) -> List[Dict[str, Any]]:
        now = time.time()
        results = []
        for r in sorted(self.reminders, key=lambda x: x["due_timestamp"]):
            remain_sec = max(0, int(r["due_timestamp"] - now))
            m, s = divmod(remain_sec, 60)
            results.append({
                "id": r["id"],
                "text": r["text"],
                "remaining_seconds": remain_sec,
                "remaining_str": f"{m}m {s}s" if m > 0 else f"{s}s"
            })
        return results

    # === KNOWLEDGE & LIVE INTEL RETRIEVAL ===
    def get_weather(self, city: str = "") -> Dict[str, Any]:
        """
        Fetches live weather without API keys using wttr.in JSON service.
        """
        target = urllib.parse.quote(city.strip()) if city else ""
        url = f"https://wttr.in/{target}?format=j1" if target else "https://wttr.in/?format=j1"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
            with urllib.request.urlopen(req, timeout=4.5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                current = data.get("current_condition", [{}])[0]
                area = data.get("nearest_area", [{}])[0]
                city_name = area.get("areaName", [{}])[0].get("value", city or "Tu ubicación")
                country = area.get("country", [{}])[0].get("value", "")

                temp_c = current.get("temp_C", "?")
                feels_c = current.get("FeelsLikeC", temp_c)
                desc = current.get("weatherDesc", [{}])[0].get("value", "Despejado")
                humidity = current.get("humidity", "?")
                wind_kmh = current.get("windspeedKmph", "?")

                # Translate common English weather descriptions to friendly Spanish
                translations = {
                    "clear": "Despejado ☀️",
                    "sunny": "Soleado ☀️",
                    "partly cloudy": "Parcialmente nublado ⛅",
                    "cloudy": "Nublado ☁️",
                    "overcast": "Cubierto ☁️",
                    "light rain": "Lluvia ligera 🌦️",
                    "moderate rain": "Lluvia moderada 🌧️",
                    "heavy rain": "Lluvia intensa ⛈️",
                    "thunderstorm": "Tormenta eléctrica ⚡",
                    "mist": "Neblina 🌫️",
                    "fog": "Niebla densa 🌫️",
                    "patchy rain nearby": "Chubascos cercanos 🌦️"
                }
                desc_es = translations.get(desc.lower(), desc)

                summary = (
                    f"Amo Víctor, el clima en {city_name} ({country}) es {desc_es}: "
                    f"temperatura de {temp_c}°C (sensación de {feels_c}°C), "
                    f"humedad al {humidity}% y viento a {wind_kmh} km/h."
                )

                return {
                    "success": True,
                    "city": city_name,
                    "temperature_c": temp_c,
                    "feels_like_c": feels_c,
                    "description": desc_es,
                    "humidity": humidity,
                    "wind_kmh": wind_kmh,
                    "summary": summary
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "summary": "No pude conectar al servicio meteorológico en este momento, Amo Víctor."
            }

    def search_wikipedia_summary(self, query: str) -> Dict[str, Any]:
        """Fetches a concise Wikipedia summary in Spanish."""
        clean_q = query.strip()
        if not clean_q:
            return {"success": False, "error": "Consulta vacía."}

        encoded = urllib.parse.quote(clean_q)
        url = f"https://es.wikipedia.org/api/rest_v1/page/summary/{encoded}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "VanessaAssistant/2.0"})
            with urllib.request.urlopen(req, timeout=4.5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                title = data.get("title", clean_q)
                extract = data.get("extract", "")
                if extract:
                    # Truncate to 280 characters for natural speech
                    short_extract = extract[:280] + "..." if len(extract) > 280 else extract
                    return {
                        "success": True,
                        "title": title,
                        "extract": short_extract,
                        "summary": f"Amo Víctor, según Wikipedia: «{short_extract}»"
                    }
        except Exception as e:
            return {"success": False, "error": str(e)}

        return {"success": False, "error": f"No se encontró información sobre '{clean_q}'."}

    def get_network_diagnostics(self) -> Dict[str, Any]:
        """Inspects network interfaces, latency, and public IP."""
        public_ip = "Desconocida"
        try:
            req = urllib.request.Request("https://api.ipify.org?format=json", headers={"User-Agent": "curl/7.68.0"})
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                public_ip = json.loads(resp.read().decode('utf-8')).get("ip", "Desconocida")
        except Exception:
            pass

        # Latency check to Cloudflare DNS 1.1.1.1
        latency_ms = None
        try:
            out = subprocess.check_output(["ping", "-c", "1", "-W", "1", "1.1.1.1"], text=True)
            if "time=" in out:
                latency_ms = round(float(out.split("time=")[1].split(" ")[0]), 1)
        except Exception:
            pass

        return {
            "public_ip": public_ip,
            "latency_ms": latency_ms,
            "status": "Conectado a Internet" if latency_ms is not None else "Sin conexión directa",
            "summary": f"IP Pública: {public_ip} | Latencia: {latency_ms or '?'}ms ({'En línea' if latency_ms else 'Offline'})"
        }

    # === IRON MAN JARVIS PROTOCOLS (AUTOMATION MACROS) ===
    def execute_protocol(self, protocol_name: str, overlay=None) -> Dict[str, Any]:
        """
        Executes compound automation protocols (Trabajo, Descanso, Multimedia, Diagnóstico).
        """
        pname = protocol_name.lower().strip()

        if "trabajo" in pname or "programar" in pname or "codigo" in pname or "work" in pname:
            self.os_interact.switch_workspace(1)
            time.sleep(0.1)
            self.os_interact.launch_app("code", workspace_id=1)
            self.os_interact.launch_app("terminal", workspace_id=1)
            if overlay and hasattr(overlay, "vrm_widget"):
                overlay.vrm_widget.play_gesture("salute")
            msg = "⚡ ¡Protocolo Trabajo Activado, Amo Víctor! Espacio de desarrollo preparado con VS Code y terminal Kitty. A su servicio."
            return {"success": True, "protocol": "trabajo", "message": msg}

        elif "descanso" in pname or "dormir" in pname or "noche" in pname or "sleep" in pname:
            subprocess.run(["playerctl", "pause"], check=False)
            if overlay:
                overlay.set_volume(25)
                overlay.enter_sleep_mode()
                if hasattr(overlay, "vrm_widget"):
                    overlay.vrm_widget.start_motion("relax")
            msg = "🌙 ¡Protocolo Descanso Activado! Música pausada, volumen en 25% y modo reposo activado. Descanse plácidamente, Amo Víctor."
            return {"success": True, "protocol": "descanso", "message": msg}

        elif "multimedia" in pname or "fiesta" in pname or "musica" in pname or "party" in pname:
            self.os_interact.launch_app("spotify")
            if overlay:
                overlay.set_volume(75)
                if hasattr(overlay, "vrm_widget"):
                    overlay.vrm_widget.start_motion("happy_gesture")
            msg = "🎵 ¡Protocolo Multimedia Activado, Amo Víctor! Spotify listo, volumen al 75% y coreografía 3D en marcha. ¡A disfrutar!"
            return {"success": True, "protocol": "multimedia", "message": msg}

        elif "diagnostico" in pname or "salud" in pname or "escaneo" in pname or "health" in pname:
            tel = self.os_interact.get_system_telemetry()
            net = self.get_network_diagnostics()
            msg = (
                f"🛡️ ¡Diagnóstico Completo de Jarvis, Amo Víctor!\n"
                f"• CPU: {tel.get('cpu_percent')}% | RAM: {tel.get('ram_used_gb')}GB / {tel.get('ram_total_gb')}GB ({tel.get('ram_percent')}%)\n"
                f"• Red: {net.get('summary')}\n"
                f"• Batería: {tel.get('battery')} | Procesos activos: {tel.get('processes_count')}."
            )
            return {"success": True, "protocol": "diagnostico", "message": msg}

        return {"success": False, "error": f"Protocolo '{protocol_name}' no reconocido."}

    # === ASSOCIATIVE MEMORY VAULT ===
    def store_fact(self, topic: str, fact: str) -> bool:
        try:
            with self.memory_mgr._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO jarvis_knowledge_vault (topic, fact, updated_at) VALUES (?, ?, ?) "
                    "ON CONFLICT(topic) DO UPDATE SET fact = excluded.fact, updated_at = excluded.updated_at",
                    (topic.strip().lower(), fact.strip(), time.time())
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"[JarvisEngine] Error guardando hecho en memoria: {e}")
            return False

    def recall_fact(self, topic_query: str) -> Optional[str]:
        try:
            with self.memory_mgr._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT fact FROM jarvis_knowledge_vault WHERE topic LIKE ? LIMIT 1",
                    (f"%{topic_query.strip().lower()}%",)
                )
                row = cursor.fetchone()
                if row:
                    return row[0]
        except Exception:
            pass
        return None

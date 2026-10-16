import os
import re
import math
import json
import psutil
import datetime
import urllib.request
import urllib.parse
import subprocess
from typing import Dict, Any, List, Optional, Tuple

class AIIntelligenceHub:
    def __init__(self, overlay=None):
        self.overlay = overlay
        self.user_agent = "VanessaMaidAssistant/2.0 (Linux; Wayland/Hyprland)"

    def search_knowledge(self, query: str) -> Dict[str, Any]:
        cleaned_query = query.strip()
        try:
            wiki_url = f"https://es.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(cleaned_query)}"
            req = urllib.request.Request(wiki_url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                extract = data.get("extract", "")
                title = data.get("title", cleaned_query)
                if extract and len(extract) > 40:
                    return {
                        "source": "Wikipedia",
                        "title": title,
                        "text": extract[:380] + ("..." if len(extract) > 380 else ""),
                        "url": data.get("content_urls", {}).get("desktop", {}).get("page", "")
                    }
        except Exception:
            pass

        try:
            ddg_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(cleaned_query)}&format=json&no_html=1&skip_disambig=1"
            req = urllib.request.Request(ddg_url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                abstract = data.get("AbstractText", "")
                heading = data.get("Heading", cleaned_query)
                if abstract:
                    return {
                        "source": "DuckDuckGo",
                        "title": heading,
                        "text": abstract[:380],
                        "url": data.get("AbstractURL", "")
                    }
                topics = data.get("RelatedTopics", [])
                if topics and isinstance(topics, list) and isinstance(topics[0], dict):
                    rel_text = topics[0].get("Text", "")
                    if rel_text:
                        return {
                            "source": "DuckDuckGo",
                            "title": heading,
                            "text": rel_text[:380],
                            "url": topics[0].get("FirstURL", "")
                        }
        except Exception:
            pass

        return {
            "source": "none",
            "title": cleaned_query,
            "text": f"No encontré un resumen enciclopédico directo para '{cleaned_query}', pero puedo investigarlo a fondo con mi modelo de lenguaje.",
            "url": ""
        }

    def get_weather(self, location: str = "") -> Dict[str, Any]:
        target = location.strip() if location else ""
        url = f"https://wttr.in/{urllib.parse.quote(target)}?format=j1" if target else "https://wttr.in/?format=j1"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                current = data.get("current_condition", [{}])[0]
                nearest = data.get("nearest_area", [{}])[0]
                area_name = nearest.get("areaName", [{}])[0].get("value", "Su ubicación")
                country = nearest.get("country", [{}])[0].get("value", "")

                temp_c = current.get("temp_C", "--")
                feels_like = current.get("FeelsLikeC", temp_c)
                desc = current.get("lang_es", [{}])[0].get("value", current.get("weatherDesc", [{}])[0].get("value", "Despejado"))
                humidity = current.get("humidity", "--")
                wind = current.get("windspeedKmph", "--")

                summary = (
                    f"🌤️ Clima para Amo Víctor en {area_name}{f', {country}' if country else ''}:\n"
                    f"• Condición: {desc}\n"
                    f"• Temperatura: {temp_c}°C (Sensación: {feels_like}°C)\n"
                    f"• Humedad: {humidity}%\n"
                    f"• Viento: {wind} km/h"
                )

                return {
                    "status": "ok",
                    "location": area_name,
                    "country": country,
                    "temp_c": temp_c,
                    "feels_like": feels_like,
                    "description": desc,
                    "humidity": humidity,
                    "wind_kmh": wind,
                    "summary": summary
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"No pude consultar el clima en este momento, Amo Víctor: {e}",
                "summary": "🌤️ Servicio meteorológico no disponible temporalmente."
            }

    def get_morning_digest(self) -> str:
        now = datetime.datetime.now()
        dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        fecha_str = f"{dias[now.weekday()]}, {now.day} de {meses[now.month - 1]} de {now.year}"
        hora_str = now.strftime("%H:%M")

        t = self.get_hardware_telemetry()
        w = self.get_weather()
        weather_text = w.get("summary", "🌤️ Clima no disponible.")

        lines = [
            f"🌅 ¡Buenos días, Amo Víctor! Su informe matutino está listo:",
            f"📅 {fecha_str} | ⏰ {hora_str}",
            "",
            weather_text,
            "",
            f"💻 Estado de su equipo:",
            f"• CPU: {t['cpu_percent']}% | RAM libre: {t['ram_total_gb'] - t['ram_used_gb']:.1f} GB de {t['ram_total_gb']} GB",
            f"• Almacenamiento: {t['disk_free_gb']} GB disponibles en disco",
            f"• Energía: {t['battery']}",
            "",
            f"✨ ¡A su completo servicio para hacer de hoy un día extraordinario, mi Amo!"
        ]
        return "\n".join(lines)

    def get_hardware_telemetry(self) -> Dict[str, Any]:
        cpu_pct = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        battery_info = "Sin batería (conectado a corriente)"
        try:
            bat = psutil.sensors_battery()
            if bat:
                status = "Cargando" if bat.power_plugged else "Descargando"
                battery_info = f"{bat.percent:.0f}% ({status})"
        except Exception:
            pass

        top_procs = []
        try:
            for p in sorted(psutil.process_iter(['name', 'cpu_percent', 'memory_percent']),
                            key=lambda x: x.info['memory_percent'] or 0, reverse=True)[:3]:
                top_procs.append(f"{p.info['name']} ({p.info['memory_percent']:.1f}% RAM)")
        except Exception:
            pass

        return {
            "cpu_percent": cpu_pct,
            "ram_used_gb": round((mem.total - mem.available) / (1024 ** 3), 1),
            "ram_total_gb": round(mem.total / (1024 ** 3), 1),
            "ram_percent": mem.percent,
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024 ** 3), 1),
            "battery": battery_info,
            "top_processes": top_procs
        }

    def format_telemetry_report(self) -> str:
        t = self.get_hardware_telemetry()
        top_str = ", ".join(t["top_processes"]) if t["top_processes"] else "Ningún proceso pesado"
        return (
            f"📊 Estado del Sistema:\n"
            f"• CPU: {t['cpu_percent']}%\n"
            f"• RAM: {t['ram_used_gb']}GB / {t['ram_total_gb']}GB ({t['ram_percent']}%)\n"
            f"• Disco: {t['disk_free_gb']}GB libres ({t['disk_percent']}% en uso)\n"
            f"• Batería: {t['battery']}\n"
            f"• Procesos destacados: {top_str}"
        )

    def calculate_expression(self, expr: str) -> Optional[str]:
        cleaned = expr.strip().lower()
        cleaned = re.sub(r'^(cuanto es|calcula|calcular|resuelve|operacion|resultado de)\s*', '', cleaned)
        cleaned = cleaned.replace("×", "*").replace("÷", "/").replace("^", "**")

        allowed = set("0123456789+-*/()., %abs round sin cos tan sqrt pi e pow log")
        safe_str = "".join([c for c in cleaned if c in allowed or c.isalnum() or c in " _"])

        safe_dict = {
            "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "sqrt": math.sqrt, "pi": math.pi, "e": math.e,
            "pow": pow, "log": math.log, "abs": abs, "round": round
        }
        try:
            result = eval(safe_str, {"__builtins__": {}}, safe_dict)
            if isinstance(result, (int, float)):
                if isinstance(result, float) and result.is_integer():
                    return str(int(result))
                return f"{result:,.4f}".rstrip("0").rstrip(".")
        except Exception:
            pass
        return None

    def search_workspace(self, root_dir: str, keyword: str, max_results: int = 5) -> List[Dict[str, Any]]:
        results = []
        try:
            for root, dirs, files in os.walk(root_dir):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", ".venv", "__pycache__")]
                for f in files:
                    if f.startswith("."):
                        continue
                    full_p = os.path.join(root, f)
                    if keyword.lower() in f.lower():
                        results.append({
                            "filename": f,
                            "path": full_p,
                            "type": "name_match"
                        })
                    if len(results) >= max_results:
                        break
                if len(results) >= max_results:
                    break
        except Exception:
            pass
        return results

    def get_hyprland_windows(self) -> List[Dict[str, Any]]:
        try:
            res = subprocess.run(["hyprctl", "clients", "-j"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                windows = json.loads(res.stdout)
                return [w for w in windows if "Vanessa Maid" not in w.get("title", "") and w.get("mapped", False)]
        except Exception:
            pass
        return []

    def get_current_active_window(self) -> Optional[Dict[str, Any]]:
        try:
            res = subprocess.run(["hyprctl", "activewindow", "-j"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                win = json.loads(res.stdout)
                if win.get("mapped", False) and "Vanessa Maid" not in win.get("title", ""):
                    return win
        except Exception:
            pass
        return None

    def execute_playful_window_interaction(self) -> Tuple[str, str]:
        active_win = self.get_current_active_window()
        if not active_win:
            return ("idle_maid", "")

        title = active_win.get("title", "")
        app_cls = active_win.get("class", "").lower()

        if any(k in title.lower() or k in app_cls for k in ["youtube", "video", "twitch", "mpv", "vlc", "netflix", "crunchyroll"]):
            return ("museum_inspect", "")

        if "spotify" in app_cls or "spotify" in title.lower():
            return ("look_around_curious", "")

        elif any(k in title.lower() or k in app_cls for k in ["code", "writer", "word", "document", "bash", "fish", "antigravity", "terminal", "kitty"]):
            return ("curious_lean", "")

        else:
            return ("museum_inspect", "")

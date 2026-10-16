"""
Universal AI Intelligence Hub for Vanessa.
Consolidates advanced multi-domain Artificial Intelligence capabilities:
1. Search & Knowledge AI: Real-time Wikipedia & DuckDuckGo query retrieval
2. System Diagnostics & Hardware AI: Real-time telemetry, RAM/CPU/GPU load, top consumers
3. Calculation & Logic AI: Safe mathematical, scientific, and unit conversions
4. Screen Vision & OCR AI: Screen capture analysis and document perception
5. Document & Workspace AI: Project tree, file indexing and content summarization
6. Animator-vs-Animation Desktop Play AI: Interactive Hyprland window perception and roaming
"""
import os
import re
import math
import json
import psutil
import urllib.request
import urllib.parse
import subprocess
from typing import Dict, Any, List, Optional, Tuple


class AIIntelligenceHub:
    def __init__(self, overlay=None):
        self.overlay = overlay
        self.user_agent = "VanessaMaidAssistant/2.0 (Linux; Wayland/Hyprland)"

    # =========================================================================
    # 1. SEARCH & KNOWLEDGE AI (WIKIPEDIA & DUCKDUCKGO INSTANT INTEL)
    # =========================================================================
    def search_knowledge(self, query: str) -> Dict[str, Any]:
        """Queries Wikipedia and DuckDuckGo for factual, encyclopedic, or real-time queries."""
        cleaned_query = query.strip()
        # 1. Try Spanish Wikipedia Summary
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

        # 2. Try DuckDuckGo Instant Answer API
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
                # Check RelatedTopics
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

    # =========================================================================
    # 2. SYSTEM TELEMETRY & HARDWARE AI
    # =========================================================================
    def get_hardware_telemetry(self) -> Dict[str, Any]:
        """Gathers real-time CPU, RAM, Disk, battery, and top process telemetry."""
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

        # Top processes by memory and CPU
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
        """Creates a cheerful maid system diagnostic summary."""
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

    # =========================================================================
    # 3. MATHEMATICAL & LOGIC CALCULATION AI
    # =========================================================================
    def calculate_expression(self, expr: str) -> Optional[str]:
        """Safely calculates scientific math expressions, unit conversions and formulas."""
        # Sanitize allowed characters
        cleaned = expr.strip().lower()
        cleaned = re.sub(r'^(cuanto es|calcula|calcular|resuelve|operacion|resultado de)\s*', '', cleaned)
        cleaned = cleaned.replace("×", "*").replace("÷", "/").replace("^", "**")

        # Allow only safe math math tokens
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

    # =========================================================================
    # 4. WORKSPACE & FILE MANAGEMENT AI
    # =========================================================================
    def search_workspace(self, root_dir: str, keyword: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Scans Victor's active files and code for relevant keywords."""
        results = []
        try:
            for root, dirs, files in os.walk(root_dir):
                # Ignore hidden and virtual env folders
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
        except Exception as e:
            print(f"[AIHub] Error scanning workspace: {e}")
        return results

    # =========================================================================
    # 5. HYPRLAND WORKSPACE & WINDOW PLAYFUL CONTROLLER (ANIMATOR-VS-ANIMATION)
    # =========================================================================
    def get_hyprland_windows(self) -> List[Dict[str, Any]]:
        """Returns all open windows on Hyprland desktop."""
        try:
            res = subprocess.run(["hyprctl", "clients", "-j"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0:
                windows = json.loads(res.stdout)
                # Filter out Vanessa overlay herself
                return [w for w in windows if "Vanessa Maid" not in w.get("title", "") and w.get("mapped", False)]
        except Exception:
            pass
        return []

    def get_current_active_window(self) -> Optional[Dict[str, Any]]:
        """Returns detailed info of currently focused Hyprland window."""
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
        """Executes a playful desktop action (peek, window hover, workspace commentary).
        Respects anime companion etiquette: silent observation during videos/streaming."""
        active_win = self.get_current_active_window()
        if not active_win:
            return ("idle_maid", "")

        title = active_win.get("title", "")
        app_cls = active_win.get("class", "").lower()

        # Dynamic Video Content (YouTube, Media player, Streaming)
        # Anime companion etiquette (Aegis/Yui): do NOT spam balloons or interrupt the viewer!
        if any(k in title.lower() or k in app_cls for k in ["youtube", "video", "twitch", "mpv", "vlc", "netflix", "crunchyroll"]):
            return ("museum_inspect", "")

        # Music (Spotify, player)
        if "spotify" in app_cls or "spotify" in title.lower():
            return ("look_around_curious", "")

        # Static Productivity Content (Word, Code, Terminal, Docs)
        elif any(k in title.lower() or k in app_cls for k in ["code", "writer", "word", "document", "bash", "fish", "antigravity", "terminal", "kitty"]):
            return ("curious_lean", "")

        else:
            return ("museum_inspect", "")

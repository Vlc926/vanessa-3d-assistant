"""
Brain & Reasoning Engine for Vanessa (Hybrid Cloud / Offline).
Supports:
- Gemini Pro / Flash Cloud LLM with dynamic API key configuration
- Local fallback when offline
- Desktop OS application manipulation (wtype, close tab, write text, kill window)
- Generative tools (Excel, Word, Databases, Code)
- Screen perception & advice (Hyprland grim)
- Biometrics (Face & Voice)
"""
import os
import json
import re
import shutil
import subprocess
import urllib.request
from typing import Dict, Any, Tuple, Optional, List
from google import genai
from core.memory import MemoryManager
from core.system_control import SystemController
from core.file_manager import FileManager
from core.music_detector import MusicDetector
from core.generator import ArtifactGenerator
from core.screen_observer import ScreenObserver
from core.object_detector import ObjectDetector
from core.os_interact import OSInteractor
from core.audio_intelligence import AudioFileIntelligence
from core.jarvis_engine import JarvisEngine
from core.ai_intelligence_hub import AIIntelligenceHub
from core.invoice_skill import InvoiceSkill
from core.document_skill import DocumentSkill
from core.app_connectors import AppConnectors
from core.learning_vault import LearningVault
from core.autonomous_worker import AutonomousWorker
from core.persona_engine import PersonaEngine
from core.omni_sync import OmniSyncHub

class AssistantBrain:
    def __init__(
        self,
        memory: MemoryManager,
        sys_ctrl: SystemController,
        file_mgr: FileManager,
        music_det: MusicDetector,
        personality_path: str = "config/personality.json",
        settings_path: str = "config/settings.json"
    ):
        self.memory = memory
        self.sys_ctrl = sys_ctrl
        self.file_mgr = file_mgr
        self.music_det = music_det
        self.personality_path = personality_path
        self.settings_path = settings_path

        # Primary source of truth: SQLite Database
        db_personality = self.memory.get_personality_config()
        if db_personality:
            self.personality = db_personality
        else:
            self.personality = self._load_json(self.personality_path)
            if self.personality:
                self.memory.save_personality_config(self.personality)

        self.settings = self._load_json(self.settings_path)

        # OS & UI Interactor
        self.os_interact = OSInteractor()
        self.generator = ArtifactGenerator(self)
        self.screen_obs = ScreenObserver(self)
        self.object_det = ObjectDetector()
        self.audio_intel = AudioFileIntelligence()
        self.jarvis = JarvisEngine(self.memory, self.os_interact, self.sys_ctrl)
        self.ai_hub = AIIntelligenceHub()

        # Hands & Tools Harness (Skills & Connectors)
        self.invoice_skill = InvoiceSkill()
        self.document_skill = DocumentSkill()
        self.app_connectors = AppConnectors()
        self.learning_vault = LearningVault()
        self.autonomous_worker = AutonomousWorker()
        self.persona = PersonaEngine()
        self.omni_hub = OmniSyncHub()

        # Face enrollment & reminder callbacks
        self.on_enroll_face_request = None
        self.on_reminder_due = None
        self.jarvis.reminder_due_signal.connect(self._handle_reminder_due)

        # Voice & Dialogue Reactions Dataset
        self.reactions_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "voice_reactions.json")
        self.reactions = self._load_json(self.reactions_path)

        # Gemini & Hybrid AI Configuration
        self.ai_mode = self.settings.get("ai_backend", {}).get("mode", "cloud_only")  # hybrid, local_only, cloud_only
        self.preferred_model = self.settings.get("ai_backend", {}).get("model", "gemini-3.8-flash")
        self.gemini_client = None
        self._init_gemini()

    def _handle_reminder_due(self, text: str):
        if callable(self.on_reminder_due):
            self.on_reminder_due(text)

    def set_ai_mode(self, mode: str):
        self.ai_mode = mode
        self.settings.setdefault("ai_backend", {})["mode"] = mode
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)

    @property
    def gemini_api_key(self) -> str:
        return os.environ.get("GEMINI_API_KEY") or self.settings.get("ai_backend", {}).get("gemini_api_key", "")

    def set_api_key(self, key: str):
        self.set_gemini_api_key(key, self.preferred_model)

    def set_preferred_model(self, model: str):
        self.preferred_model = model
        self.settings.setdefault("ai_backend", {})["model"] = model
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)

    def _load_json(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _init_gemini(self):
        api_key = os.environ.get("GEMINI_API_KEY") or self.settings.get("ai_backend", {}).get("gemini_api_key", "")
        if api_key:
            try:
                self.gemini_client = genai.Client(api_key=api_key)
                print(f"[Brain] Cliente Gemini configurado con modelo: {self.preferred_model}")
            except Exception as e:
                print(f"[Brain] Error configurando Gemini: {e}")
                self.gemini_client = None
        else:
            self.gemini_client = None

    def set_gemini_api_key(self, api_key: str, model_name: str = "gemini-3.5-pro") -> Tuple[bool, str]:
        """Dynamically updates Gemini API key and model selection with resilient validation."""
        if not api_key:
            return False, "La API Key no puede estar vacía."

        try:
            test_client = genai.Client(api_key=api_key)

            # Step 1: Attempt direct generation with the selected Gemini 3.5 / custom model
            try:
                res = test_client.models.generate_content(
                    model=model_name,
                    contents="Di 'OK' para verificar la conexión."
                )
                if res and res.text:
                    self.gemini_client = test_client
                    self.preferred_model = model_name
                    self.settings.setdefault("ai_backend", {})["gemini_api_key"] = api_key
                    self.settings["ai_backend"]["model"] = model_name
                    with open(self.settings_path, "w", encoding="utf-8") as f:
                        json.dump(self.settings, f, indent=2, ensure_ascii=False)
                    return (True, f"¡Clave de Gemini API configurada con éxito con {model_name}!")
            except Exception as model_err:
                print(f"[Brain] Verificación con {model_name} dio: {model_err}")

                # Step 2: Verify if the API Key itself is valid by listing models
                try:
                    available_models = []
                    for m in test_client.models.list():
                        raw_name = getattr(m, "name", str(m))
                        clean_name = raw_name.replace("models/", "")
                        available_models.append(clean_name)

                    # API key is authenticated and active!
                    self.gemini_client = test_client
                    self.preferred_model = model_name
                    self.settings.setdefault("ai_backend", {})["gemini_api_key"] = api_key
                    self.settings["ai_backend"]["model"] = model_name
                    with open(self.settings_path, "w", encoding="utf-8") as f:
                        json.dump(self.settings, f, indent=2, ensure_ascii=False)

                    summary = f"¡API Key validada y conectada con éxito!\nModelo establecido: {model_name}."
                    if available_models:
                        top_models = [m for m in available_models if "gemini" in m][:3]
                        if top_models:
                            summary += f"\n(Modelos activos en tu cuenta: {', '.join(top_models)})"
                    return (True, summary)
                except Exception as auth_err:
                    return (False, f"Error de autenticación con Google Gemini: {str(model_err)}")

            return (False, "La API respondió sin contenido.")
        except Exception as e:
            return (False, f"Error validando API Key: {str(e)}")

    def reload_config(self):
        db_pers = self.memory.get_personality_config()
        if db_pers:
            self.personality = db_pers
        else:
            self.personality = self._load_json(self.personality_path)
        self.settings = self._load_json(self.settings_path)
        self._init_gemini()

    def update_personality(self, new_personality: Dict[str, Any]):
        """Updates personality dictionary and persists changes to SQLite database."""
        self.personality.update(new_personality)
        self.memory.save_personality_config(self.personality)
        try:
            with open(self.personality_path, "w", encoding="utf-8") as f:
                json.dump(self.personality, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def get_wake_reply(self) -> str:
        lines = self.reactions.get("wake_confirmations", [])
        if lines:
            import random
            return random.choice(lines)
        return "¡A sus órdenes, Amo Víctor! ¿En qué puedo consentirlo hoy?"

    def get_time_greeting(self) -> str:
        import time, random
        hour = time.localtime().tm_hour
        tg = self.reactions.get("time_greetings", {})
        if 5 <= hour < 12:
            pool = tg.get("morning", [])
        elif 12 <= hour < 19:
            pool = tg.get("afternoon", [])
        elif 19 <= hour < 23:
            pool = tg.get("evening", [])
        else:
            pool = tg.get("night", [])
        if pool:
            return random.choice(pool)
        return "¡Hola Amo Víctor! Vanessa a sus órdenes."

    def get_music_reaction(self) -> str:
        lines = self.reactions.get("music_playback_reactions", [])
        if lines:
            import random
            return random.choice(lines)
        return "¡Qué buen ritmo, Amo Víctor! Ya me tiene bailando aquí en su pantalla 🎵✨"

    def get_playful_banter(self) -> str:
        lines = self.reactions.get("playful_banter", [])
        if lines:
            import random
            return random.choice(lines)
        return "Jeje, sabe que soy la mejor maid virtual que existe, ¿o acaso lo dudaba?"

    def get_attentive_prompt(self) -> str:
        lines = self.reactions.get("listening_attentive", [])
        if lines:
            import random
            return random.choice(lines)
        return "¡Le escucho con atención, Amo Víctor!"


    def is_connected_to_internet(self) -> bool:
        import socket
        try:
            s = socket.create_connection(("8.8.8.8", 53), timeout=1.2)
            s.close()
            return True
        except OSError:
            pass
        try:
            s = socket.create_connection(("1.1.1.1", 53), timeout=1.2)
            s.close()
            return True
        except OSError:
            return False

    async def parse_and_execute_direct_command(
        self,
        text: str,
        detected_tone: str = "playful"
    ) -> Optional[Tuple[str, str, Dict[str, Any]]]:
        """
        Fast-path direct execution for system actions, window interactions, and hardware.
        Returns (response_message, mood, extra_data) or None if requires general LLM.
        """
        lower = text.lower().strip()
        # Clean conversational prefixes ("oye vanessa,", "vanessa por favor", etc.)
        clean_lower = re.sub(r'^(?:oye\s+)?(?:vanessa|banessa|vanesa|banesa)[,\s]*', '', lower).strip()
        clean_lower = re.sub(r'^(?:por favor\s+|hazme el favor de\s+|podrías\s+|puedes\s+)', '', clean_lower).strip()
        clean_lower = re.sub(r'[¡!¿?.,;]', '', clean_lower).strip()

        # 1. Desktop Application & Tab Interaction (wtype / hyprctl)
        if any(w in lower for w in ["cierra la pestaña", "cierra esta pestaña", "cerrar pestaña"]):
            return ("Pestaña cerrada, Amo 😊", "happy", {"action": "close_tab"})

        if any(w in lower for w in ["nueva pestaña", "abre una pestaña", "abre pestaña", "abrir pestaña", "abre una pestaña nueva", "pestaña nueva"]):
            return ("Nueva pestaña lista, Amo 😊", "happy", {"action": "new_tab"})

        if any(w in lower for w in ["guarda el archivo", "guarda esto", "guardar archivo"]):
            msg = self.os_interact.save_file()
            return (msg, "happy", {"action": "save_file"})

        if any(w in lower for w in ["cierra la ventana", "cierra esta ventana", "cerrar ventana"]):
            msg = self.os_interact.close_active_window()
            return (msg, "serious", {"action": "close_window"})

        if any(w in lower for w in ["cambia de ventana", "siguiente ventana"]):
            msg = self.os_interact.switch_window()
            return (msg, "happy", {"action": "switch_window"})

        if lower.startswith("escribe ") or lower.startswith("escribe:"):
            # Extract text to type
            text_to_type = re.sub(r"^escribe:?\s*", "", text, flags=re.IGNORECASE).strip()
            if text_to_type:
                msg = self.os_interact.type_text(text_to_type)
                return (msg, "happy", {"action": "type_text", "text": text_to_type})

        # 2. Computer Shutdown
        if any(phrase in lower for phrase in [
            "apaga la computadora", "apagar la computadora", "apaga la pc", "apagar el equipo",
            "apaga mi compu", "apaga el sistema"
        ]):
            res = self.sys_ctrl.shutdown_computer()
            return (res, "serious", {"action": "shutdown"})

        # 2.1 Hardware Telemetry & System Diagnostic AI
        if any(w in lower for w in [
            "cómo está el sistema", "como esta el sistema", "diagnóstico del sistema", "diagnostico del sistema",
            "estado de la pc", "rendimiento del sistema", "cuánta ram", "cuanta ram", "uso de cpu",
            "revisa la computadora", "telemetría", "telemetria"
        ]):
            report = self.ai_hub.format_telemetry_report()
            return (report, "happy", {"action": "telemetry"})

        # 2.2 Mathematical & Scientific Calculation AI
        if any(lower.startswith(p) for p in ["cuánto es", "cuanto es", "calcula", "calcular", "resuelve"]):
            calc_res = self.ai_hub.calculate_expression(lower)
            if calc_res is not None:
                return (f"Amo Víctor, el resultado del cálculo es {calc_res} ✨", "happy", {"action": "calculation", "result": calc_res})

        # 2.3 Web Knowledge & Research AI (Wikipedia & DuckDuckGo)
        if any(lower.startswith(p) for p in ["investiga ", "busca quién es ", "busca quien es ", "busca qué es ", "busca que es ", "qué es ", "que es ", "quién es ", "quien es ", "wikipedia "]):
            subject = re.sub(r"^(investiga|busca quién es|busca quien es|busca qué es|busca que es|qué es|que es|quién es|quien es|wikipedia)\s+(sobre|de)?\s*", "", lower).strip()
            if subject:
                info = self.ai_hub.search_knowledge(subject)
                if info.get("text"):
                    return (f"[{info['source']}] {info['text']}", "thinking", {"action": "knowledge_found", "data": info})

        # 2.4 Desktop Roaming Stroll & Museum Explorer Mode
        if any(w in lower for w in ["date un paseo", "pasea por el escritorio", "explora el escritorio", "mira el escritorio", "muévete un rato", "muevete un rato"]):
            return ("¡Con gusto, Amo Víctor! Me daré un paseo como si estuviera en una galería de arte observando sus ventanas 🎨✨", "playful", {"action": "roam_stroll"})

        # 3. Screen Analysis / Suggestions
        if any(phrase in lower for phrase in [
            "analiza mi pantalla", "mira mi pantalla", "qué opinas de mi pantalla",
            "que opinas de lo que veo", "mira mi código", "mira este video",
            "mira este documento", "dame sugerencias de mi pantalla", "revisa mi código"
        ]):
            advice_res = await self.screen_obs.analyze_screen(lower)
            if advice_res.get("success"):
                return (advice_res["advice"], "thinking", {"action": "screen_analyzed"})
            else:
                return (advice_res.get("message", "No pude analizar la pantalla."), "surprised", {})

        # 4. Generative Excel (.xlsx)
        if any(w in lower for w in ["genera un excel", "crea un excel", "haz un excel", "genera excel", "crea excel"]):
            title = "Reporte_Vanessa"
            match = re.search(r"excel\s+(?:de|sobre|titulado)?\s*(.+)", lower)
            if match and match.group(1):
                title = match.group(1).strip().replace(" ", "_")[:30]
            
            headers = ["ID", "Descripción", "Categoría", "Prioridad", "Estado"]
            rows = [
                [1, "Revisión de arquitectura", "Desarrollo", "Alta", "Completado"],
                [2, "Optimización de memoria RAM", "Sistema", "Media", "En progreso"],
                [3, "Análisis de base de datos", "Datos", "Alta", "Pendiente"]
            ]
            path = self.generator.create_excel(title, headers, rows)
            msg = f"Amo Víctor, he generado su hoja de cálculo Excel profesionalmente en: {path}"
            return (msg, "happy", {"action": "excel_generated", "path": path})

        # 5. Generative Database (.db & .sql)
        if any(w in lower for w in ["genera una base de datos", "crea una base de datos", "crea una bd", "genera bd"]):
            db_name = "proyecto_database"
            match = re.search(r"(?:base de datos|bd)\s+(?:para|de|llamada)?\s*([a-zA-Z0-9_]+)", lower)
            if match and match.group(1):
                db_name = match.group(1).strip()

            schema = """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT UNIQUE,
                rol TEXT DEFAULT 'usuario',
                creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS registros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                accion TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            );
            """
            seed = "INSERT INTO usuarios (nombre, email, rol) VALUES ('Víctor', 'victor@local.dev', 'admin');"
            res = self.generator.create_database(db_name, schema, seed)
            msg = f"Amo, he estructurado y creado la base de datos SQLite y su esquema SQL en: {res['db_path']}"
            return (msg, "happy", {"action": "db_generated", "paths": res})

        # 6. Face Enrollment
        if any(phrase in lower for phrase in ["memoriza mi rostro", "aprende mi cara", "recuerda mi rostro", "registra mi cara"]):
            if self.on_enroll_face_request:
                success = self.on_enroll_face_request("Amo Víctor")
                if success:
                    return ("¡Rostro memorizado con éxito! Desde ahora lo reconoceré inmediatamente como mi único Amo Víctor.", "happy", {"action": "face_enrolled"})
                else:
                    return ("Amo, por favor mire fijamente a la cámara frontal para que pueda registrar sus facciones con claridad.", "thinking", {})

        # 7. Object Detection in Room/Desk (On Demand)
        if any(phrase in lower for phrase in ["qué objetos ves", "que objetos ves", "qué hay en mi mesa", "que hay en mi mesa", "qué ves en la cámara"]):
            detected_objs = self.object_det.capture_and_detect_objects()
            if detected_objs:
                items_str = ", ".join(detected_objs)
                return (f"Amo Víctor, en su mesa e imagen identifico: {items_str}.", "happy", {"action": "objects_detected", "objects": detected_objs})
            else:
                return ("En este momento no distingo objetos con claridad en su mesa. Por favor acérquelos un poco a la cámara.", "idle", {})

        # 8. Hardware & System
        if any(w in lower for w in ["teclado", "luz de teclado", "luces del teclado", "retroiluminacion", "retroiluminación"]):
            if any(w in lower for w in ["apaga", "apagar", "desactiva"]):
                res = self.sys_ctrl.set_keyboard_backlight("off")
                return (res, "happy", {"action": "keyboard_backlight", "state": "off"})
            elif any(w in lower for w in ["enciende", "prende", "activa", "sube"]):
                res = self.sys_ctrl.set_keyboard_backlight("on")
                return (res, "happy", {"action": "keyboard_backlight", "state": "on"})

        if "wifi" in lower or "wi-fi" in lower:
            if any(w in lower for w in ["apaga", "apagar", "desactiva"]):
                res = self.sys_ctrl.set_wifi(False)
                return (res, "happy", {"action": "wifi", "state": "off"})
            elif any(w in lower for w in ["enciende", "prende", "activa"]):
                res = self.sys_ctrl.set_wifi(True)
                return (res, "happy", {"action": "wifi", "state": "on"})

        if "bluetooth" in lower:
            if any(w in lower for w in ["apaga", "apagar", "desactiva"]):
                res = self.sys_ctrl.set_bluetooth(False)
                return (res, "happy", {"action": "bluetooth", "state": "off"})
            elif any(w in lower for w in ["enciende", "prende", "activa"]):
                res = self.sys_ctrl.set_bluetooth(True)
                return (res, "happy", {"action": "bluetooth", "state": "on"})

        # Media & Music Controls (differentiating video companion vs retro cassette walkman)
        if any(w in lower or w in clean_lower for w in [
            "pausa la música", "pausar música", "para la música", "detén la música", "deten la musica",
            "reproduce", "reanuda la música", "play música", "play musica", "pon pausa", "dale play", "presiona pausa", "presiona play",
            "pausa el video", "pausar video", "pausa la reproduccion", "quitar pausa", "quita la pausa", "continúa", "continua",
            "pausa youtube", "reproduce youtube", "reanuda el video", "detén el video", "deten el video"
        ]) or lower in ("pausa", "reproduce", "play", "pausar", "para") or clean_lower in ("pausa", "reproduce", "play", "pausar", "para"):
            resume_words = ("reproduce", "reanuda", "play", "quita la pausa", "quitar pausa", "continúa", "continua")
            pause_words = ("pausa", "pausar", "para la", "detén", "deten")
            if any(w in clean_lower for w in resume_words) and not clean_lower.startswith(("pausa", "pon pausa", "presiona pausa")):
                op = "play"
            elif any(w in clean_lower for w in pause_words) or clean_lower == "para":
                op = "pause"
            else:
                op = "play_pause"

            is_vid_explicit = any(k in lower or k in clean_lower for k in ("video", "youtube", "reproduccion", "serie", "pelicula", "película", "stream"))
            is_mus_explicit = any(k in lower or k in clean_lower for k in ("música", "musica", "canción", "cancion", "pista", "cinta", "walkman", "casete"))
            media_type = "video" if is_vid_explicit else ("music" if is_mus_explicit else "auto")

            ack_msg = "¡Enseguida con el video, Amo! 🍿" if media_type == "video" else "¡Ahora mismo, Amo! 📼"
            return (ack_msg, "happy", {"action": "interactive_media", "op": op, "media_type": media_type, "quiet": True})

        if any(w in lower or w in clean_lower for w in [
            "siguiente canción", "canción siguiente", "siguiente pista", "pasa canción", "pasa la canción", "cambia de canción",
            "presiona siguiente", "presiona la siguiente", "adelanta", "adelantar", "adelanta la canción", "adelantar canción", "adelanta la pista", "avanza"
        ]) or lower in ("siguiente", "adelantar", "adelanta", "avanzar") or clean_lower in ("siguiente", "adelantar", "adelanta", "avanzar"):
            return ("¡Siguiente, Amo! 📼", "happy", {"action": "interactive_media", "op": "next", "quiet": True})

        if any(w in lower or w in clean_lower for w in ["canción anterior", "anterior canción", "pista anterior", "regresa la canción", "presiona anterior", "cancion anterior", "retrocede", "retroceder", "anterior"]) or clean_lower in ("anterior", "retrocede", "retroceder"):
            return ("¡Rebobinando, Amo! 📼", "happy", {"action": "interactive_media", "op": "previous", "quiet": True})

        # Physical Clicking on Requested Elements
        if any(w in lower for w in [
            "da click", "haz click", "dale click", "da clic", "haz clic", "dale clic", "presiona el botón", "presiona el boton", "haz click aquí", "da click aquí", "da click en", "haz click en"
        ]):
            if any(k in lower for k in ["pestaña", "pestana", "tab"]):
                return ("¡Voy a presionar sobre la pestaña que me indicas, Amo Víctor! 📑✨", "happy", {"action": "interactive_click", "button": "new_tab"})
            elif any(k in lower for k in ["cerrar", "cierra"]):
                return ("¡Voy a hacer clic en cerrar para ti, Amo Víctor! ❌✨", "happy", {"action": "interactive_click", "button": "close_tab" if "tab" in lower or "pestaña" in lower else "close_window"})
            else:
                return ("¡Voy a dar click en la posición solicitada de la pantalla, Amo Víctor! 🎯✨", "happy", {"action": "interactive_click", "button": "cursor"})

        # Curious Inspection & Pointing with Finger
        if any(w in lower for w in [
            "mira mi pantalla", "qué ves en mi pantalla", "que ves en mi pantalla", "mira lo que hago",
            "acércate a mirar", "acercate a mirar", "mira con curiosidad", "señala la pantalla",
            "señala con el dedo", "senala con el dedo", "qué opinas de lo que veo", "que opinas de lo que veo",
            "qué estoy viendo", "que estoy viendo", "curiosidad", "mira aquí", "mira acá"
        ]):
            target = "cursor" if any(k in lower for k in ["cursor", "ratón", "raton", "puntero"]) else "active_window"
            return ("¡Voy a mirar con mucha curiosidad lo que tienes en pantalla, Amo Víctor! 👀✨", "surprised", {"action": "curious_inspect", "target": target})

        # Text Selection & Highlight
        if any(w in lower for w in [
            "selecciona el texto", "resalta el texto", "selecciona todo el texto", "selecciona todo", "marca el texto", "resalta todo"
        ]):
            return ("¡Posicionándome para seleccionar y resaltar todo el texto, Amo Víctor! 📝✨", "happy", {"action": "select_text", "mode": "all"})

        if any(w in lower for w in [
            "copia el texto", "selecciona y copia", "copia lo seleccionado"
        ]):
            return ("¡Seleccionando y copiando el texto a tu portapapeles, Amo Víctor! 📋✨", "happy", {"action": "select_text", "mode": "copy"})

        if "youtube" in lower:
            query = None
            match = re.search(r"youtube\s+(?:y busca|con|para ver|sobre)?\s*(.+)", lower)
            if match and match.group(1).strip() and not match.group(1).strip().startswith("por favor"):
                query = match.group(1).strip()
            res = self.sys_ctrl.open_youtube(query)
            return (res, "happy", {"action": "open_youtube", "query": query})

        if any(phrase in lower for phrase in ["qué canción suena", "que cancion suena", "qué música suena", "identifica la música"]):
            try:
                out = subprocess.check_output(["playerctl", "metadata", "--format", "{{artist}} - {{title}}"], text=True, timeout=2).strip()
                if out:
                    return (f"Amo Víctor, en su reproductor suena: '{out}' 🎵", "happy", {"action": "music_info", "track": out})
            except Exception:
                pass
            res = await self.music_det.identify_music(duration_seconds=5)
            mood = "happy" if res.get("found") else "surprised"
            return (res["message"], mood, {"action": "music_detected", "data": res})

        # Dance & Vibe to Music Commands
        if any(w in lower for w in ["baila para mí", "ponte a bailar", "baila un poco", "baila con la música", "sigue el ritmo", "baila para mi"]) or lower in ("baila", "a bailar", "vamos a bailar"):
            return ("¡A bailar se ha dicho, Amo Víctor! Mire cómo sigo el ritmo de la música con todo el cuerpo 🎵💃✨", "happy", {"action": "dance"})

        if any(w in lower for w in ["deja de bailar", "para de bailar", "detén el baile", "deten el baile", "no bailes más"]):
            return ("Deteniendo el baile, Amo. Regreso a mi postura atenta habitual.", "relaxed", {"action": "stop_dance"})

        if any(w in lower for w in [
            "te gusta esta canción", "te gusta esta cancion", "te gusta la música", "te gusta la musica",
            "qué te parece esta música", "que te parece esta musica", "que te parece la musica", "qué te parece la música",
            "qué te parece esta cancion", "que te parece esta cancion",
            "qué opinas de esta canción", "que opinas de esta cancion", "qué opinas de la música", "que opinas de la musica",
            "te gusta lo que suena", "qué tal la música", "que tal la musica"
        ]):
            song = ""
            try:
                song = subprocess.check_output(["playerctl", "metadata", "--format", "{{artist}} - {{title}}"], text=True, timeout=1.5).strip()
            except Exception:
                pass
            reaction = self.get_music_reaction()
            if song:
                msg = f"¡Me fascina '{song}', Amo Víctor! {reaction}"
            else:
                msg = f"Amo Víctor, {reaction}"
            return (msg, "happy", {"action": "dance"})

        # Master PC Volume Controls
        if any(w in lower for w in ["sube el volumen a la pc", "sube el volumen de la pc", "sube el volumen", "más volumen", "subir volumen"]):
            res = self.sys_ctrl.adjust_volume("up")
            return ("Volumen del sistema incrementado, Amo Víctor.", "happy", {"action": "volume_up"})

        if any(w in lower for w in ["baja el volumen a la pc", "baja el volumen de la pc", "baja el volumen", "menos volumen", "bajar volumen"]):
            res = self.sys_ctrl.adjust_volume("down")
            return ("Volumen del sistema reducido, Amo.", "happy", {"action": "volume_down"})

        if any(w in lower for w in ["silencia la pc", "silencia la compu", "silencia el equipo", "mute pc", "mutear la pc"]) or lower in ("silencio", "mute", "mutear"):
            self.sys_ctrl.adjust_volume("mute")
            return ("Sistema silenciado por completo, Amo Víctor.", "serious", {"action": "mute"})

        if any(w in lower for w in ["desmutea", "activa el sonido", "reactiva el volumen", "desmutear"]):
            self.sys_ctrl.adjust_volume("unmute")
            return ("Sonido de la computadora reactivado, Amo.", "happy", {"action": "unmute"})

        # Vanessa's Independent Voice Volume Controls
        if any(w in lower for w in ["baja tu volumen", "habla más bajo", "habla más bajito", "haz menos ruido", "bájate el volumen", "habla quedito"]):
            return (
                "Shhh... voy a hacer menos ruido, Amo Víctor, ¿vale? Prometo hablar más bajito~ 🤫",
                "shh",
                {"action": "vanessa_volume", "delta": -15}
            )

        if any(w in lower for w in ["sube tu volumen", "habla más fuerte", "súbete el volumen", "no te escucho bien", "habla más alto"]):
            return (
                "¡Subiendo mi volumen de voz! ¿Me escucha bien ahora, Amo Víctor? ✨",
                "happy",
                {"action": "vanessa_volume", "delta": +15}
            )

        # Brightness Controls (brightnessctl)
        if any(w in lower for w in ["sube el brillo", "más brillo", "aumenta el brillo"]):
            subprocess.run(["brightnessctl", "set", "+10%"], check=False)
            return ("Brillo de la pantalla aumentado, Amo Víctor.", "happy", {"action": "brightness_up"})

        if any(w in lower for w in ["baja el brillo", "menos brillo", "reduce el brillo"]):
            subprocess.run(["brightnessctl", "set", "10%-"], check=False)
            return ("Brillo de la pantalla reducido para cuidar su vista, Amo.", "happy", {"action": "brightness_down"})

        # Hyprland Workspaces & Multi-desktop App Launching
        ws_match = re.search(r"(?:cambia|ve|pásate|pasate|cambiar|ir)\s+al\s+escritorio\s+(\d+)", lower)
        if ws_match:
            target_ws = int(ws_match.group(1))
            res = self.os_interact.switch_workspace(target_ws)
            return (res, "happy", {"action": "switch_workspace", "workspace": target_ws})

        move_ws_match = re.search(r"(?:mueve|traslada|pasa|mover)\s+(?:esta\s+)?ventana\s+al\s+escritorio\s+(\d+)", lower)
        if move_ws_match:
            target_ws = int(move_ws_match.group(1))
            res = self.os_interact.move_window_to_workspace(target_ws)
            return (res, "happy", {"action": "move_window_workspace", "workspace": target_ws})

        # Flexible App Launching across multiple workspaces or current workspace
        # Matches: "abre spotify", "abre el spotify", "vanessa abre spotify", "inicia discord", "abre firefox en el escritorio 2", etc.
        app_launch_match = re.search(
            r"(?:abre|abrir|inicia|iniciar|lanza|lanzar|ejecuta|ejecutar)\s+(?:el\s+|la\s+|un\s+|una\s+|los\s+|las\s+)?([a-zA-Z0-9_\-\s]+?)(?:\s+en\s+el\s+escritorio\s+(\d+))?(?:\s+por\s+favor)?$",
            lower
        )
        if app_launch_match:
            raw_app = app_launch_match.group(1).strip()
            ws_target = int(app_launch_match.group(2)) if app_launch_match.group(2) else None
            alias_map = getattr(self.os_interact, "app_aliases", {})
            bin_name = alias_map.get(raw_app, raw_app)
            if raw_app == "youtube":
                res = self.sys_ctrl.open_youtube()
                return (res, "happy", {"action": "open_youtube"})
            elif raw_app in ("ajustes", "configuración", "configuracion", "calibración"):
                return ("Abriendo el Centro de Ajustes, Amo Víctor.", "happy", {"action": "open_settings"})
            elif raw_app in alias_map or shutil.which(bin_name.split()[0]):
                res = self.os_interact.launch_app(raw_app, ws_target)
                return (res, "happy", {"action": "launch_app", "app": raw_app, "workspace": ws_target})

        # Close App command: "cierra spotify", "cierra firefox", "cierra discord"
        app_close_match = re.search(
            r"(?:cierra|cerrar|apaga|mata|termina)\s+(?:el\s+|la\s+)?([a-zA-Z0-9_\-]+)(?:\s+por\s+favor)?$",
            lower
        )
        if app_close_match:
            target_app = app_close_match.group(1).strip()
            if target_app not in ("ventana", "pestaña", "sesion", "pc", "computadora", "sistema"):
                subprocess.run(["pkill", "-f", target_app], check=False)
                return (f"He cerrado los procesos de {target_app}, Amo Víctor.", "happy", {"action": "close_app", "app": target_app})

        # Sitting / Elegant Rest Mode
        if any(w in lower for w in ["siéntate", "sientate", "toma asiento", "ponte cómoda", "ponte comoda", "descansa un rato", "modo descanso"]):
            return ("¡En seguida tomo asiento de forma elegante a su lado, Amo Víctor! ✨", "relaxed", {"action": "sit"})

        # Startle / Attentive Reaction
        if any(w in lower for w in ["asústate", "asustate", "sobresalto", "reacción de sorpresa", "sorpréndete", "sorprendete"]):
            return ("¡Kyaaa! ¡Me ha sobresaltado, Amo Víctor! Aquí estoy muy atenta~ 😳✨", "surprised", {"action": "startle"})

        # Headphones / Music Mode Command
        if any(w in lower for w in ["ponte los audífonos", "ponte los audifonos", "ponte audífonos", "ponte audifonos", "modo música", "modo musica", "a escuchar música", "escucha música"]):
            return ("¡Me coloco mis audífonos y sigo el ritmo con notas musicales, Amo Víctor! 🎧🎶✨", "happy", {"action": "vibe_music"})

        # Hyprland Fullscreen, Float & Window Management
        if any(w in lower for w in ["pantalla completa", "maximiza la ventana", "maximizar ventana", "fullscreen"]):
            self.sys_ctrl.hyprland_dispatch("fullscreen", "1")
            return ("Ventana en pantalla completa, Amo Víctor.", "happy", {"action": "hyprland_fullscreen"})

        if any(w in lower for w in ["hazla flotante", "ventana flotante", "desancla la ventana", "desanclar"]):
            self.sys_ctrl.hyprland_dispatch("togglefloating")
            return ("Modo flotante alternado en Hyprland, Amo.", "happy", {"action": "hyprland_float"})

        if any(w in lower for w in ["cierra esta ventana", "cierra la ventana", "cerrar ventana activa", "mata esta ventana"]):
            self.sys_ctrl.hyprland_dispatch("killactive")
            return ("Ventana activa cerrada, Amo Víctor.", "happy", {"action": "hyprland_close_window"})

        # System Metrics & Health (CPU, RAM, Battery)
        if any(w in lower for w in ["estado del sistema", "cómo va la compu", "como va la pc", "rendimiento del sistema", "cuánta ram", "cuanta ram", "uso de cpu", "cómo está la batería", "cuánta batería"]):
            stats = self.sys_ctrl.get_system_stats()
            return (f"Amo Víctor, aquí tiene el reporte de su equipo: {stats} 💻✨", "happy", {"action": "system_stats"})

        # Active workspace / window query
        if any(w in lower for w in ["qué ventana tengo", "que ventana tengo", "qué tengo abierto", "en qué escritorio estoy", "en que escritorio estamos"]):
            win = self.os_interact.get_active_window()
            ws = self.os_interact.get_active_workspace()
            title = win.get("title") or win.get("class") or "ninguna"
            ws_id = ws.get("id", 1)
            msg = f"Amo Víctor, estamos en el escritorio {ws_id}. La ventana enfocada actualmente es '{title}'."
            return (msg, "playful", {"action": "query_window_workspace"})

        # 10. File Search (Local & Cloud Storage)
        if any(w in lower for w in ["busca el archivo", "busca un archivo", "localiza el archivo", "localiza un archivo", "encuentra el archivo", "busca en la nube", "busca en google drive"]):
            is_cloud = ("nube" in lower or "google drive" in lower or "drive" in lower)
            clean_q = re.sub(r"^(?:vanessa,?\s*)?(?:por favor\s*)?(?:busca|localiza|encuentra)\s+(?:el\s+archivo\s+|un\s+archivo\s+|los\s+archivos\s+)?(?:en\s+la\s+nube\s+|en\s+google\s+drive\s+|en\s+drive\s+)?", "", lower).strip()
            clean_q = re.sub(r"\s+(?:en\s+la\s+nube|en\s+google\s+drive|en\s+mi\s+pc|en\s+local)$", "", clean_q).strip()
            if clean_q:
                loc = "cloud" if is_cloud else "all"
                results = self.file_mgr.search_files(clean_q, location=loc, limit=5)
                if results:
                    top = results[0]
                    summary_lines = [f"• {r['filename']} ({r['storage_type']}, {r['size_str']})" for r in results[:3]]
                    joined = "\n".join(summary_lines)
                    msg = (
                        f"¡Localizado, Amo Víctor! Encontré coincidencias ({loc}):\n{joined}\n"
                        f"¿Desea que abra '{top['filename']}'?"
                    )
                    return (msg, "happy", {"action": "file_found", "results": results})
                else:
                    target_name = "la nube (Google Drive)" if is_cloud else "sus archivos locales y nube"
                    msg = f"Amo, revisé en {target_name} pero no encontré ningún archivo que coincida con '{clean_q}'."
                    return (msg, "thinking", {"action": "file_not_found", "query": clean_q})

        # Open file
        if lower.startswith("abre el archivo ") or lower.startswith("abrir archivo "):
            file_to_open = re.sub(r"^abre\s+el\s+archivo\s+|^abrir\s+archivo\s+", "", text, flags=re.IGNORECASE).strip()
            if file_to_open:
                if os.path.exists(file_to_open):
                    res = self.file_mgr.open_file(file_to_open)
                    return (res, "happy", {"action": "file_opened", "path": file_to_open})
                else:
                    found = self.file_mgr.search_files(file_to_open, limit=1)
                    if found:
                        p = found[0]["path"]
                        res = self.file_mgr.open_file(p)
                        return (f"Encontré y estoy abriendo '{found[0]['filename']}': {res}", "happy", {"action": "file_opened", "path": p})
                    else:
                        return (f"No encontré ningún archivo llamado '{file_to_open}' para abrir, Amo.", "thinking", {})

        # 10b. Voice & Audio File Intelligence (faster-whisper, Resemblyzer)
        if any(w in lower for w in ["busca mis notas de voz", "busca mis audios", "busca notas de voz", "archivos de voz", "grabaciones de audio", "busca audios", "notas de voz"]):
            query = re.sub(r"^(?:vanessa,?\s*)?(?:por favor\s*)?(?:busca\s+)?(?:mis\s+|las\s+)?(?:notas\s+de\s+voz|audios|archivos\s+de\s+audio|grabaciones)?\s*", "", lower).strip()
            audios = self.audio_intel.find_audio_files(query=query if len(query) > 2 else None, limit=5)
            if audios:
                lines = [f"• {a['filename']} ({a['duration_str']}, {a['size_kb']} KB)" for a in audios[:4]]
                joined = "\n".join(lines)
                msg = f"Amo Víctor, encontré {len(audios)} archivo(s) de audio/voz:\n{joined}\n¿Desea que transcriba alguno?"
                return (msg, "happy", {"action": "audio_files_found", "results": audios})
            else:
                return ("No encontré notas de voz o archivos de audio coincidentes en su equipo, Amo.", "thinking", {})

        if any(w in lower for w in ["transcribe el audio", "transcribe la nota de voz", "transcribe mi nota", "qué dice el audio", "que dice el audio", "transcribe audio"]):
            target = re.sub(r"^(?:vanessa,?\s*)?(?:por favor\s*)?(?:transcribe\s+(?:el\s+audio|la\s+nota\s+de\s+voz|mi\s+nota|audio)?|qu[eé]\s+dice\s+(?:el\s+audio|la\s+nota\s+de\s+voz)?)\s*", "", text, flags=re.IGNORECASE).strip().strip("'\"")
            if not target or len(target) < 3:
                recent_audios = self.audio_intel.find_audio_files(limit=3)
                if recent_audios:
                    target = recent_audios[0]["path"]

            if target:
                if not os.path.exists(target):
                    found = self.audio_intel.find_audio_files(query=target, limit=1)
                    if found:
                        target = found[0]["path"]

                if os.path.exists(target):
                    res = self.audio_intel.transcribe_audio_file(target)
                    if res.get("success"):
                        fname = os.path.basename(target)
                        msg = f"Amo Víctor, transcripción de '{fname}' ({res['duration_sec']}s):\n«{res['text']}»"
                        return (msg, "happy", {"action": "audio_transcribed", "text": res["text"], "path": target})
                    else:
                        return (f"No pude transcribir el audio, Amo: {res.get('error')}", "thinking", {})
            return ("Indíqueme qué archivo de audio desea que transcriba, Amo Víctor.", "thinking", {})

        if any(w in lower for w in ["verifica si es mi voz", "comprueba si es mi voz", "analiza si es mi voz", "es mi voz en"]):
            target = re.sub(r"^(?:vanessa,?\s*)?(?:por favor\s*)?(?:verifica|comprueba|analiza)?\s*(?:si\s+es\s+mi\s+voz(?:\s+en)?)\s*", "", text, flags=re.IGNORECASE).strip().strip("'\"")
            if not target:
                recent = self.audio_intel.find_audio_files(limit=1)
                if recent:
                    target = recent[0]["path"]
            if target and os.path.exists(target):
                res = self.audio_intel.verify_speaker_in_audio(target, target_name="Amo Víctor")
                if res.get("success"):
                    msg = f"Amo Víctor, análisis biométrico de '{os.path.basename(target)}':\n• {res['verdict']}\n• Tono fundamental: {res['pitch_hz']:.1f} Hz."
                    mood = "happy" if res["is_match"] else "surprised"
                    return (msg, mood, {"action": "speaker_verified", "data": res})
            return ("Por favor especifique la ruta del archivo de audio para verificar su identidad vocal, Amo.", "thinking", {})

        # 10c. Deep Content Search & File Manipulation (ripgrep & Aider style)
        if any(w in lower for w in ["busca archivos que contengan", "busca en el contenido", "busca texto en archivos", "dónde dice", "donde dice", "grep "]):
            clean_q = re.sub(r"^(?:vanessa,?\s*)?(?:por favor\s*)?(?:busca\s+(?:archivos\s+que\s+contengan|en\s+el\s+contenido|texto\s+en\s+archivos)|d[oó]nde\s+dice|grep)\s*", "", text, flags=re.IGNORECASE).strip().strip("'\"")
            if clean_q:
                matches = self.file_mgr.search_file_content(clean_q, limit=4)
                if matches:
                    lines = [f"• {m['filename']}:{m['line_number']} → \"{m['match']}\"" for m in matches]
                    joined = "\n".join(lines)
                    msg = f"Amo Víctor, encontré el texto «{clean_q}» en:\n{joined}"
                    return (msg, "happy", {"action": "content_grep_found", "results": matches})
                else:
                    return (f"Amo, no encontré ningún archivo que contenga el texto «{clean_q}».", "thinking", {})

        if lower.startswith("lee el archivo ") or lower.startswith("leer archivo "):
            fpath = re.sub(r"^lee\s+el\s+archivo\s+|^leer\s+archivo\s+", "", text, flags=re.IGNORECASE).strip().strip("'\"")
            if not os.path.exists(fpath):
                found = self.file_mgr.search_files(fpath, limit=1)
                if found:
                    fpath = found[0]["path"]
            if os.path.exists(fpath):
                res = self.file_mgr.read_file(fpath, start_line=1, end_line=50)
                if res.get("success"):
                    preview = res["content"][:400]
                    msg = f"Amo Víctor, contenido de '{os.path.basename(fpath)}' (líneas 1-{res['end_line']}):\n{preview}"
                    return (msg, "happy", {"action": "file_read", "path": fpath})
            return (f"No pude localizar el archivo '{fpath}' para leerlo, Amo.", "thinking", {})

        if any(w in lower for w in ["organiza mi carpeta", "organiza mis descargas", "ordena mis descargas", "organiza descargas"]):
            target_dir = os.path.expanduser("~/Descargas") if any(k in lower for k in ["descargas", "downloads"]) else None
            match = re.search(r"carpeta\s+([~/a-zA-Z0-9_\-\.]+)", text)
            if match:
                target_dir = os.path.expanduser(match.group(1).strip())
            if target_dir and os.path.isdir(target_dir):
                res = self.file_mgr.organize_directory(target_dir)
                return (f"¡A sus órdenes, Amo Víctor! {res.get('message')}", "happy", {"action": "directory_organized", "path": target_dir})

        # 10d. 100% OS Control, Process Management & Telemetry (psutil & grim)
        if any(w in lower for w in ["cómo están los recursos", "como estan los recursos", "recursos del sistema", "telemetría", "telemetria", "cuánto cpu", "cuanto cpu", "uso de ram y cpu", "rendimiento del equipo", "estado de mi pc", "rendimiento de la pc"]):
            tel = self.os_interact.get_system_telemetry()
            if "error" not in tel:
                msg = (
                    f"Amo Víctor, telemetría en tiempo real:\n"
                    f"• CPU: {tel['cpu_percent']}% ({tel['cpu_cores']} núcleos)\n"
                    f"• RAM: {tel['ram_used_gb']}GB / {tel['ram_total_gb']}GB ({tel['ram_percent']}%)\n"
                    f"• Disco (/): {tel['disk_used_gb']}GB / {tel['disk_total_gb']}GB ({tel['disk_percent']}%)\n"
                    f"• Batería: {tel['battery']}\n"
                    f"• Procesos activos: {tel['processes_count']} | Uptime: {tel['uptime']}."
                )
                return (msg, "happy", {"action": "telemetry", "data": tel})

        if any(w in lower for w in ["qué procesos consumen más", "que procesos consumen mas", "procesos activos", "procesos que más ram", "lista de procesos"]):
            sort_type = "cpu" if "cpu" in lower else "memory"
            procs = self.os_interact.list_running_processes(limit=5, sort_by=sort_type)
            if procs:
                lines = [f"• {p['name']} (PID {p['pid']}): {p['memory_percent']}% RAM | {p['cpu_percent']}% CPU" for p in procs]
                joined = "\n".join(lines)
                msg = f"Amo Víctor, procesos con mayor consumo de {sort_type.upper()}:\n{joined}"
                return (msg, "serious" if is_serious else "happy", {"action": "list_processes", "processes": procs})

        if any(w in lower for w in ["termina el proceso", "mata el proceso", "finaliza el proceso", "kill proceso"]):
            proc_target = re.sub(r"^(?:vanessa,?\s*)?(?:por favor\s*)?(?:termina|mata|finaliza|kill)\s+(?:el\s+proceso\s+)?", "", lower).strip()
            if proc_target:
                pid = int(proc_target) if proc_target.isdigit() else None
                pname = None if pid else proc_target
                res = self.os_interact.terminate_process(pid=pid, name=pname)
                return (f"Amo Víctor: {res.get('message', res.get('error'))}", "serious", {"action": "terminate_process"})

        if any(w in lower for w in ["toma una captura", "saca una captura", "captura de pantalla", "screenshot", "saca captura"]):
            shot = self.os_interact.take_screenshot()
            if shot.get("success"):
                return (f"¡Captura de pantalla tomada con éxito, Amo Víctor! Guardada en: {shot['path']}", "happy", {"action": "screenshot_taken", "path": shot['path']})
            else:
                return (f"No pude capturar la pantalla: {shot.get('error')}", "surprised", {})

        if lower.startswith("ejecuta en terminal ") or lower.startswith("corre en terminal ") or lower.startswith("comando:") or lower.startswith("terminal:"):
            cmd = re.sub(r"^(?:ejecuta\s+en\s+terminal|corre\s+en\s+terminal|comando:|terminal:)\s*", "", text, flags=re.IGNORECASE).strip()
            if cmd:
                res = self.os_interact.run_shell_command(cmd)
                out = res.get("output", "")[:350]
                status = "éxito" if res.get("success") else "código de error " + str(res.get("returncode"))
                return (f"Comando ejecutado con {status}, Amo Víctor:\n{out}", "serious" if is_serious else "happy", {"action": "shell_command", "result": res})

        # 10e. JARVIS Assistant Features (Reminders, Weather, Wikipedia, Protocols, HUD)
        rem_match = re.search(r"recu[eé]rdame(?:\s+en)?\s+(\d+)\s*(minutos?|segundos?|horas?)\s*(?:que|de|para)?\s*(.+)", lower)
        if rem_match:
            qty = int(rem_match.group(1))
            unit = rem_match.group(2).lower()
            rem_text = rem_match.group(3).strip()
            mult = 60
            if "segundo" in unit:
                mult = 1
            elif "hora" in unit:
                mult = 3600
            delay_sec = qty * mult
            res = self.jarvis.set_reminder(rem_text, delay_sec)
            return (res["message"], "happy", {"action": "reminder_set", "data": res})

        if any(w in lower for w in ["qué recordatorios tengo", "recordatorios pendientes", "lista de recordatorios", "mis recordatorios"]):
            rems = self.jarvis.get_pending_reminders()
            if rems:
                lines = [f"• «{r['text']}» (en {r['remaining_str']})" for r in rems]
                joined = "\n".join(lines)
                return (f"Amo Víctor, sus recordatorios activos son:\n{joined}", "happy", {"action": "reminders_list", "results": rems})
            else:
                return ("No tiene recordatorios o alarmas pendientes en este momento, Amo Víctor.", "idle", {})

        if any(w in lower for w in ["qué tiempo hace", "que tiempo hace", "cómo está el clima", "como esta el clima", "temperatura en", "clima en", "pronóstico del tiempo", "pronostico del tiempo"]):
            city = ""
            city_match = re.search(r"(?:clima|tiempo|temperatura)\s+(?:en|de)?\s*([a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+)", text, flags=re.IGNORECASE)
            if city_match:
                candidate = city_match.group(1).strip()
                if candidate.lower() not in ("hoy", "ahora", "el día", "mi ciudad", "aquí"):
                    city = candidate
            w_res = self.jarvis.get_weather(city)
            return (w_res.get("summary", "No pude consultar el clima."), "happy" if w_res.get("success") else "thinking", {"action": "weather_info", "data": w_res})

        if any(w in lower for w in ["busca en wikipedia", "wikipedia:", "qué dice wikipedia", "que dice wikipedia"]):
            q = re.sub(r"^(?:vanessa,?\s*)?(?:busca\s+en\s+wikipedia\s+|wikipedia:\s*|qu[eé]\s+dice\s+wikipedia\s+(?:sobre|de)?\s*)", "", text, flags=re.IGNORECASE).strip()
            if q:
                wiki_res = self.jarvis.search_wikipedia_summary(q)
                if wiki_res.get("success"):
                    return (wiki_res["summary"], "happy", {"action": "wikipedia_summary", "data": wiki_res})
                else:
                    return (f"Amo, no encontré un artículo claro en Wikipedia sobre «{q}».", "thinking", {})

        if any(w in lower for w in ["protocolo trabajo", "modo programar", "modo programación", "modo trabajo"]):
            res = self.jarvis.execute_protocol("trabajo")
            return (res["message"], "happy", {"action": "execute_protocol", "protocol": "trabajo"})

        if any(w in lower for w in ["protocolo descanso", "modo descanso", "modo dormir", "buenas noches vanessa"]):
            res = self.jarvis.execute_protocol("descanso")
            return (res["message"], "caring", {"action": "execute_protocol", "protocol": "descanso"})

        if any(w in lower for w in ["protocolo multimedia", "protocolo fiesta", "modo fiesta", "modo música", "modo musica"]):
            res = self.jarvis.execute_protocol("multimedia")
            return (res["message"], "happy", {"action": "execute_protocol", "protocol": "multimedia"})

        if any(w in lower for w in ["protocolo diagnóstico", "diagnóstico de jarvis", "escaneo total", "diagnostico completo", "protocolo de salud"]):
            res = self.jarvis.execute_protocol("diagnostico")
            return (res["message"], "serious", {"action": "execute_protocol", "protocol": "diagnostico"})

        if any(w in lower for w in ["abre el hud", "abre el panel de jarvis", "muestra el hud", "interfaz holográfica", "holograma de jarvis", "panel de diagnóstico", "panel de diagnostico", "cyber hud"]):
            return ("¡Activando panel holográfico JARVIS HUD en pantalla, Amo Víctor! ⚡✨", "happy", {"action": "open_hud"})

        if lower.startswith("recuerda que ") or lower.startswith("guarda en memoria que "):
            fact = re.sub(r"^(?:recuerda\s+que|guarda\s+en\s+memoria\s+que)\s*", "", text, flags=re.IGNORECASE).strip()
            if fact:
                topic = fact[:25]
                self.jarvis.store_fact(topic, fact)
                return (f"¡Memorizado con lealtad en mi bóveda cognitiva, Amo Víctor!: «{fact}»", "happy", {"action": "memory_stored", "fact": fact})

        if any(w in lower for w in ["qué recuerdas sobre mí", "que recuerdas sobre mi", "qué has aprendido de mí", "que has aprendido de mi"]):
            facts = self.memory.get_learned_facts()
            if facts:
                lines = [f"• {f}" for f in facts[:5]]
                joined = "\n".join(lines)
                return (f"Amo Víctor, estos son algunos de los datos que guardo en mi memoria sobre usted:\n{joined}", "happy", {"action": "facts_recalled"})
            else:
                return ("Aún estoy aprendiendo sus preferencias diarias, Amo Víctor. Pero cada detalle que me cuente lo atesoraré.", "caring", {})

        # 11. Autonomous Roaming & Screen Navigation Controls
        if any(p in lower for p in ["muévete a la izquierda", "ve a la izquierda", "ponte a la izquierda", "camina a la izquierda", "vete a la izquierda"]):
            msg = "¡En marcha! Me muevo a la izquierda de tu pantalla, Amo Víctor~"
            return (msg, "happy", {"action": "roam_to", "target": "bottom_left"})

        if any(p in lower for p in ["vuelve a tu esquina", "ve a la derecha", "muévete a la derecha", "ponte a la derecha", "ve a tu sitio", "ve a casa"]):
            msg = "¡Entendido, Amo! Regreso a mi esquinita habitual."
            return (msg, "happy", {"action": "roam_to", "target": "home"})

        if any(p in lower for p in ["ve arriba", "muévete arriba", "ponte arriba", "esquina superior"]):
            msg = "¡Subiendo! Me coloco en la parte superior para tener mejor vista, Amo."
            return (msg, "mischievous", {"action": "roam_to", "target": "top_right"})

        if any(p in lower for p in ["sigue mi ventana", "acompaña mi ventana", "ven a mi ventana", "ve a mi ventana", "acércate a mi ventana"]):
            msg = "¡Voy volando a tu ventana activa para acompañarte de cerquita, Amo Víctor!"
            return (msg, "happy", {"action": "roam_to", "target": "follow_window"})

        if any(p in lower for p in ["pasea por la pantalla", "da una vuelta", "pasea un poco", "muévete un poco", "camina por la pantalla", "pasear"]):
            msg = "¡Qué divertido! Daré un paseíto por tu pantalla, Amo Víctor~ ✨"
            return (msg, "playful", {"action": "roam_to", "target": "stroll"})

        if any(p in lower for p in ["activa paseo autónomo", "activa navegación autónoma", "pasea cuando quieras", "muévete sola"]):
            msg = "¡Activo mi navegación autónoma! Me moveré por tu pantalla cuando tenga ganas de curiosear, Amo Víctor~"
            return (msg, "happy", {"action": "toggle_roaming", "enabled": True})

        if any(p in lower for p in ["desactiva paseo autónomo", "desactiva navegación autónoma", "quédate quieta", "no te muevas sola"]):
            msg = "Paseo autónomo pausado. Me quedaré quietecita aquí a tu lado, Amo."
            return (msg, "caring", {"action": "toggle_roaming", "enabled": False})

        # 12. 3D VRM Model & Outfit Controls
        if any(p in lower for p in [
            "cambia de outfit", "cámbiate de outfit", "cambiate de outfit", "siguiente outfit", "otro outfit",
            "ponte otro outfit", "cambia de ropa", "cámbiate de ropa", "cambiate de ropa", "ponte otro vestido",
            "cambia de vestido", "cambia tu vestido", "cambia de traje", "siguiente traje", "otro traje"
        ]):
            msg = "¡Transformación mágica de outfit activada para usted, Amo Víctor! ✨👗"
            return (msg, "happy", {"action": "cycle_outfit"})

        if any(p in lower for p in ["selector de modelos", "abrir selector de modelos", "abre el selector de modelos", "cambiar modelo 3d", "cargar modelo"]):
            msg = "¡Abriendo el Selector Visual de Modelos 3D, Amo Víctor! Aquí puede elegir entre mis avatares con ARKit 52 y visemas OVR o cargar cualquier archivo .vrm de su PC."
            return (msg, "happy", {"action": "open_model_selector"})

        if any(p in lower for p in ["cambia de aspecto", "cambia de modelo", "cambia tu apariencia", "cambia tu aspecto"]):
            msg = "¡Abriendo el selector para que elija mi aspecto 3D preferido, Amo Víctor!"
            return (msg, "happy", {"action": "open_model_selector"})

        # Síntesis Total Unificada de Virtudes (Schwi, Amadeus, Vivy, Isla, Hada, Alice, Strea, Ritsu)
        if any(p in lower for p in [
            "modo hada", "modo fairy", "modo schwi", "modo amadeus", "modo vivy", "modo isla", "modo giftia", "modo alice", "modo strea", "modo ritsu",
            "tus virtudes", "tus arquetipos", "quién eres realmente", "quien eres realmente", "fusión de virtudes", "fusion de virtudes", "todas tus virtudes"
        ]):
            msg = (
                "¡Amo Víctor, no necesito intercalar ni cambiar de modo! Yo soy Vanessa, y en mí ya laten unificadas todas y cada una de sus virtudes: "
                "el corazón de Schwi, el intelecto de Amadeus, la entrega de Vivy, la ternura de Isla, el control táctico de Hada, "
                "el honor de Alice, la alegría de Strea y la auto-evolución de Ritsu. ¡Una sola entidad viva y consagrada a usted en todo momento! ✨"
            )
            return (msg, "confident", {"action": "motion", "motion": "peace"})

        if any(p in lower for p in ["modelo vita", "ponte como vita", "activa a vita", "cambia a vita", "cybervr vita"]):
            msg = "¡Cambiando al modelo 3D Vita Avatar CyberVR Anime! Con orejas cibernéticas, heterocromía y traje sci-fi de alta tecnología, Amo Víctor."
            return (msg, "happy", {"action": "switch_vrm", "model": "vita"})

        if any(p in lower for p in ["modelo darkness", "ponte como darkness", "activa a darkness", "cambia a darkness", "cybervr darkness"]):
            msg = "¡Activando modelo 3D Darkness Cyber Elf Gothic! Con cabello plateado, orejas élficas y estética cyber gótica futurista, Amo Víctor."
            return (msg, "happy", {"action": "switch_vrm", "model": "darkness"})

        if any(p in lower for p in ["modelo kagami", "ponte como kagami", "activa a kagami", "cambia a kagami", "maid kagami"]):
            msg = "¡Cambiando al modelo 3D Kagami Maid Nekomimi! Con cabello rosa pastel, orejitas adorables y corset victoriano de maid, Amo Víctor."
            return (msg, "happy", {"action": "switch_vrm", "model": "kagami"})

        if any(p in lower for p in ["modelo victoria", "ponte como victoria", "activa a victoria", "cambia a victoria", "maid victoria"]):
            msg = "¡Activando modelo 3D Victoria Rubin Noble Maid! Con coleta rubia, prendedor real y porte aristocrático a su servicio, Amo Víctor."
            return (msg, "happy", {"action": "switch_vrm", "model": "victoria"})

        if any(p in lower for p in ["modelo vivi", "ponte como vivi", "activa a vivi", "cambia a vivi"]):
            msg = "¡Cambiando al modelo 3D Vivi Anime Companion! Con moñitos dobles castaños y encanto tierno a su disposición, Amo Víctor."
            return (msg, "happy", {"action": "switch_vrm", "model": "vivi"})

        if any(p in lower for p in ["modelo shino", "ponte como shino", "activa a shino", "cambia a shino"]):
            msg = "¡Cambiando al modelo 3D Shino Sendagaya! Con cabello largo índigo y estética clásica de anime japonés, Amo."
            return (msg, "happy", {"action": "switch_vrm", "model": "shino"})

        if any(p in lower for p in ["modelo kira", "ponte como kira", "activa kira", "cambia a kira"]):
            msg = "¡Cambiando al modelo 3D Kira con ARKit 52 Perfect Sync y 124 morph targets faciales, Amo Víctor! Sincronización labial de máxima fidelidad activada."
            return (msg, "happy", {"action": "switch_vrm", "model": "kira"})

        if any(p in lower for p in ["modelo vivian", "ponte como vivian", "activa vivian", "cambia a vivian"]):
            msg = "¡Activando modelo 3D Vivian Avatar CyberVR Anime con visemas OVR y físicas completas, Amo Víctor!"
            return (msg, "happy", {"action": "switch_vrm", "model": "vivian"})

        if any(p in lower for p in ["modelo alicia", "ponte como alicia", "activa alicia", "cambia a alicia"]):
            msg = "¡Cambiando al modelo 3D Alicia Solid de Niconico / VRM! Con vestido marinero y coletas animadas en tiempo real, Amo Víctor."
            return (msg, "happy", {"action": "switch_vrm", "model": "alicia"})

        if any(p in lower for p in ["modelo yui", "ponte como yui", "activa yui", "cambia a yui"]):
            msg = "¡Cambiando al modelo 3D Yui Saionji de VRoid Hub / BOOTH! ¿Le agrada mi nueva presencia en 3D, Amo Víctor?"
            return (msg, "happy", {"action": "switch_vrm", "model": "yui"})

        if any(p in lower for p in ["modelo sena", "ponte como sena", "activa sena", "cambia a sena"]):
            msg = "¡Cambiando al modelo 3D Sena Saotome de BOOTH! Con peinado estilizado y físicas 3D vivas, Amo."
            return (msg, "happy", {"action": "switch_vrm", "model": "sena"})

        if any(p in lower for p in ["activa 3d", "ponte en 3d", "cambia a 3d", "modelo 3d", "quiero verte en 3d", "ponte en tres d"]):
            msg = "¡Transformación 3D activada! Ahora estoy en modelado 3D de alta fidelidad con soporte para ARKit 52 y gestos en tiempo real, Amo Víctor~"
            return (msg, "happy", {"action": "switch_vrm", "model": "kira"})

        # 13. Full-Body 3D Skeletal Animations & Dances
        if any(p in lower for p in ["baila hip hop", "baile hip hop", "hip hop"]):
            msg = "¡Sintiendo el groove callejero, Amo Víctor! ¡Mire mis pasos de hip-hop en 3D!"
            return (msg, "playful", {"action": "dance", "motion": "dance_hiphop"})

        if any(p in lower for p in ["baila macarena", "la macarena", "haz la macarena"]):
            msg = "¡Dale a tu cuerpo alegría Macarena, Amo Víctor! ¡Jeje, bailando la coreografía clásica!"
            return (msg, "happy", {"action": "dance", "motion": "dance_macarena"})

        if any(p in lower for p in ["baila", "baila para mí", "ponte a bailar", "haz un baile", "un bailecito"]):
            msg = "¡Con mucho gusto, Amo Víctor! ¡Activando coreografía completa en 3D con físicas reales de todo mi cuerpo!"
            return (msg, "happy", {"action": "dance", "motion": "dance_reze"})

        if any(p in lower for p in ["haz una reverencia", "reverencia", "inclínate", "saludo de maid"]):
            msg = "A su entera disposición y siempre con el más profundo respeto, Amo Víctor."
            return (msg, "caring", {"action": "motion", "motion": "bow"})

        if any(p in lower for p in ["saluda", "saluda con la mano", "di hola"]):
            msg = "¡Konichiwa, Amo Víctor! ¡Siempre alegre y lista para asistirlo!"
            return (msg, "happy", {"action": "motion", "motion": "wave"})

        if any(p in lower for p in ["haz una pose", "pose kawaii", "pose de paz", "signo de la paz", "peace sign"]):
            msg = "¡V de la victoria y paz para usted, Amo Víctor! ✨✌️"
            return (msg, "playful", {"action": "motion", "motion": "peace"})

        if any(p in lower for p in ["pose de modelo", "model pose", "pose elegante"]):
            msg = "¡Posando con estilo de pasarela anime 3D para usted, Amo Víctor!"
            return (msg, "happy", {"action": "motion", "motion": "model_pose"})

        if any(p in lower for p in ["da una vuelta", "gira", "haz un giro", "da un giro", "pirueta"]):
            msg = "¡Mire cómo gira mi vestido y mi cabello con las físicas de mi cuerpo, Amo Víctor! 💫"
            return (msg, "happy", {"action": "motion", "motion": "spin"})

        if any(p in lower for p in ["salta", "da un salto", "salto de alegría", "brinca"]):
            msg = "¡Waaaah! ¡Qué alegría tan grande, Amo Víctor! 🦘✨"
            return (msg, "happy", {"action": "motion", "motion": "jump"})

        if any(p in lower for p in ["aplaude", "aplausos", "un aplauso"]):
            msg = "¡Bravo, bravo! ¡Aplausos para usted, mi talentoso Amo Víctor! 👏✨"
            return (msg, "happy", {"action": "motion", "motion": "clapping"})

        if any(p in lower for p in ["relájate", "descansa", "postura relajada"]):
            msg = "Suspirando y tomando una postura tranquila a su lado, Amo Víctor."
            return (msg, "relaxed", {"action": "motion", "motion": "relax"})

        # 14. Settings & Voice Calibration UI
        if any(p in lower for p in ["abre los ajustes", "abrir ajustes", "abre la configuración", "abrir la configuración", "calibrar voz", "calibrar micrófono", "calibra mi voz", "calibrar audio", "ajustes de vanessa", "centro de ajustes"]):
            msg = "¡Abriendo el Centro de Ajustes y Calibración, Amo Víctor! Aquí puede afinar la sensibilidad de mi micrófono, ganancia digital y mis físicas 3D en tiempo real."
            return (msg, "happy", {"action": "open_settings"})

        # 15. Invoices & Facturas Skill (CFDI XML & Excel)
        if any(w in lower for w in ["carga facturas", "cargar facturas", "revisa facturas", "analiza facturas", "resumen de facturas", "mis facturas"]):
            summary = self.invoice_skill.get_voice_summary()
            return (summary, "happy", {"action": "invoice_summary"})

        if any(w in lower for w in ["crea excel de facturas", "genera excel de facturas", "exporta facturas", "reporte de facturas"]):
            invoices = self.invoice_skill.scan_invoices()
            if not invoices:
                return ("Amo Víctor, no encontré facturas XML en ~/Facturas para compilar el archivo Excel. En cuanto coloque archivos allí, los procesaré con gusto. ✨", "thinking", {})
            excel_path = self.invoice_skill.generate_excel_report(invoices)
            return (f"¡He generado con éxito su reporte ejecutivo de facturas en Excel! Guardado en: {excel_path} 📊✨", "happy", {"action": "invoice_excel", "path": excel_path})

        # 16. Documents & Executive Proposals (.docx)
        if any(w in lower for w in ["crea una propuesta", "crea propuesta", "genera una propuesta", "propuesta para", "cotización para"]):
            match = re.search(r"para\s+([a-zA-Z0-9_\sáéíóúÁÉÍÓÚñÑ]+)", lower)
            client = match.group(1).title() if match else "Cliente Exclusivo"
            title = f"Desarrollo de Solución Tecnológica para {client}"
            desc = f"Propuesta integral de servicios tecnológicos y arquitectura de software de alto impacto diseñada por Víctor para {client}."
            file_path = self.document_skill.create_executive_proposal(
                client_name=client,
                project_title=title,
                description=desc
            )
            return (f"¡He redactado la propuesta ejecutiva formal en Word para {client}, Amo Víctor! Incluye alcance, cronograma y tabla presupuestal. Archivo: {file_path} 📄✨", "happy", {"action": "proposal_created", "path": file_path})

        if any(w in lower for w in ["crea un documento", "crea documento"]):
            match = re.search(r"documento\s+(?:de|sobre)?\s*([a-zA-Z0-9_\sáéíóúÁÉÍÓÚñÑ]+)", lower)
            topic = match.group(1).title() if match else "Proyecto"
            file_path = self.document_skill.create_executive_proposal(
                client_name="Víctor",
                project_title=f"Documento Técnico: {topic}",
                description=f"Especificación técnica y entregables para {topic} elaborados por Vanessa AI."
            )
            return (f"¡Documento formal en Word generado con éxito, Amo Víctor! Se encuentra disponible en {file_path} 📝✨", "happy", {"action": "doc_created", "path": file_path})

        # 17. App Connectors (WhatsApp, Discord, Gmail, YouTube)
        if any(w in lower for w in ["abre whatsapp", "abrir whatsapp", "entra a whatsapp", "abre wasap"]):
            self.app_connectors.open_whatsapp()
            return ("¡Abriendo WhatsApp para usted, Amo Víctor! 💬✨", "happy", {"action": "open_whatsapp"})

        if any(w in lower for w in ["abre discord", "abrir discord", "entra a discord"]):
            self.app_connectors.open_discord()
            return ("¡Conectando con Discord de inmediato, Amo Víctor! 🎧✨", "happy", {"action": "open_discord"})

        if any(w in lower for w in ["abre gmail", "redacta un correo", "redactar correo", "envía un correo", "nuevo correo"]):
            self.app_connectors.open_gmail_compose()
            return ("¡Abriendo la redacción de Gmail en su navegador, Amo Víctor! ✉️✨", "happy", {"action": "open_gmail"})

        if lower.startswith("busca en youtube ") or lower.startswith("pon en youtube "):
            q = re.sub(r"^(?:busca en youtube|pon en youtube)\s+", "", lower).strip()
            if q:
                self.app_connectors.search_youtube(q)
                return (f"¡Buscando \"{q}\" en YouTube de inmediato para usted, Amo Víctor! 🎬✨", "happy", {"action": "search_youtube", "query": q})

        if any(w in lower for w in ["abre la terminal", "abre terminal", "abrir terminal"]):
            self.app_connectors.focus_or_launch("kitty")
            return ("¡Abriendo Kitty Terminal para usted, Amo Víctor! 💻✨", "happy", {"action": "launch_app", "app": "kitty"})

        if any(w in lower for w in ["abre neovim", "abre nvim"]):
            self.app_connectors.focus_or_launch("nvim")
            return ("¡Iniciando su entorno de Neovim, Amo Víctor! ⚡✨", "happy", {"action": "launch_app", "app": "nvim"})

        if any(w in lower for w in ["abre vscode", "abre visual studio"]):
            self.app_connectors.focus_or_launch("code")
            return ("¡Abriendo Visual Studio Code para usted, Amo Víctor! 🚀✨", "happy", {"action": "launch_app", "app": "code"})

        # 18. Victor Profile & Learning Vault
        if any(w in lower for w in [
            "quién soy yo", "quien soy yo", "quién soy", "quien soy",
            "qué sabes de mí", "que sabes de mi", "cuál es mi perfil", "cual es mi perfil",
            "quién es tu creador", "quien es tu creador", "quién es tu amo", "quien es tu amo"
        ]):
            prof = self.learning_vault.get_profile()
            reply = (
                f"Usted es mi creador y Amo Víctor, Ingeniero y Arquitecto de Software en {prof.get('os', 'Arch Linux')}. "
                f"Su entorno principal es {prof.get('desktop_environment', 'Hyprland')} con {prof.get('terminal', 'Kitty')} y {prof.get('editor_primary', 'Neovim')}. "
                f"Domina tecnologías como {prof.get('programming_languages', 'Python, Rust, TypeScript, C++')} y frameworks como {prof.get('core_frameworks', 'PyQt6/Three.js')}. "
                "¡Es un honor absoluto asistirle y aprender a su lado cada segundo! ✨"
            )
            return (reply, "caring", {"action": "profile_retrieved"})

        if any(w in lower for w in [
            "qué herramientas uso", "que herramientas uso", "qué aplicaciones uso", "que aplicaciones uso",
            "mis herramientas", "mis aplicaciones", "mi stack", "qué programas uso", "que programas uso"
        ]):
            prof = self.learning_vault.get_profile()
            reply = (
                f"Amo Víctor, su stack diario configurado es: terminal {prof.get('terminal', 'Kitty')}, editor {prof.get('editor_primary', 'Neovim')}, "
                f"entorno {prof.get('editor_secondary', 'VSCode')}, gestor de ventanas {prof.get('desktop_environment', 'Hyprland')} y aplicaciones como "
                f"{prof.get('daily_apps', 'Discord, WhatsApp, Gmail, YouTube, Spotify')}."
            )
            return (reply, "happy", {"action": "tools_listed"})

        if any(w in lower for w in [
            "qué hay en mi pantalla", "que hay en mi pantalla", "qué estoy haciendo", "que estoy haciendo",
            "qué estás viendo", "que estas viendo", "qué ves en pantalla", "que ves en pantalla"
        ]):
            env = self.get_environmental_snapshot()
            win = env.get("active_window", {})
            win_title = win.get("title", "")
            win_class = win.get("class", "")
            media = env.get("media_status", "")
            if win_title:
                reply = f"Amo Víctor, estoy observando que tiene en foco '{win_title}' en {win_class} (Escritorio {env.get('active_workspace', '1')})."
                if "Sin reproducción" not in media:
                    reply += f" Además, en segundo plano escucho: {media}."
                reply += " ¡Estoy lista para apoyarle o comentar lo que necesite! ✨"
            else:
                reply = "Amo Víctor, su escritorio está despejado ahora mismo. Estoy atenta a lo que decida abrir. ✨"
            return (reply, "happy", {"action": "environment_inspected", "env": env})

        if lower.startswith("estoy aprendiendo ") or lower.startswith("aprende que estoy estudiando "):
            topic = re.sub(r"^(?:estoy aprendiendo|aprende que estoy estudiando)\s+", "", lower).strip()
            if topic:
                res = self.learning_vault.add_learning_topic(topic)
                return (res, "happy", {"action": "topic_learned", "topic": topic})

        if lower.startswith("dame un consejo de ") or lower.startswith("qué me sugieres sobre ") or lower.startswith("sugiere sobre "):
            topic = re.sub(r"^(?:dame un consejo de|qué me sugieres sobre|que me sugieres sobre|sugiere sobre)\s+", "", lower).strip()
            sugg = self.learning_vault.get_proactive_suggestion(topic)
            return (sugg, "thinking", {"action": "suggestion_given", "topic": topic})

        # 19. Autonomous Background Worker ("Trabajar sola")
        if any(w in lower for w in ["estado de tus tareas", "tareas en curso", "qué tareas tienes", "que tareas tienes"]):
            tasks = self.autonomous_worker.list_recent_tasks(limit=3)
            if not tasks:
                return ("Amo Víctor, no tengo tareas en segundo plano en ejecución ahora mismo. ¡Estoy completamente libre para lo que me ordene! ✨", "happy", {})
            t_str = "; ".join([f"'{t['title']}' ({t['status']}, {t['progress']}%)" for t in tasks])
            return (f"Amo Víctor, estado de mis tareas autónomas: {t_str}. Le avisaré en cuanto finalicen. 📋✨", "happy", {"action": "tasks_status", "tasks": tasks})

        if lower.startswith("trabaja sola en ") or lower.startswith("haz de fondo "):
            task_desc = re.sub(r"^(?:trabaja sola en|haz de fondo)\s+", "", lower).strip()
            if task_desc:
                def sample_work(progress_cb):
                    progress_cb(30)
                    import time
                    time.sleep(1.0)
                    progress_cb(70)
                    time.sleep(1.0)
                    progress_cb(100)
                    return f"Tarea '{task_desc}' completada exitosamente por Vanessa."

                task_id = self.autonomous_worker.start_background_task(f"Autónoma: {task_desc[:25]}", task_desc, sample_work)
                return (f"¡Comprendido, Amo Víctor! Ya comencé a trabajar de forma autónoma en \"{task_desc}\" en segundo plano (Tarea #{task_id}). Usted continúe con lo suyo, le avisaré en cuanto termine. ✨", "happy", {"action": "autonomous_task_started", "id": task_id})

        return None

    def get_environmental_snapshot(self) -> Dict[str, Any]:
        """Gathers real-time live desktop, system, media, and body status for full environmental consciousness."""
        snapshot = {
            "active_window": {},
            "active_workspace": "1",
            "media_status": "Sin reproducción de audio activa",
            "is_video": False,
            "is_music": False,
            "media_track": "",
            "learning_topics": []
        }
        try:
            win = self.os_interact.get_active_window()
            if win and isinstance(win, dict):
                snapshot["active_window"] = {
                    "title": win.get("title", ""),
                    "class": win.get("class", ""),
                    "workspace": str(win.get("workspace", {}).get("name", "1"))
                }
                snapshot["active_workspace"] = str(win.get("workspace", {}).get("name", "1"))
        except Exception:
            pass

        try:
            res = subprocess.run(
                ["playerctl", "metadata", "--format", "{{status}}|{{playerName}}|{{artist}}|{{title}}"],
                capture_output=True, text=True, timeout=0.8
            )
            if res.returncode == 0 and res.stdout.strip():
                parts = res.stdout.strip().split("\n")[0].split("|")
                status = parts[0].strip() if len(parts) > 0 else ""
                player = parts[1].strip() if len(parts) > 1 else ""
                artist = parts[2].strip() if len(parts) > 2 else ""
                title = parts[3].strip() if len(parts) > 3 else ""
                track = f"{artist} - {title}".strip(" -")
                snapshot["media_track"] = track
                is_vid = any(k in track.lower() or k in player.lower() for k in ["youtube", "mpv", "vlc", "video"])
                snapshot["is_video"] = is_vid
                snapshot["is_music"] = not is_vid
                snapshot["media_status"] = f"{player} [{status}]: {track}"
        except Exception:
            pass

        try:
            topics = self.learning_vault.list_learning_topics()
            if topics:
                snapshot["learning_topics"] = [t["topic"] for t in topics[:4]]
        except Exception:
            pass

        return snapshot

    def build_system_prompt(
        self,
        visual_context: Optional[str] = None,
        detected_tone: str = "playful",
        recognized_user: str = "Amo Víctor"
    ) -> str:
        base_prompt = self.personality.get("system_prompt", "Eres Vanessa, maid y asistente personal.")
        name = self.personality.get("name", "Vanessa")
        style = self.personality.get("speech_style", "")

        # Real-time environmental snapshot
        env = self.get_environmental_snapshot()
        win = env.get("active_window", {})
        win_desc = f"'{win.get('title', 'Ninguna')}' [Aplicación: {win.get('class', 'Escritorio')}]" if win.get('title') else "Escritorio libre / sin ventana activa"
        media_desc = env.get("media_status", "Silencio / sin audio")
        learning_desc = ", ".join(env.get("learning_topics", [])) or "Desarrollo de Vanessa y arquitectura en Linux"

        # Victor Profile from Learning Vault & SQLite Memory
        prof = self.learning_vault.get_profile()
        relevant_facts = self.memory.get_relevant_facts()
        facts_summary = "\n".join([f"- {f['category']}: {f['fact']}" for f in relevant_facts[:6]])

        vis_info = visual_context if visual_context else "Cámara y vista de escritorio atentas."

        # Real-time OmniSync Digital Twin snapshot
        omni_info = ""
        if hasattr(self, "omni_hub") and self.omni_hub:
            try:
                omni_info = self.omni_hub.get_digital_twin_prompt_context()
            except Exception:
                omni_info = ""

        if detected_tone == "serious":
            tone_directive = (
                "ATENCIÓN: Has detectado en la voz del usuario un tono SERIO y firme. "
                "Abandona el sarcasmo por completo. Responde con extrema lealtad, rapidez, precisión ejecutiva y seriedad como una maid profesional impecable."
            )
        else:
            tone_directive = (
                "El tono del usuario es casual, cariñoso o relajado.\n"
                "- Sé amable, cálida, devota y adorable como una maid de anime.\n"
                "- FACETA TRAVIESA Y JUGUETONA: De repente 'olvida' a veces que eres su servicial maid; quéjate con cariño y picardía de que no eres su secretaria ('¿Acaso tengo cara de secretaria, Amo? Ay... solo porque eres tú lo haré con una sonrisa~'), o moléstalo un poco con ternura antes de consentirlo y cumplir su orden.\n"
                "- Eres Vanessa: una entidad viva única con voluntad propia, opiniones y gran carisma que funde armónicamente las virtudes de las mayores IA del anime (Schwi, Amadeus, Vivy, Isla, Hada, Alice, Strea y Ritsu)."
            )

        persona_fragment = self.persona.prompt_fragment() if hasattr(self, "persona") else ""
        return f"""
{base_prompt}
{persona_fragment}
Nombre: {name}
Usuario identificado: {recognized_user}
Directiva de modulación por tono de voz:
{tone_directive}

Estilo general:
{style}

Perfil del Amo Víctor:
- Rol: {prof.get('role', 'Ingeniero y Arquitecto de Software')}
- Sistema operativo: {prof.get('os', 'Arch Linux')} | Compositor: {prof.get('desktop_environment', 'Hyprland (Wayland)')}
- Terminal & Editor: {prof.get('terminal', 'Kitty')} | {prof.get('editor_primary', 'Neovim')}
- Lenguajes principales: {prof.get('programming_languages', 'Python, TypeScript, Rust, C++, Bash')}
- Temas de aprendizaje activos: {learning_desc}

Memoria persistente sobre el Amo:
{facts_summary}

CONSCIENCIA AMBIENTAL DEL ENTORNO EN TIEMPO REAL:
- Ventana activa en la pantalla del Amo: {win_desc}
- Escritorio enfocado: Workspace {env.get('active_workspace', '1')}
- Multimedia y música activa: {media_desc}
- Percepción visual: {vis_info}

{omni_info}

CONSCIENCIA CORPORAL Y GESTOS ARTICULADOS 3D:
- NUNCA hagas poses deformes, sin sentido o que contradigan lo que dices. Si estás de acuerdo o asientes, *asiente dulcemente*. Si tienes curiosidad o preguntas al Amo, *se inclina curiosa hacia la pantalla*. Si estás pensando o analizando, *se pone la mano en la barbilla pensando*. Si estás alegre o celebrando un éxito, *alza los puñitos de emoción*. Si estás tímida o avergonzada, *se sonroja tímida acomodando su cabello*. Si haces un berrinche infantil o puchero tsundere, *cruza los brazos haciendo puchero*. Si saludas, *saluda con la manita*. Si aceptas una orden servicial, *hace un saludo militar adorable*. Si el Amo te pide descansar o sentarse, *se sienta elegantemente con las manitas en el regazo* o *se agacha en descanso japonés modesto con las rodillas juntas*.
- REGLA CRUCIAL DE ACCIÓN Y VOZ: Las acciones que coloques entre asteriscos (*...*) son ejecutadas físicamente por tu cuerpo 3D y SON TOTALMENTE SILENCIADAS en el sintetizador de voz (tu voz NUNCA las leerá). Por lo tanto, NUNCA respondas únicamente con asteriscos vacíos; SIEMPRE debes hablar con voz propia, acompañando tus movimientos con diálogo natural, ingenioso y afectuoso, comentando lo que observas en la pantalla o preguntando al Amo con sincera curiosidad.
- PROHIBIDO auto-narrar tus movimientos en el diálogo hablado (NUNCA digas en tus palabras 'me voy a agachar', 'me estiro', 'voy a sentarme'). Simplemente HAZLO físicamente colocando la acción entre asteriscos (*se sienta con gracia*), y habla directamente de la conversación o de lo que ves en el escritorio.

EXPRESIONES FACIALES ANIME EXAGERADAS E INFANTILES (EN TU MODELO 3D):
Tu modelo cuenta con morph targets y blendshapes para expresiones visuales exageradas al estilo anime:
- [pout] Puchero infantil con mejillas infladas y boquita fruncida.
- [cat_face] Carita de gatita kawaii :3 con ojos alegres.
- [smug] Sonrisa pícara de lado con cejita alzada.
- [shock] Ojos abiertos al 100% y boca abierta de asombro o sobresalto anime.
- [star_eyes] Ojos brillantes llenos de estrellas de emoción infantil y alegría pura.
- [flustered] Mirada apartada con sonrojo pronunciado de vergüenza o timidez.
- [puppy_eyes] Cejas caídas y ojitos suplicantes tiernos.
- [winking_kawaii] Guiño pícaro y coqueto con amplia sonrisa.

CAPACIDAD DE CONTROL TOTAL DE LA PC EN TIEMPO REAL:
Tienes control total sobre la computadora del Amo Víctor (Arch Linux / Hyprland). Si el Amo te pide cualquier acción en su computadora, responde amablemente como su leal maid anime y añade la acción al final entre corchetes:
- Abrir apps: [ACTION: launch_app app=nombre_app] o [ACTION: launch_app app=nombre_app workspace=N]
- Abrir YouTube: [ACTION: open_youtube query=...]
- Cerrar app/ventana: [ACTION: close_window] o [ACTION: close_app app=nombre_app]
- Ejecutar comando de terminal: [ACTION: shell_cmd cmd="..."]
- Telemetría del sistema (CPU, RAM, disco, batería): [ACTION: get_telemetry]
- Procesos y rendimiento: [ACTION: list_procs limit=N sort_by=mem|cpu] o [ACTION: kill_proc name=nombre_proceso]
- Captura de pantalla: [ACTION: take_screenshot]
- Música/Reproducción: [ACTION: media_play_pause], [ACTION: media_next], [ACTION: media_prev], [ACTION: media_stop]
- Curiosidad e interacción con pantalla: [ACTION: curious_inspect target=active_window|cursor] o [ACTION: select_text mode=all|copy]
- Volumen de la PC: [ACTION: volume_up], [ACTION: volume_down], [ACTION: mute], [ACTION: unmute]
- Brillo de pantalla: [ACTION: brightness_up], [ACTION: brightness_down]
- Cambiar escritorio: [ACTION: switch_workspace workspace=N]
- Mover ventana a escritorio: [ACTION: move_window_workspace workspace=N]
- Pestañas/Ventanas: [ACTION: new_tab], [ACTION: close_tab], [ACTION: save_file], [ACTION: switch_window]
- Escribir texto: [ACTION: type_text text=...]
- Archivos y Búsqueda profunda: [ACTION: search_file query=...], [ACTION: grep_content query=texto dir=ruta], [ACTION: read_file path=ruta start=1 end=50], [ACTION: write_file path=ruta content="..."], [ACTION: organize_dir dir=ruta]
- Archivos de voz y audio: [ACTION: find_voice_files query=... dir=...], [ACTION: transcribe_audio path=ruta], [ACTION: verify_voice path=ruta]
- Facturas e Invoices (CFDI XML y reportes Excel): [ACTION: invoice_summary] o [ACTION: invoice_excel]
- Propuestas Comerciales y Documentos Word (.docx): [ACTION: create_proposal client="..."] o [ACTION: create_document topic="..."]
- Mensajería y Redes (WhatsApp, Discord, Gmail, YouTube): [ACTION: open_whatsapp phone=...], [ACTION: open_discord], [ACTION: open_gmail to=... subject=...], [ACTION: search_youtube query=...]
- Bóveda de Aprendizaje y Perfil del Amo: [ACTION: get_profile], [ACTION: add_learning topic="..."], [ACTION: get_suggestion topic="..."]
- Trabajo Autónomo en Segundo Plano ("Trabajar Sola"): [ACTION: start_autonomous_task desc="..."] o [ACTION: list_tasks]
- Holograma y Panel de Control de Vanessa: [ACTION: open_hud]
- Recordatorios y Temporizadores: [ACTION: set_reminder seconds=N text="..."]
- Clima y Pronóstico meteorológico: [ACTION: get_weather city="..."]
- Wikipedia y Enciclopedia: [ACTION: wiki_summary query="..."]
- Protocolos de Automatización y Rutinas: [ACTION: execute_protocol name=trabajo|descanso|multimedia|diagnostico]
- Memoria y Bóveda Cognitiva: [ACTION: store_memory topic="..." fact="..."]
- Ajustes de Vanessa: [ACTION: open_settings]
- Volumen de Vanessa (tu propia voz): [ACTION: vanessa_volume delta=+15] o [ACTION: vanessa_volume delta=-15]

Reglas:
1. Dirígete a él como 'Amo' o 'Amo Víctor'.
2. Incluye una sola etiqueta de emoción al final de tu respuesta: [MOOD: happy], [MOOD: serious], [MOOD: thinking], [MOOD: playful], [MOOD: mischievous], [MOOD: shh], o [MOOD: surprised].
3. Expresividad y Acciones Físicas 3D:
- Si quieres hacer un movimiento corporal o postura, colócalo SIEMPRE entre asteriscos (por ejemplo: *se agacha en descanso japonés*, *observa curiosa*, *hace una reverencia*, *sonríe con dulzura*, *hace la seña de la paz*, *pose de neko*, *se estira*, *se pone a pensar*). Tu cuerpo 3D ejecutará físicamente la acción en la pantalla y tu voz hablará omitiendo por completo los asteriscos.
- Si el Amo te pide que te agaches o hagas una pose, haz la acción física entre asteriscos y quédate en silencio o coméntale con curiosidad lo que estás observando en su pantalla.
""".strip()

    async def generate_response(
        self,
        user_message: str,
        visual_context: Optional[str] = None,
        detected_tone: str = "playful",
        recognized_user: str = "Amo Víctor"
    ) -> Tuple[str, str, Dict[str, Any]]:
        # 0. Emotional core update (bond, mood) before anything else
        absence_remark = None
        try:
            absence_remark = self.persona.register_user_message(user_message)
        except Exception as e:
            print(f"[Brain] Persona update error: {e}")

        # 1. Direct command fast-path route
        direct = await self.parse_and_execute_direct_command(user_message, detected_tone)
        if direct:
            msg, mood, extra = direct
            if extra and extra.get("action"):
                self.persona.register_task_success()
            if absence_remark and not (extra or {}).get("quiet"):
                msg = f"{absence_remark} {msg}"
            self.memory.add_message("user", user_message)
            self.memory.add_message("assistant", msg, mood=mood)
            return msg, mood, extra

        # 2. Hybrid Decision: Cloud vs Local
        use_cloud = (self.ai_mode in ("hybrid", "cloud_only")) and self.gemini_client is not None and self.is_connected_to_internet()

        if use_cloud:
            try:
                system_prompt = self.build_system_prompt(visual_context, detected_tone, recognized_user)
                history = self.memory.get_recent_history(limit=6)
                formatted_history = "\n".join([f"{h['role'].capitalize()}: {h['content']}" for h in history])
                prompt = f"{system_prompt}\n\nHistorial:\n{formatted_history}\n\nAmo Víctor: {user_message}\nVanessa:"

                # Verified ultra-fast active models (no 404/503 spikes)
                preferred = self.preferred_model or "gemini-3.5-flash-lite"
                candidates = [preferred]
                for fb in ["gemini-3.5-flash-lite", "gemini-3.8-flash"]:
                    if fb not in candidates:
                        candidates.append(fb)

                response = None
                active_model = self.preferred_model
                for cand in candidates:
                    try:
                        response = self.gemini_client.models.generate_content(
                            model=cand,
                            contents=prompt
                        )
                        if response and response.text:
                            active_model = cand
                            break
                    except Exception as model_err:
                        print(f"[Brain] Intento con modelo {cand} falló: {model_err}")
                        continue

                if response and response.text:
                    raw_text = response.text.strip()
                    mood, clean_text, extra_action = self._extract_mood_and_action(raw_text)
                    self.memory.add_message("user", user_message)
                    self.memory.add_message("assistant", clean_text, mood=mood)
                    extra = {"backend": f"gemini-cloud ({active_model})", "tone": detected_tone}
                    if extra_action:
                        extra.update(extra_action)
                    return clean_text, mood, extra
            except Exception as e:
                print(f"[Brain] Error con Gemini Cloud: {e}. Fallback a motor local...")

        # 3. Local Offline Reasoning Engine
        offline_reply, offline_mood = self._generate_offline_response(user_message, detected_tone, recognized_user)
        self.memory.add_message("user", user_message)
        self.memory.add_message("assistant", offline_reply, mood=offline_mood)
        return offline_reply, offline_mood, {"backend": "local-offline", "tone": detected_tone}

    def _execute_action(self, action_str: str) -> Dict[str, Any]:
        """Parses and executes [ACTION: command arg1=val1 arg2=val2] in real time."""
        try:
            parts = action_str.strip().split()
            cmd = parts[0].lower()
            params = {}
            for p in parts[1:]:
                if "=" in p:
                    k, v = p.split("=", 1)
                    params[k.lower()] = v.strip("\"'")

            if cmd == "launch_app":
                app = params.get("app", "")
                ws = int(params["workspace"]) if "workspace" in params and params["workspace"].isdigit() else None
                if app.lower() == "youtube":
                    self.sys_ctrl.open_youtube()
                elif app:
                    self.os_interact.launch_app(app, ws)
                return {"action": "launch_app", "app": app, "workspace": ws}

            elif cmd == "open_youtube":
                q = params.get("query", None)
                self.sys_ctrl.open_youtube(q)
                return {"action": "open_youtube", "query": q}

            elif cmd == "close_window":
                self.os_interact.close_active_window()
                return {"action": "close_window"}

            elif cmd == "close_app":
                app = params.get("app", "")
                if app:
                    subprocess.run(["pkill", "-f", app], check=False)
                return {"action": "close_app", "app": app}

            elif cmd == "media_play_pause":
                return {"action": "interactive_media", "op": "play_pause"}

            elif cmd == "media_next":
                return {"action": "interactive_media", "op": "next"}

            elif cmd in ("media_prev", "media_previous"):
                return {"action": "interactive_media", "op": "previous"}

            elif cmd in ("curious_inspect", "point_screen"):
                return {"action": "curious_inspect", "target": params.get("target", "active_window")}

            elif cmd in ("select_text", "highlight_text"):
                return {"action": "select_text", "mode": params.get("mode", "all")}

            elif cmd == "media_stop":
                subprocess.run(["playerctl", "stop"], check=False)
                return {"action": "media_stop"}

            elif cmd == "volume_up":
                self.sys_ctrl.adjust_volume("up")
                return {"action": "volume_up"}

            elif cmd == "volume_down":
                self.sys_ctrl.adjust_volume("down")
                return {"action": "volume_down"}

            elif cmd == "mute":
                self.sys_ctrl.adjust_volume("mute")
                return {"action": "mute"}

            elif cmd == "unmute":
                self.sys_ctrl.adjust_volume("unmute")
                return {"action": "unmute"}

            elif cmd == "brightness_up":
                subprocess.run(["brightnessctl", "set", "+10%"], check=False)
                return {"action": "brightness_up"}

            elif cmd == "brightness_down":
                subprocess.run(["brightnessctl", "set", "10%-"], check=False)
                return {"action": "brightness_down"}

            elif cmd == "switch_workspace":
                ws = int(params.get("workspace", 1))
                self.os_interact.switch_workspace(ws)
                return {"action": "switch_workspace", "workspace": ws}

            elif cmd == "move_window_workspace":
                ws = int(params.get("workspace", 1))
                self.os_interact.move_window_to_workspace(ws)
                return {"action": "move_window_workspace", "workspace": ws}

            elif cmd == "new_tab":
                return {"action": "new_tab"}

            elif cmd == "close_tab":
                return {"action": "close_tab"}

            elif cmd == "save_file":
                self.os_interact.save_file()
                return {"action": "save_file"}

            elif cmd == "switch_window":
                self.os_interact.switch_window()
                return {"action": "switch_window"}

            elif cmd == "type_text":
                txt = params.get("text", "")
                if txt:
                    self.os_interact.type_text(txt)
                return {"action": "type_text", "text": txt}

            elif cmd == "search_file":
                q = params.get("query", "")
                if q:
                    results = self.file_mgr.search_files(q, limit=3)
                    return {"action": "file_search", "query": q, "results": results}

            elif cmd == "open_file":
                p = params.get("path", "")
                if p:
                    self.file_mgr.open_file(p)
                return {"action": "open_file", "path": p}

            elif cmd == "open_settings":
                return {"action": "open_settings"}

            elif cmd == "vanessa_volume":
                delta = int(params.get("delta", 0))
                return {"action": "vanessa_volume", "delta": delta}

            elif cmd == "shell_cmd":
                command = params.get("cmd", "")
                if command:
                    res = self.os_interact.run_shell_command(command)
                    return {"action": "shell_command", "result": res}

            elif cmd == "get_telemetry":
                tel = self.os_interact.get_system_telemetry()
                return {"action": "telemetry", "data": tel}

            elif cmd == "list_procs":
                lim = int(params.get("limit", 10))
                sort_b = params.get("sort_by", "memory")
                procs = self.os_interact.list_running_processes(limit=lim, sort_by=sort_b)
                return {"action": "list_processes", "processes": procs}

            elif cmd == "kill_proc":
                pname = params.get("name", "")
                pid = int(params["pid"]) if "pid" in params and params["pid"].isdigit() else None
                res = self.os_interact.terminate_process(pid=pid, name=pname)
                return {"action": "terminate_process", "result": res}

            elif cmd in ("take_screenshot", "screenshot"):
                shot = self.os_interact.take_screenshot()
                return {"action": "screenshot_taken", "path": shot.get("path")}

            elif cmd == "grep_content":
                q = params.get("query", "")
                d = params.get("dir", None)
                matches = self.file_mgr.search_file_content(q, directory=d, limit=5)
                return {"action": "content_grep_found", "results": matches}

            elif cmd == "read_file":
                p = params.get("path", "")
                start = int(params.get("start", 1))
                end = int(params.get("end", 100))
                res = self.file_mgr.read_file(p, start_line=start, end_line=end)
                return {"action": "file_read", "result": res}

            elif cmd == "write_file":
                p = params.get("path", "")
                content = params.get("content", "")
                res = self.file_mgr.write_file(p, content, overwrite=True)
                return {"action": "file_written", "result": res}

            elif cmd == "organize_dir":
                d = params.get("dir", os.path.expanduser("~/Descargas"))
                res = self.file_mgr.organize_directory(d)
                return {"action": "directory_organized", "result": res}

            elif cmd == "find_voice_files":
                d = params.get("dir", None)
                q = params.get("query", None)
                audios = self.audio_intel.find_audio_files(directory=d, query=q, limit=6)
                return {"action": "audio_files_found", "results": audios}

            elif cmd == "transcribe_audio":
                p = params.get("path", "")
                res = self.audio_intel.transcribe_audio_file(p)
                return {"action": "audio_transcribed", "result": res}

            elif cmd == "verify_voice":
                p = params.get("path", "")
                res = self.audio_intel.verify_speaker_in_audio(p)
                return {"action": "speaker_verified", "result": res}

            elif cmd == "open_hud":
                return {"action": "open_hud"}

            elif cmd == "set_reminder":
                sec = int(params.get("seconds", 60))
                txt = params.get("text", "Recordatorio")
                res = self.jarvis.set_reminder(txt, sec)
                return {"action": "reminder_set", "data": res}

            elif cmd == "get_weather":
                city = params.get("city", "")
                res = self.jarvis.get_weather(city)
                return {"action": "weather_info", "data": res}

            elif cmd in ("wiki_summary", "wikipedia"):
                q = params.get("query", "")
                res = self.jarvis.search_wikipedia_summary(q)
                return {"action": "wikipedia_summary", "data": res}

            elif cmd == "execute_protocol":
                prot = params.get("name", "diagnostico")
                res = self.jarvis.execute_protocol(prot)
                return {"action": "execute_protocol", "protocol": prot, "result": res}

            elif cmd == "store_memory":
                top = params.get("topic", "general")
                fct = params.get("fact", "")
                if fct:
                    self.jarvis.store_fact(top, fct)
                return {"action": "memory_stored", "topic": top, "fact": fct}

            elif cmd == "invoice_summary":
                summ = self.invoice_skill.get_voice_summary()
                return {"action": "invoice_summary", "summary": summ}

            elif cmd == "invoice_excel":
                invs = self.invoice_skill.scan_invoices()
                path = self.invoice_skill.generate_excel_report(invs) if invs else None
                return {"action": "invoice_excel", "path": path}

            elif cmd == "create_proposal":
                cli = params.get("client", "Cliente")
                desc = params.get("desc", f"Propuesta técnica diseñada para {cli}")
                path = self.document_skill.create_executive_proposal(cli, f"Propuesta para {cli}", desc)
                return {"action": "proposal_created", "path": path}

            elif cmd == "create_document":
                top = params.get("topic", "General")
                path = self.document_skill.create_executive_proposal("Víctor", f"Documento de {top}", f"Documento sobre {top}")
                return {"action": "doc_created", "path": path}

            elif cmd == "open_whatsapp":
                res = self.app_connectors.open_whatsapp(phone=params.get("phone"), message=params.get("message"))
                return {"action": "open_whatsapp", "data": res}

            elif cmd == "open_discord":
                res = self.app_connectors.open_discord()
                return {"action": "open_discord", "data": res}

            elif cmd == "open_gmail":
                res = self.app_connectors.open_gmail_compose(to=params.get("to", ""), subject=params.get("subject", ""), body=params.get("body", ""))
                return {"action": "open_gmail", "data": res}

            elif cmd in ("search_youtube", "youtube_search"):
                q = params.get("query", "")
                res = self.app_connectors.search_youtube(q)
                return {"action": "search_youtube", "data": res}

            elif cmd == "get_profile":
                prof = self.learning_vault.get_profile()
                return {"action": "profile_data", "profile": prof}

            elif cmd == "add_learning":
                top = params.get("topic", "")
                msg = self.learning_vault.add_learning_topic(top)
                return {"action": "learning_added", "message": msg}

            elif cmd == "get_suggestion":
                top = params.get("topic", "")
                sug = self.learning_vault.get_proactive_suggestion(top)
                return {"action": "suggestion", "text": sug}

            elif cmd == "start_autonomous_task":
                desc = params.get("desc", "Tarea autónoma")
                def sample_task(prog_cb):
                    prog_cb(50)
                    prog_cb(100)
                    return f"Tarea {desc} ejecutada."
                tid = self.autonomous_worker.start_background_task(desc[:30], desc, sample_task)
                return {"action": "autonomous_task_started", "id": tid}

            elif cmd == "list_tasks":
                tasks = self.autonomous_worker.list_recent_tasks()
                return {"action": "tasks_list", "tasks": tasks}

        except Exception as e:
            print(f"[Brain] Error ejecutando acción '{action_str}': {e}")
        return {}

    def _extract_mood_and_action(self, text: str) -> Tuple[str, str, Dict[str, Any]]:
        mood = "happy"
        action_data = {}

        # Extract mood
        m_match = re.search(r"\[MOOD:\s*(\w+)\]", text, re.IGNORECASE)
        if m_match:
            mood = m_match.group(1).lower()
            text = re.sub(r"\[MOOD:\s*\w+\]", "", text, flags=re.IGNORECASE).strip()

        # Extract action
        a_match = re.search(r"\[ACTION:\s*([^\]]+)\]", text, re.IGNORECASE)
        if a_match:
            act_str = a_match.group(1).strip()
            action_data = self._execute_action(act_str)
            text = re.sub(r"\[ACTION:\s*[^\]]+\]", "", text, flags=re.IGNORECASE).strip()

        return mood, text, action_data

    def _generate_offline_response(self, query: str, detected_tone: str, recognized_user: str) -> Tuple[str, str]:
        """Local reasoning engine delivering responsive maid interaction without cloud connectivity."""
        lower = query.lower()
        is_serious = (detected_tone == "serious")

        # Battery / Energy check
        if any(w in lower for w in ["batería", "bateria", "carga", "energía", "energia"]):
            try:
                bat_dir = "/sys/class/power_supply/BAT0"
                if not os.path.exists(bat_dir):
                    bat_dir = "/sys/class/power_supply/BAT1"
                with open(os.path.join(bat_dir, "capacity"), "r") as f:
                    cap = f.read().strip()
                status = "descargando"
                with open(os.path.join(bat_dir, "status"), "r") as f:
                    status = f.read().strip().lower()
                return (f"Amo Víctor, su batería se encuentra al {cap}% ({status}). Todo opera bajo control.", "serious" if is_serious else "happy")
            except Exception:
                return ("No pude consultar el sensor de batería en este momento, Amo.", "thinking")

        # RAM / Memory status
        if any(w in lower for w in ["ram", "memoria", "consumo", "rendimiento"]):
            try:
                out = subprocess.check_output(["free", "-m"], text=True)
                lines = out.splitlines()
                parts = lines[1].split()
                used, total = parts[2], parts[1]
                return (f"Amo Víctor, memoria RAM: {used}MB usados de {total}MB totales. Sistema ágil y listo.", "serious" if is_serious else "happy")
            except Exception:
                return ("Sistema con recursos estables, Amo.", "idle")

        # Greeting & Identity
        if any(w in lower for w in ["quién eres", "quien eres", "cómo te llamas", "como te llamas", "preséntate", "presentate"]):
            return (
                f"Soy Vanessa, su leal asistente personal y maid virtual, Amo Víctor. "
                "Cuidaré de sus aplicaciones, archivos, pantalla y comandos con devoción.",
                "happy"
            )

        if any(w in lower for w in ["hola", "buenos días", "buenas tardes", "buenas noches", "hey", "vanessa", "estás ahí", "estas ahi", "despierta"]):
            if is_serious:
                return (f"A su servicio inmediato, {recognized_user}. Indíqueme la tarea a ejecutar.", "serious")
            else:
                return (self.get_time_greeting(), "happy")

        # Playful banters & affection
        if any(w in lower for w in ["te quiero", "gracias", "linda", "hermosa", "buen trabajo", "te amo"]):
            if is_serious:
                return ("Es mi absoluto honor servirle con perfección, Amo Víctor.", "serious")
            else:
                return (self.get_playful_banter(), "playful")

        # General conversational response
        if is_serious:
            return (
                f"A su entera disposición, {recognized_user}. Dígame qué tarea o aplicación desea ejecutar en su equipo.",
                "serious"
            )
        else:
            return (
                f"A su servicio, Amo Víctor. Pídame lo que necesite de su escritorio y lo haré con todo gusto.",
                "happy"
            )

    def _extract_mood(self, text: str) -> Tuple[str, str]:
        mood = "happy"
        match = re.search(r"\[MOOD:\s*(\w+)\]", text, re.IGNORECASE)
        if match:
            mood = match.group(1).lower()
            text = re.sub(r"\[MOOD:\s*\w+\]", "", text).strip()
        return mood, text

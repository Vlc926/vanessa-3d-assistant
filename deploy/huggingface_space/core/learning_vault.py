"""
Learning Vault & Victor Knowledge Base for Vanessa.
Stores Victor's profile, dev stack, ongoing learning topics, and provides proactive suggestions.
Persists into SQLite (assistant_memory.db).
"""
import sqlite3
import datetime
from typing import Dict, Any, List, Optional


class LearningVault:
    def __init__(self, db_path: str = "data/assistant_memory.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # User Identity & Preferences Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    category TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Dynamic Learning Topics Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learning_topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT UNIQUE,
                    category TEXT,
                    notes TEXT,
                    status TEXT DEFAULT 'learning',
                    resources TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_reviewed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

        self._seed_default_profile()

    def _seed_default_profile(self):
        defaults = [
            ("name", "Víctor", "identity"),
            ("title", "Amo Víctor", "identity"),
            ("role", "Software Engineer & AI Architect", "professional"),
            ("os", "Arch Linux / CachyOS (Rolling Release)", "environment"),
            ("desktop_environment", "Hyprland (Wayland Compositor)", "environment"),
            ("terminal", "Kitty Terminal", "tools"),
            ("editor_primary", "Neovim", "tools"),
            ("editor_secondary", "Visual Studio Code", "tools"),
            ("programming_languages", "Python, TypeScript, Rust, C++, Bash", "skills"),
            ("core_frameworks", "PyQt6, Three.js, Fast-Whisper, Kokoro TTS, Gemini API", "skills"),
            ("daily_apps", "Discord, WhatsApp Web, Gmail, YouTube, Spotify", "tools"),
        ]
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for key, val, cat in defaults:
                cursor.execute("""
                    INSERT OR IGNORE INTO user_profile (key, value, category)
                    VALUES (?, ?, ?)
                """, (key, val, cat))
            conn.commit()

    def get_profile(self) -> Dict[str, Any]:
        """Returns Victor's full known profile."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value, category FROM user_profile")
            rows = cursor.fetchall()
            profile = {}
            for k, v, c in rows:
                profile[k] = v
            return profile

    def update_profile_field(self, key: str, value: str, category: str = "general"):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_profile (key, value, category, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
            """, (key, value, category))
            conn.commit()

    def add_learning_topic(self, topic: str, category: str = "Tech", notes: str = "", resources: str = "") -> str:
        """Registers a new topic Victor is studying."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO learning_topics (topic, category, notes, resources, last_reviewed)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(topic) DO UPDATE SET notes=excluded.notes, resources=excluded.resources, last_reviewed=CURRENT_TIMESTAMP
            """, (topic.strip(), category.strip(), notes.strip(), resources.strip()))
            conn.commit()
        return f"Amo Víctor, he registrado '{topic}' en mi bóveda de aprendizaje. Le acompañaré y buscaré referencias útiles para usted. ✨"

    def list_learning_topics(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, topic, category, notes, status, last_reviewed FROM learning_topics ORDER BY last_reviewed DESC")
            rows = cursor.fetchall()
            return [
                {"id": r[0], "topic": r[1], "category": r[2], "notes": r[3], "status": r[4], "reviewed": r[5]}
                for r in rows
            ]

    def get_proactive_suggestion(self, topic: Optional[str] = None) -> str:
        """Generates proactive suggestions, docs, or insights based on what Victor is studying."""
        profile = self.get_profile()
        topics = self.list_learning_topics()

        if not topic and topics:
            target_topic = topics[0]["topic"]
        else:
            target_topic = topic or "arquitectura de software"

        suggestions_map = {
            "rust": "En Rust, recuerde revisar el modelo de propiedad (borrow checker) y los smart pointers como Arc y Mutex para concurrencia segura. ¿Le busco la documentación oficial de docs.rs?",
            "hyprland": "Para Hyprland, dominar los window rules v2 y los gestos táctiles optimiza enormemente el flujo de trabajo en Wayland. ¡Podemos crear un atajo personalizado si lo desea!",
            "python": "En Python avanzado, el uso de asyncio y uvloop o generadores asíncronos reduce la latencia en tareas de I/O concurrentes a casi cero.",
            "three.js": "En Three.js / WebGL, agrupar las llamadas de renderizado mediante InstancedMesh y optimizar las texturas reduce el consumo de GPU de manera radical."
        }

        for k, text in suggestions_map.items():
            if k in target_topic.lower():
                return f"Amo Víctor, con respecto a {target_topic}: {text} ✨"

        return f"Amo Víctor, respecto a {target_topic}, he tomado nota y puedo investigar la documentación más reciente o crearle un documento resumen cuando guste. ✨"

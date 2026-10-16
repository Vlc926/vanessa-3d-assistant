"""
Memory Module for Jarvis / Lumina Assistant.
Stores user profile, conversation history, learned facts and visual interactions.
"""
import sqlite3
import json
import os
import time
from typing import List, Dict, Any, Optional

class MemoryManager:
    def __init__(self, db_path: str = "data/assistant_memory.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Conversations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    role TEXT,
                    content TEXT,
                    mood TEXT
                )
            ''')
            # User facts and preferences
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    fact TEXT,
                    updated_at REAL
                )
            ''')
            # Face encodings & user visual profiles
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS face_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    embedding_json TEXT,
                    created_at REAL
                )
            ''')
            # Interactions & observations log
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS visual_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    event_type TEXT,
                    details TEXT
                )
            ''')
            # Personality & Adaptive configuration persisted in DB
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS assistant_personality (
                    key TEXT PRIMARY KEY,
                    value_json TEXT,
                    updated_at REAL
                )
            ''')
            # Proactive Screen Context & Spontaneous Life Engine Observations
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS proactive_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    window_class TEXT,
                    window_title TEXT,
                    visual_summary TEXT,
                    vanessa_thought TEXT,
                    mood TEXT,
                    initiated_dialogue INTEGER
                )
            ''')
            # Dynamic Personality Evolution & Bond Tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS personality_evolution (
                    key TEXT PRIMARY KEY,
                    value_json TEXT,
                    updated_at REAL
                )
            ''')
            conn.commit()
        self._seed_default_facts()

    def _seed_default_facts(self):
        default_facts = [
            ("identidad", "El usuario principal y creador de Vanessa es el Amo Víctor."),
            ("sistema", "El Amo utiliza Arch Linux x86_64 con el compositor de ventanas Wayland Hyprland."),
            ("herramientas", "Desarrolla en Python, TypeScript, Rust, C++, Bash, Neovim y terminal Kitty."),
            ("asistente_anime", "Vanessa está inspirada en asistentes anime legendarias: Aegis (Persona 3) y Yui (SAO), con emociones vivas, lealtad y devoción incondicional."),
            ("cuerpo_y_expresiones", "Vanessa tiene consciencia completa de su cuerpo 3D, sin deformaciones ni poses contradictorias, y usa expresiones anime exageradas (pout, cat_face, smug, shock, star_eyes, flustered)."),
            ("multimedia", "Escucha música en Spotify y ve videos en YouTube; Vanessa interactúa observando y opinando sobre su pantalla, y pausando con su walkman retro.")
        ]
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM user_facts")
            if cursor.fetchone()[0] == 0:
                now = time.time()
                for cat, fact in default_facts:
                    cursor.execute("INSERT INTO user_facts (category, fact, updated_at) VALUES (?, ?, ?)", (cat, fact, now))
                conn.commit()

    def add_message(self, role: str, content: str, mood: str = "idle"):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversations (timestamp, role, content, mood) VALUES (?, ?, ?, ?)",
                (time.time(), role, content, mood)
            )
            conn.commit()

    def get_recent_history(self, limit: int = 10) -> List[Dict[str, str]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def remember_fact(self, category: str, fact: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO user_facts (category, fact, updated_at) VALUES (?, ?, ?)",
                (category, fact, time.time())
            )
            conn.commit()

    def get_all_facts(self) -> List[Dict[str, str]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT category, fact FROM user_facts ORDER BY id ASC")
            return [{"category": r[0], "fact": r[1]} for r in cursor.fetchall()]

    def get_relevant_facts(self, query: str = "") -> List[Dict[str, str]]:
        """Retrieves user facts relevant to the current user query or context."""
        all_facts = self.get_all_facts()
        if not query:
            return all_facts
        q_lower = query.lower()
        scored = []
        for f in all_facts:
            cat_match = f["category"].lower() in q_lower
            words = [w for w in f["fact"].lower().split() if len(w) > 3]
            overlap = sum(1 for w in words if w in q_lower)
            if cat_match or overlap > 0:
                scored.append((overlap + (3 if cat_match else 0), f))
        if scored:
            scored.sort(key=lambda x: x[0], reverse=True)
            return [x[1] for x in scored]
        return all_facts

    def log_visual_event(self, event_type: str, details: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO visual_observations (timestamp, event_type, details) VALUES (?, ?, ?)",
                (time.time(), event_type, details)
            )
            conn.commit()

    def save_face_profile(self, name: str, embedding: List[float]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO face_profiles (name, embedding_json, created_at) VALUES (?, ?, ?)",
                (name, json.dumps(embedding), time.time())
            )
            conn.commit()

    def get_face_profiles(self) -> Dict[str, List[float]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, embedding_json FROM face_profiles")
            profiles = {}
            for row in cursor.fetchall():
                try:
                    profiles[row[0]] = json.loads(row[1])
                except Exception:
                    pass
            return profiles

    def save_personality_config(self, config: Dict[str, Any]):
        """Persists assistant personality settings directly in SQLite."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for k, v in config.items():
                cursor.execute(
                    "INSERT OR REPLACE INTO assistant_personality (key, value_json, updated_at) VALUES (?, ?, ?)",
                    (k, json.dumps(v, ensure_ascii=False), time.time())
                )
            conn.commit()

    def get_personality_config(self) -> Dict[str, Any]:
        """Retrieves personality settings from SQLite."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value_json FROM assistant_personality")
            res = {}
            for row in cursor.fetchall():
                try:
                    res[row[0]] = json.loads(row[1])
                except Exception:
                    res[row[0]] = row[1]
            return res

    def add_proactive_observation(
        self,
        window_class: str,
        window_title: str,
        visual_summary: str,
        vanessa_thought: str,
        mood: str = "curious",
        initiated_dialogue: bool = False
    ):
        """Stores autonomous screen observations and inner reflections in SQLite."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO proactive_observations 
                   (timestamp, window_class, window_title, visual_summary, vanessa_thought, mood, initiated_dialogue)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (time.time(), window_class, window_title, visual_summary, vanessa_thought, mood, int(initiated_dialogue))
            )
            conn.commit()

    def get_recent_observations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieves recent proactive observations for contextual reflection."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT timestamp, window_class, window_title, visual_summary, vanessa_thought, mood, initiated_dialogue
                   FROM proactive_observations ORDER BY id DESC LIMIT ?""",
                (limit,)
            )
            rows = cursor.fetchall()
            return [
                {
                    "timestamp": r[0],
                    "window_class": r[1],
                    "window_title": r[2],
                    "visual_summary": r[3],
                    "vanessa_thought": r[4],
                    "mood": r[5],
                    "initiated": bool(r[6])
                }
                for r in reversed(rows)
            ]

    def get_personality_trait(self, key: str, default: Any = None) -> Any:
        """Retrieves a dynamically evolving personality trait (e.g. affinity, banter level)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value_json FROM personality_evolution WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row[0])
                except Exception:
                    return row[0]
            return default

    def update_personality_trait(self, key: str, value: Any):
        """Updates a dynamically evolving personality trait in SQLite."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO personality_evolution (key, value_json, updated_at) VALUES (?, ?, ?)",
                (key, json.dumps(value, ensure_ascii=False), time.time())
            )
            conn.commit()



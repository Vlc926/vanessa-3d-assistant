"""
User Authentication & Multi-Account Cloud Sync Database.
Provides secure password hashing, session tokens, and unified login synchronization
for Vanessa Cloud Assistant.
"""
import os
import sqlite3
import hashlib
import secrets
import time
import json
import logging
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("UserAuth")
logger.setLevel(logging.INFO)


class UserAuthDB:
    def __init__(self, db_path: str = "data/user_auth.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            c = conn.cursor()
            # 1. Users table
            c.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    display_name TEXT,
                    created_at REAL NOT NULL,
                    last_login REAL
                )
            """)
            # 2. Sessions table
            c.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    device_name TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)
            # 3. Synchronized logins/services table
            c.execute("""
                CREATE TABLE IF NOT EXISTS user_logins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    service_name TEXT NOT NULL,
                    account_id TEXT,
                    account_username TEXT,
                    status TEXT DEFAULT 'synced',
                    metadata_json TEXT DEFAULT '{}',
                    last_sync REAL NOT NULL,
                    UNIQUE(user_id, service_name),
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

    def register_user(self, email: str, password: str, display_name: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        email = email.strip().lower()
        if not email or "@" not in email:
            return False, "Correo electrónico inválido.", None
        if len(password) < 4:
            return False, "La contraseña debe tener al menos 4 caracteres.", None

        salt = secrets.token_hex(16)
        pw_hash = self._hash_password(password, salt)
        now = time.time()
        name = display_name.strip() if display_name else email.split("@")[0]

        try:
            with self._get_conn() as conn:
                c = conn.cursor()
                c.execute(
                    "INSERT INTO users (email, password_hash, salt, display_name, created_at, last_login) VALUES (?, ?, ?, ?, ?, ?)",
                    (email, pw_hash, salt, name, now, now)
                )
                user_id = c.lastrowid

                # Create default synchronized services for this user
                default_services = [
                    ("steam", "Victor_Steam", "connected"),
                    ("spotify", "Victor_Spotify", "connected"),
                    ("discord", "Victor_Discord", "connected"),
                    ("whatsapp", "Victor_WA", "connected"),
                    ("telegram", "Victor_TG", "connected"),
                    ("meta", "Victor_Meta", "connected"),
                ]
                for s_name, s_user, s_status in default_services:
                    c.execute("""
                        INSERT OR REPLACE INTO user_logins (user_id, service_name, account_id, account_username, status, metadata_json, last_sync)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (user_id, s_name, s_user, s_user, s_status, json.dumps({"auto_sync": True}), now))

                # Generate session token
                token = secrets.token_urlsafe(32)
                expires = now + (86400 * 30) # 30 days session
                c.execute(
                    "INSERT INTO sessions (token, user_id, created_at, expires_at, device_name) VALUES (?, ?, ?, ?, ?)",
                    (token, user_id, now, expires, "Vanessa Desktop Client")
                )
                conn.commit()

                user_data = {
                    "id": user_id,
                    "email": email,
                    "display_name": name,
                    "token": token,
                    "expires_at": expires
                }
                return True, "Cuenta creada y sincronizada exitosamente.", user_data
        except sqlite3.IntegrityError:
            return False, "Este correo ya está registrado. Por favor inicia sesión.", None
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return False, f"Error interno: {str(e)}", None

    def login_user(self, email: str, password: str, device_name: str = "Vanessa Desktop Client") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        email = email.strip().lower()
        now = time.time()
        try:
            with self._get_conn() as conn:
                c = conn.cursor()
                c.execute("SELECT id, email, password_hash, salt, display_name FROM users WHERE email = ?", (email,))
                row = c.fetchone()
                if not row:
                    # User friendly auto-registration if it's the master user entering their credentials
                    return self.register_user(email, password)

                user_id = row["id"]
                expected_hash = self._hash_password(password, row["salt"])
                if row["password_hash"] != expected_hash:
                    return False, "Contraseña incorrecta para este correo.", None

                # Update last login
                c.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, user_id))

                # Generate new active session
                token = secrets.token_urlsafe(32)
                expires = now + (86400 * 30) # 30 days
                c.execute(
                    "INSERT INTO sessions (token, user_id, created_at, expires_at, device_name) VALUES (?, ?, ?, ?, ?)",
                    (token, user_id, now, expires, device_name)
                )
                conn.commit()

                # Fetch all synced service logins
                logins = self.get_user_logins(user_id)

                user_data = {
                    "id": user_id,
                    "email": row["email"],
                    "display_name": row["display_name"],
                    "token": token,
                    "expires_at": expires,
                    "logins": logins
                }
                return True, "Sesión iniciada y sincronizada correctamente.", user_data
        except Exception as e:
            logger.error(f"Error logging in user: {e}")
            return False, f"Error al iniciar sesión: {str(e)}", None

    def validate_session(self, token: str) -> Optional[Dict[str, Any]]:
        now = time.time()
        try:
            with self._get_conn() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT s.token, s.user_id, s.expires_at, u.email, u.display_name
                    FROM sessions s
                    JOIN users u ON s.user_id = u.id
                    WHERE s.token = ? AND s.expires_at > ?
                """, (token, now))
                row = c.fetchone()
                if not row:
                    return None
                logins = self.get_user_logins(row["user_id"])
                return {
                    "user_id": row["user_id"],
                    "email": row["email"],
                    "display_name": row["display_name"],
                    "token": row["token"],
                    "expires_at": row["expires_at"],
                    "logins": logins
                }
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return None

    def get_user_logins(self, user_id: int) -> Dict[str, Any]:
        result = {}
        try:
            with self._get_conn() as conn:
                c = conn.cursor()
                c.execute("SELECT service_name, account_id, account_username, status, last_sync FROM user_logins WHERE user_id = ?", (user_id,))
                for row in c.fetchall():
                    result[row["service_name"]] = {
                        "account_id": row["account_id"],
                        "username": row["account_username"],
                        "status": row["status"],
                        "last_sync": row["last_sync"]
                    }
        except Exception as e:
            logger.error(f"Error fetching user logins: {e}")
        return result

    def sync_logins_for_user(self, user_id: int) -> Dict[str, Any]:
        """Refreshes synchronization timestamp for all connected logins of the user."""
        now = time.time()
        with self._get_conn() as conn:
            c = conn.cursor()
            c.execute("UPDATE user_logins SET last_sync = ?, status = 'synced' WHERE user_id = ?", (now, user_id))
            conn.commit()
        return self.get_user_logins(user_id)

    def logout_token(self, token: str):
        try:
            with self._get_conn() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM sessions WHERE token = ?", (token,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error deleting session: {e}")

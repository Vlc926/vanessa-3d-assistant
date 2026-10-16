"""
Autonomous Worker Engine for Vanessa ("Trabajar sola").
Enables Vanessa to execute multi-step background tasks autonomously:
- File organization and directory cleanups
- Invoice batch processing and report compilation
- Technical research and document generation
- Asynchronous task queues persisted in SQLite
- Signals and notifications when jobs finish
"""
import sqlite3
import threading
import datetime
from typing import Dict, Any, List, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal


class AutonomousWorker(QObject):
    task_started = pyqtSignal(str)          # task_name
    task_progress = pyqtSignal(str, int)     # task_name, percentage (0-100)
    task_completed = pyqtSignal(str, str)    # task_name, result_summary

    def __init__(self, db_path: str = "data/assistant_memory.db"):
        super().__init__()
        self.db_path = db_path
        self.on_task_finished_callback: Optional[Callable[[str, str], None]] = None
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS autonomous_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'pending',
                    progress INTEGER DEFAULT 0,
                    result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    finished_at TIMESTAMP
                )
            """)
            conn.commit()

    def start_background_task(self, title: str, description: str, task_func: Callable[[Callable[[int], None]], str]) -> int:
        """Launches an autonomous task in a background daemon thread with persistent tracking."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO autonomous_tasks (title, description, status, progress)
                VALUES (?, ?, 'running', 0)
            """, (title, description))
            task_id = cursor.lastrowid
            conn.commit()

        self.task_started.emit(title)

        def runner():
            try:
                def progress_cb(pct: int):
                    with self._get_connection() as c:
                        c.execute("UPDATE autonomous_tasks SET progress = ? WHERE id = ?", (pct, task_id))
                        c.commit()
                    self.task_progress.emit(title, pct)

                result_text = task_func(progress_cb)

                with self._get_connection() as c:
                    c.execute("""
                        UPDATE autonomous_tasks
                        SET status = 'completed', progress = 100, result = ?, finished_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (result_text, task_id))
                    c.commit()

                self.task_completed.emit(title, result_text)
                if callable(self.on_task_finished_callback):
                    self.on_task_finished_callback(title, result_text)

            except Exception as e:
                err_msg = f"Error: {e}"
                with self._get_connection() as c:
                    c.execute("""
                        UPDATE autonomous_tasks
                        SET status = 'failed', result = ?, finished_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (err_msg, task_id))
                    c.commit()
                self.task_completed.emit(title, f"Ocurrió un problema: {err_msg}")

        t = threading.Thread(target=runner, daemon=True)
        t.start()
        return task_id

    def list_active_tasks(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, description, status, progress, created_at
                FROM autonomous_tasks
                WHERE status = 'running'
                ORDER BY created_at DESC
            """)
            rows = cursor.fetchall()
            return [
                {"id": r[0], "title": r[1], "desc": r[2], "status": r[3], "progress": r[4], "created": r[5]}
                for r in rows
            ]

    def list_recent_tasks(self, limit: int = 5) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, status, progress, result, finished_at
                FROM autonomous_tasks
                ORDER BY id DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [
                {"id": r[0], "title": r[1], "status": r[2], "progress": r[3], "result": r[4], "finished": r[5]}
                for r in rows
            ]

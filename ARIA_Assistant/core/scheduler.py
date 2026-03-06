"""📅 ПЛАНИРОВЩИК ЗАДАЧ (SQLite)"""

import sqlite3
import os
from datetime import date, datetime
from utils.logger import log

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "aria_memory.db")

class Scheduler:
    def _conn(self):
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            date     TEXT NOT NULL,
            time     TEXT NOT NULL,
            task     TEXT NOT NULL,
            priority INTEGER DEFAULT 2,
            done     INTEGER DEFAULT 0
        )""")
        conn.commit()
        return conn

    def add_task(self, time_str: str, task_name: str, priority: int = 2) -> int:
        today = date.today().isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO tasks (date, time, task, priority) VALUES (?, ?, ?, ?)",
                (today, time_str, task_name, priority)
            )
            return cur.lastrowid

    def get_today_tasks(self) -> list:
        today = date.today().isoformat()
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE date=? ORDER BY time ASC", (today,)
            ).fetchall()
        return [dict(r) for r in rows]

    def mark_done(self, task_id: int):
        with self._conn() as conn:
            conn.execute("UPDATE tasks SET done=1 WHERE id=?", (task_id,))

    def delete_task(self, task_id: int):
        with self._conn() as conn:
            conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))

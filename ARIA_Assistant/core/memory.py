"""
🧠 СИСТЕМА ПАМЯТИ И ОБУЧЕНИЯ
============================
• Хранит историю разговоров
• Запоминает предпочтения пользователя
• Отслеживает паттерны поведения
• Адаптирует поведение ИИ со временем
База: SQLite (встроен в Python, не нужен сервер)
"""

import sqlite3
import json
import os
from datetime import datetime, date
from utils.logger import log

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "aria_memory.db")


class MemorySystem:
    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            # История сообщений
            conn.execute("""CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                role       TEXT NOT NULL,          -- 'user' | 'assistant'
                content    TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            )""")

            # Знания (что ИИ узнал о пользователе)
            conn.execute("""CREATE TABLE IF NOT EXISTS learnings (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                fact       TEXT NOT NULL UNIQUE,   -- Текст факта
                confidence REAL DEFAULT 1.0,        -- Уверенность (растёт с повторами)
                count      INTEGER DEFAULT 1,       -- Сколько раз подтверждалось
                created_at TEXT DEFAULT (datetime('now','localtime')),
                updated_at TEXT DEFAULT (datetime('now','localtime'))
            )""")

            # Предпочтения (ключ-значение)
            conn.execute("""CREATE TABLE IF NOT EXISTS preferences (
                key        TEXT PRIMARY KEY,
                value      TEXT NOT NULL,
                updated_at TEXT DEFAULT (datetime('now','localtime'))
            )""")

            # Частота запросов (для адаптации)
            conn.execute("""CREATE TABLE IF NOT EXISTS query_stats (
                intent     TEXT PRIMARY KEY,
                count      INTEGER DEFAULT 1,
                last_used  TEXT DEFAULT (datetime('now','localtime'))
            )""")

            # Настройки приложения
            conn.execute("""CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )""")
            conn.commit()

    # ─── ИСТОРИЯ СООБЩЕНИЙ ────────────────────────────────────────────────────
    def add_message(self, role: str, content: str):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO messages (role, content) VALUES (?, ?)",
                (role, content)
            )
            # Храним только последние 500 сообщений
            conn.execute(
                "DELETE FROM messages WHERE id NOT IN (SELECT id FROM messages ORDER BY id DESC LIMIT 500)"
            )

    def get_recent_messages(self, n: int = 10) -> list:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT role, content, created_at FROM messages ORDER BY id DESC LIMIT ?", (n,)
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    # ─── ОБУЧЕНИЕ ─────────────────────────────────────────────────────────────
    def learn(self, fact: str):
        """
        Запоминает новый факт о пользователе.
        Если факт уже известен — увеличивает уверенность.
        """
        with self._get_conn() as conn:
            existing = conn.execute(
                "SELECT id, count, confidence FROM learnings WHERE fact = ?", (fact,)
            ).fetchone()

            if existing:
                new_count = existing['count'] + 1
                new_conf  = min(1.0, existing['confidence'] + 0.1)
                conn.execute(
                    "UPDATE learnings SET count=?, confidence=?, updated_at=datetime('now','localtime') WHERE id=?",
                    (new_count, new_conf, existing['id'])
                )
            else:
                conn.execute(
                    "INSERT OR IGNORE INTO learnings (fact) VALUES (?)", (fact,)
                )
        log(f"🎓 Выучил: {fact}")

    def get_recent_learnings(self, n: int = 5) -> list[str]:
        """Возвращает самые уверенные факты о пользователе."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT fact FROM learnings ORDER BY confidence DESC, count DESC LIMIT ?", (n,)
            ).fetchall()
        return [r['fact'] for r in rows]

    def get_all_learnings(self) -> list:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT fact, confidence, count, updated_at FROM learnings ORDER BY confidence DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    # ─── ПРЕДПОЧТЕНИЯ ─────────────────────────────────────────────────────────
    def update_preference(self, key: str, value):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES (?, ?, datetime('now','localtime'))",
                (key, json.dumps(value, ensure_ascii=False))
            )

    def get_preferences(self) -> dict:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT key, value FROM preferences").fetchall()
        result = {}
        for r in rows:
            try:
                result[r['key']] = json.loads(r['value'])
            except:
                result[r['key']] = r['value']
        return result

    def get_preference(self, key: str, default=None):
        prefs = self.get_preferences()
        return prefs.get(key, default)

    # ─── СТАТИСТИКА ЗАПРОСОВ ──────────────────────────────────────────────────
    def track_query_frequency(self, intent: str):
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO query_stats (intent, count, last_used)
                VALUES (?, 1, datetime('now','localtime'))
                ON CONFLICT(intent) DO UPDATE SET
                    count    = count + 1,
                    last_used = datetime('now','localtime')
            """, (intent,))

    def get_top_intents(self, n: int = 3) -> list:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT intent, count FROM query_stats ORDER BY count DESC LIMIT ?", (n,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ─── НАСТРОЙКИ ────────────────────────────────────────────────────────────
    def save_settings(self, settings: dict):
        with self._get_conn() as conn:
            for k, v in settings.items():
                conn.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    (k, str(v))
                )

    def get_settings(self) -> dict:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {r['key']: r['value'] for r in rows}

    # ─── СТАТИСТИКА ───────────────────────────────────────────────────────────
    def get_stats(self) -> dict:
        with self._get_conn() as conn:
            memories  = conn.execute("SELECT COUNT(*) as c FROM messages").fetchone()['c']
            learnings = conn.execute("SELECT COUNT(*) as c FROM learnings").fetchone()['c']
            prefs     = conn.execute("SELECT COUNT(*) as c FROM preferences").fetchone()['c']
        return {
            "memories":  memories,
            "learnings": learnings,
            "preferences": prefs,
        }

    def clear_history(self):
        """Очистка истории (по запросу пользователя)."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM messages")
        log("🗑️ История очищена")

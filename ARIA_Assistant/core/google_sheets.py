"""
📊 GOOGLE SHEETS ИНТЕГРАЦИЯ
============================
Использует: gspread + google-auth
Установка: pip install gspread google-auth

НАСТРОЙКА (одноразово):
1. Google Cloud Console → создай проект
2. APIs → включи Google Sheets API
3. Credentials → Service Account → скачай JSON
4. Положи JSON как 'google_credentials.json'
5. Дай доступ к таблице (email из JSON)
"""

import json
import os
from datetime import datetime, date
from utils.logger import log

CREDS_PATH = os.path.join(os.path.dirname(__file__), "..", "google_credentials.json")


class GoogleSheetsManager:
    def __init__(self):
        self._gc     = None    # gspread client
        self._sheet  = None    # текущая таблица
        self._sheet_id = None

    def is_connected(self) -> bool:
        return self._sheet is not None

    def connect(self, sheet_id: str) -> bool:
        """Подключается к Google Sheets по ID таблицы."""
        try:
            import gspread
            from google.oauth2.service_account import Credentials

            scopes = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]

            if not os.path.exists(CREDS_PATH):
                log("⚠️ google_credentials.json не найден")
                return False

            creds = Credentials.from_service_account_file(CREDS_PATH, scopes=scopes)
            self._gc = gspread.authorize(creds)
            self._sheet = self._gc.open_by_key(sheet_id)
            self._sheet_id = sheet_id
            log(f"✅ Google Sheets подключён: {sheet_id}")
            self._ensure_worksheets()
            return True

        except ImportError:
            log("⚠️ gspread не установлен: pip install gspread google-auth")
            return False
        except Exception as e:
            log(f"❌ Google Sheets ошибка: {e}")
            return False

    def _ensure_worksheets(self):
        """Создаёт нужные листы если их нет."""
        if not self._sheet:
            return
        existing = [ws.title for ws in self._sheet.worksheets()]

        sheets_config = {
            "Расписание": ["Дата", "Время", "Задача", "Статус", "Обновлено"],
            "Заметки":    ["Дата", "Время", "Запись"],
            "Аналитика":  ["Дата", "Тип запроса", "Количество"],
        }

        for sheet_name, headers in sheets_config.items():
            if sheet_name not in existing:
                ws = self._sheet.add_worksheet(title=sheet_name, rows=1000, cols=len(headers))
                ws.update("A1", [headers])
                ws.format("A1:Z1", {"textFormat": {"bold": True}})
                log(f"✅ Создан лист: {sheet_name}")

    # ─── РАСПИСАНИЕ ───────────────────────────────────────────────────────────
    def sync_schedule(self, tasks: list) -> bool:
        """Синхронизирует задачи на сегодня в Google Sheets."""
        if not self._sheet:
            return False
        try:
            ws = self._sheet.worksheet("Расписание")
            today = date.today().strftime("%d.%m.%Y")
            now   = datetime.now().strftime("%H:%M")

            # Находим или создаём строки для сегодняшних задач
            existing = ws.get_all_values()
            today_rows = [i+1 for i, row in enumerate(existing[1:], 1) if row and row[0] == today]

            # Удаляем старые строки сегодня (в обратном порядке)
            for row_idx in reversed(today_rows):
                ws.delete_rows(row_idx)

            # Добавляем актуальные задачи
            new_rows = []
            for t in tasks:
                new_rows.append([
                    today,
                    t.get("time", ""),
                    t.get("task", ""),
                    "✓ Выполнено" if t.get("done") else "○ Активно",
                    now,
                ])

            if new_rows:
                ws.append_rows(new_rows)

            log(f"✅ Синхронизировано {len(new_rows)} задач в Google Sheets")
            return True

        except Exception as e:
            log(f"❌ Sync error: {e}")
            return False

    # ─── ЧТЕНИЕ ДАННЫХ ────────────────────────────────────────────────────────
    def read_data(self, worksheet: str = "Заметки", limit: int = 10) -> str:
        """Читает последние записи из таблицы."""
        if not self._sheet:
            return ""
        try:
            ws = self._sheet.worksheet(worksheet)
            rows = ws.get_all_values()
            if len(rows) <= 1:
                return "Таблица пуста"
            # Возвращаем последние N записей
            recent = rows[-limit:]
            return "\n".join([" | ".join(r) for r in recent])
        except Exception as e:
            log(f"❌ Read error: {e}")
            return ""

    # ─── ЗАПИСЬ ДАННЫХ ────────────────────────────────────────────────────────
    def append_row(self, values: list, worksheet: str = "Заметки") -> bool:
        """Добавляет строку в указанный лист."""
        if not self._sheet:
            return False
        try:
            ws = self._sheet.worksheet(worksheet)
            ws.append_row(values)
            log(f"✅ Записано в {worksheet}: {values}")
            return True
        except Exception as e:
            log(f"❌ Append error: {e}")
            return False

    # ─── АНАЛИТИКА ────────────────────────────────────────────────────────────
    def save_analytics(self, intent: str, count: int):
        """Сохраняет статистику использования в таблицу."""
        if not self._sheet:
            return
        try:
            ws = self._sheet.worksheet("Аналитика")
            ws.append_row([
                date.today().strftime("%d.%m.%Y"),
                intent,
                count,
            ])
        except:
            pass

    def get_sheet_url(self) -> str:
        """Возвращает URL таблицы."""
        if self._sheet_id:
            return f"https://docs.google.com/spreadsheets/d/{self._sheet_id}"
        return ""

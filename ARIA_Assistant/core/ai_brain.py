"""
🧠 AI BRAIN — Groq API + Internet Search + Learning
====================================================
Groq: бесплатный тир — 14 400 запросов/день, ~300 токен/сек
Модель: llama-3.3-70b-versatile (лучшее соотношение качество/скорость)
Поиск: DuckDuckGo (без API-ключа, полностью бесплатно)
"""

import json
import re
import os
import urllib.request
import urllib.parse
from datetime import datetime, date
from utils.logger import log


class AIBrain:
    def __init__(self, memory=None):
        self.memory = memory
        self._api_key = os.getenv("GROQ_API_KEY", "")
        self._history = []          # Контекст разговора
        self._max_history = 20      # Последние 20 сообщений
        self._groq_url = "https://api.groq.com/openai/v1/chat/completions"
        self._model = "llama-3.3-70b-versatile"

    def set_api_key(self, key: str):
        self._api_key = key.strip()

    # ─── ГЛАВНАЯ ТОЧКА ВХОДА ──────────────────────────────────────────────────
    def process(self, user_text: str, scheduler=None, sheets=None) -> str:
        """
        Обрабатывает запрос пользователя:
        1. Сохраняет в память
        2. Определяет нужен ли поиск в интернете
        3. Управляет расписанием / таблицами
        4. Генерирует ответ через Groq
        5. Обучается на паттернах
        """
        # 1. Сохранить входящий запрос
        if self.memory:
            self.memory.add_message("user", user_text)

        # 2. Определяем тип запроса
        intent = self._detect_intent(user_text)
        log(f"🎯 Намерение: {intent}")

        extra_context = ""

        # 3. Поиск в интернете если нужен
        if intent in ("search", "weather", "news", "facts"):
            search_results = self._web_search(user_text)
            if search_results:
                extra_context = f"\n\n[Данные из интернета]:\n{search_results}"

        # 4. Работа с расписанием
        if intent in ("add_task", "show_schedule", "delete_task", "build_plan"):
            return self._handle_schedule(user_text, intent, scheduler, sheets)

        # 5. Google Sheets
        if intent == "sheets":
            return self._handle_sheets(user_text, sheets)

        # 6. Получить персональный контекст из памяти
        personal_context = ""
        if self.memory:
            prefs = self.memory.get_preferences()
            learnings = self.memory.get_recent_learnings(5)
            if prefs:
                personal_context = f"\n[Предпочтения пользователя]: {json.dumps(prefs, ensure_ascii=False)}"
            if learnings:
                personal_context += f"\n[Что я узнал о пользователе]: {'; '.join(learnings)}"

        # 7. Генерируем ответ через Groq
        response = self._call_groq(user_text, extra_context + personal_context)

        # 8. Обучение — анализируем разговор
        if self.memory:
            self.memory.add_message("assistant", response)
            self._learn_from_interaction(user_text, response)

        return response

    # ─── ОПРЕДЕЛЕНИЕ НАМЕРЕНИЯ ────────────────────────────────────────────────
    def _detect_intent(self, text: str) -> str:
        text_lower = text.lower()

        schedule_add = ["добавь", "запиши", "запланируй", "поставь", "назначь", "создай встречу",
                        "напомни", "встреча", "созвон", "задача в", "в", "задачу"]
        schedule_show = ["расписание", "план", "что у меня", "покажи задачи", "сегодня"]
        schedule_del  = ["удали", "убери", "отмени задачу"]
        schedule_plan = ["составь план", "оптимальный план", "расставь задачи"]
        sheets_kw     = ["таблиц", "sheets", "гугл таблиц", "запиши в таблицу", "excel"]
        search_kw     = ["найди", "поищи", "погода", "новости", "что такое", "кто такой",
                         "когда", "где", "сколько стоит", "курс", "как сделать"]

        if any(w in text_lower for w in schedule_plan):  return "build_plan"
        if any(w in text_lower for w in schedule_del):   return "delete_task"
        if any(w in text_lower for w in schedule_show):  return "show_schedule"
        if any(w in text_lower for w in schedule_add) and re.search(r'\d{1,2}[:.,]\d{2}|\d{1,2} (час|утр|вечер|ночи|дня)', text_lower):
            return "add_task"
        if any(w in text_lower for w in sheets_kw):      return "sheets"
        if any(w in text_lower for w in search_kw):      return "search"
        return "chat"

    # ─── GROQ API ВЫЗОВ ───────────────────────────────────────────────────────
    def _call_groq(self, user_text: str, extra_context: str = "") -> str:
        if not self._api_key:
            return ("⚠️ Groq API ключ не настроен.\n"
                    "Зайди в Настройки → вставь бесплатный ключ с [b]console.groq.com[/b]")

        # Системный промпт с обучением
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        system_prompt = f"""Ты — ARIA, умный персональный голосовой ассистент. Сейчас: {now}.

СТИЛЬ ОТВЕТОВ:
- Краткие, чёткие ответы (для голоса — 1-3 предложения)
- Говори по-русски, тепло и профессионально
- Используй эмодзи уместно
- Если нужно — дай развёрнутый ответ

ТВОИ ВОЗМОЖНОСТИ:
✦ Управление расписанием и задачами
✦ Поиск информации в интернете в реальном времени  
✦ Работа с Google Таблицами
✦ Запоминание предпочтений пользователя
✦ Составление оптимального плана дня
{extra_context}"""

        # Добавляем сообщение в историю
        self._history.append({"role": "user", "content": user_text})
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        messages = [{"role": "system", "content": system_prompt}] + self._history

        try:
            payload = json.dumps({
                "model": self._model,
                "messages": messages,
                "max_tokens": 512,
                "temperature": 0.7,
                "stream": False,
            }).encode("utf-8")

            req = urllib.request.Request(
                self._groq_url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                }
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                answer = data["choices"][0]["message"]["content"].strip()

            # Сохраняем ответ в историю
            self._history.append({"role": "assistant", "content": answer})
            return answer

        except urllib.error.HTTPError as e:
            if e.code == 401:
                return "⚠️ Неверный Groq API ключ. Проверь в настройках."
            if e.code == 429:
                return "⚠️ Превышен лимит запросов Groq. Подожди минуту."
            return f"⚠️ Ошибка API: {e.code}"
        except Exception as e:
            log(f"❌ Groq error: {e}")
            return f"⚠️ Ошибка подключения: {str(e)}"

    # ─── ПОИСК В ИНТЕРНЕТЕ ────────────────────────────────────────────────────
    def _web_search(self, query: str, max_results: int = 3) -> str:
        """
        Поиск через DuckDuckGo Instant Answer API.
        Полностью бесплатно, без ключей.
        """
        try:
            # DuckDuckGo Instant Answers API
            encoded = urllib.parse.quote(query)
            url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"

            req = urllib.request.Request(url, headers={"User-Agent": "ARIA-Assistant/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            results = []

            # Основной ответ
            if data.get("AbstractText"):
                results.append(f"📖 {data['AbstractText'][:400]}")
                if data.get("AbstractSource"):
                    results.append(f"   — Источник: {data['AbstractSource']}")

            # Быстрый ответ
            if data.get("Answer"):
                results.append(f"⚡ {data['Answer']}")

            # Связанные темы
            for topic in data.get("RelatedTopics", [])[:2]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(f"• {topic['Text'][:200]}")

            if results:
                return "\n".join(results)

            # Fallback: поиск через HTML (парсинг)
            return self._ddg_html_search(query)

        except Exception as e:
            log(f"❌ Search error: {e}")
            return ""

    def _ddg_html_search(self, query: str) -> str:
        """Резервный поиск через DuckDuckGo HTML."""
        try:
            encoded = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded}"
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Android 13; Mobile) Chrome/120"
            })
            with urllib.request.urlopen(req, timeout=8) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            # Простое извлечение текста результатов
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
            clean = []
            for s in snippets[:3]:
                text = re.sub(r'<[^>]+>', '', s).strip()
                if text:
                    clean.append(f"• {text[:200]}")

            return "\n".join(clean) if clean else ""
        except:
            return ""

    # ─── УПРАВЛЕНИЕ РАСПИСАНИЕМ ───────────────────────────────────────────────
    def _handle_schedule(self, text: str, intent: str, scheduler, sheets) -> str:
        if scheduler is None:
            return "⚠️ Планировщик не инициализирован"

        if intent == "show_schedule":
            tasks = scheduler.get_today_tasks()
            if not tasks:
                return "📅 На сегодня задач нет. Скажи что добавить!"
            lines = [f"• {t['time']} — {t['task']}" + (" ✓" if t['done'] else "") for t in tasks]
            return "📅 Твоё расписание:\n" + "\n".join(lines)

        if intent == "add_task":
            # Извлекаем время и задачу
            time_match = re.search(
                r'(\d{1,2})[:\.,](\d{2})|(\d{1,2})\s*(час|утра|вечера|ночи|дня)',
                text.lower()
            )
            if time_match:
                if time_match.group(1):
                    t = f"{int(time_match.group(1)):02d}:{time_match.group(2)}"
                else:
                    h = int(time_match.group(3))
                    suffix = time_match.group(4)
                    if suffix in ("вечера", "вечер") and h < 12: h += 12
                    if suffix in ("утра", "утро") and h == 12: h = 0
                    t = f"{h:02d}:00"

                # Название задачи — убираем время и ключевые слова
                task_name = re.sub(
                    r'(добавь|запиши|поставь|напомни|задачу|задание|встречу|в\s+\d[\d:.,]*\s*(?:час|утра|вечера|ночи|дня)?|\d{1,2}[:.]\d{2})',
                    '', text, flags=re.IGNORECASE
                ).strip().strip('- ').capitalize()

                if not task_name:
                    task_name = "Задача"

                task_id = scheduler.add_task(t, task_name)

                # Синхронизируем с Google Sheets если подключено
                if sheets and sheets.is_connected():
                    sheets.sync_schedule(scheduler.get_today_tasks())

                return f"✅ Добавил: {t} — {task_name}"
            else:
                # Если время не найдено — просим уточнить через AI
                return self._call_groq(
                    text,
                    "\n[Пользователь хочет добавить задачу но не указал время. Уточни время.]"
                )

        if intent == "delete_task":
            num_match = re.search(r'номер\s*(\d+)|задачу\s*(\d+)|#(\d+)', text.lower())
            if num_match:
                task_id = int(next(g for g in num_match.groups() if g))
                scheduler.delete_task(task_id)
                return f"🗑️ Задача #{task_id} удалена"
            return "Укажи номер задачи, например: «удали задачу 3»"

        if intent == "build_plan":
            tasks = scheduler.get_today_tasks()
            plan_text = "\n".join([f"- {t['time']}: {t['task']}" for t in tasks]) if tasks else "задач нет"
            return self._call_groq(
                f"Составь оптимальный план дня. Задачи: {plan_text}",
                "\n[Дай краткий, структурированный план с советами по продуктивности]"
            )

        return self._call_groq(text)

    # ─── GOOGLE SHEETS ────────────────────────────────────────────────────────
    def _handle_sheets(self, text: str, sheets) -> str:
        if sheets is None or not sheets.is_connected():
            return ("⚠️ Google Таблицы не подключены.\n"
                    "Зайди в Настройки → укажи ID таблицы")

        text_lower = text.lower()

        # Чтение
        if any(w in text_lower for w in ["прочитай", "покажи", "что в таблице", "данные"]):
            data = sheets.read_data()
            if data:
                return f"📊 Данные из таблицы:\n{data[:500]}"
            return "📊 Таблица пуста или нет доступа"

        # Запись
        if any(w in text_lower for w in ["запиши", "добавь в таблицу", "сохрани"]):
            # Убираем ключевые слова
            value = re.sub(r'запиши|добавь в таблицу|сохрани в таблицу|в таблицу', '', text, flags=re.IGNORECASE).strip()
            ok = sheets.append_row([datetime.now().strftime("%d.%m.%Y %H:%M"), value])
            return f"✅ Записал в таблицу: {value}" if ok else "⚠️ Ошибка записи"

        return self._call_groq(text)

    # ─── ОБУЧЕНИЕ НА ВЗАИМОДЕЙСТВИЯХ ─────────────────────────────────────────
    def _learn_from_interaction(self, user_text: str, response: str):
        """
        Анализирует паттерны поведения и сохраняет предпочтения.
        Это и есть система обучения — накопительное персонализированное знание.
        """
        if not self.memory:
            return

        text_lower = user_text.lower()

        # Паттерн 1: Предпочтения по времени
        time_match = re.search(r'(\d{1,2})[:.]\d{2}', user_text)
        if time_match and any(w in text_lower for w in ["встреча", "созвон", "обед", "спорт"]):
            hour = int(time_match.group(1))
            period = "утро" if hour < 12 else ("день" if hour < 17 else "вечер")
            activity = next((w for w in ["встреча", "спорт", "обед", "тренировка"] if w in text_lower), None)
            if activity:
                self.memory.learn(f"Предпочитает {activity} в {period} (~{time_match.group(0)})")

        # Паттерн 2: Интересы пользователя
        interests = {
            "спорт": ["спорт", "тренировка", "фитнес", "бег", "зал"],
            "работа": ["работа", "проект", "дедлайн", "встреча", "презентация"],
            "здоровье": ["врач", "аптека", "здоровье", "лекарство"],
            "учёба": ["учёба", "курс", "изучить", "книга", "читать"],
        }
        for category, keywords in interests.items():
            if any(k in text_lower for k in keywords):
                self.memory.update_preference(f"interest_{category}", "high")

        # Паттерн 3: Стиль общения
        if len(user_text) < 15:
            self.memory.update_preference("communication_style", "brief")
        elif len(user_text) > 80:
            self.memory.update_preference("communication_style", "detailed")

        # Паттерн 4: Частые запросы
        self.memory.track_query_frequency(self._detect_intent(user_text))

# 🤖 ARIA — AI Personal Assistant
### Голосовой ИИ-ассистент | Android APK | Python + Kivy

---

## 🎯 ВОЗМОЖНОСТИ

| Функция | Описание | Статус |
|---------|----------|--------|
| 🎙️ Голосовое управление | Android SpeechRecognizer (нативный) | ✅ |
| 🧠 ИИ с интернетом | Groq API, Llama 3.3-70B, 14400 req/день бесплатно | ✅ |
| 🔍 Поиск в интернете | DuckDuckGo Instant Answers (без ключа) | ✅ |
| 📅 Расписание | Голосовое добавление, просмотр, удаление задач | ✅ |
| 📊 Google Таблицы | Чтение, запись, синхронизация расписания | ✅ |
| 🎓 Обучение | Запоминает привычки, предпочтения, стиль | ✅ |
| 💬 Контекст | Помнит историю разговора (500 сообщений) | ✅ |
| 🌙 Тёмная тема | Cyberpunk UI, AMOLED-дружественный | ✅ |

---

## 🏗️ АРХИТЕКТУРА

```
┌─────────────────────────────────────────────────────────┐
│                     ARIA Android APK                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  📱 Kivy + KivyMD UI (main.py)                          │
│     ↕                                                   │
│  🎙️ VoiceEngine ←→ Android SpeechRecognizer / Whisper   │
│     ↕                                                   │
│  🧠 AIBrain                                              │
│     ├── 🌐 Groq API (Llama 3.3-70B) ← интернет          │
│     ├── 🔍 DuckDuckGo Search ← интернет                 │
│     ├── 📅 Scheduler (SQLite)                            │
│     ├── 📊 Google Sheets API ← интернет                 │
│     └── 🎓 MemorySystem (SQLite) ← обучение             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## ⚡ БЫСТРЫЙ СТАРТ

### Шаг 1 — Получи бесплатный Groq API ключ
```
1. Зайди на https://console.groq.com
2. Sign Up (бесплатно)
3. API Keys → Create API Key
4. Скопируй ключ (начинается с "gsk_...")
```
> **Groq бесплатный тир**: 14 400 запросов/день, модель Llama 3.3-70B

### Шаг 2 — Настрой Google Sheets (опционально)
```
1. https://console.cloud.google.com → новый проект
2. APIs → Google Sheets API → включить
3. Credentials → Service Account → создать → скачать JSON
4. Замени содержимое google_credentials.json
5. В своей Google Таблице: Поделиться → добавь email из JSON
6. Скопируй ID таблицы из URL:
   https://docs.google.com/spreadsheets/d/[ЭТО_И_ЕСТЬ_ID]/edit
```

### Шаг 3 — Сборка APK

#### На Linux/Mac:
```bash
# Установи buildozer
pip install buildozer cython

# Установи зависимости Android
sudo apt-get install -y git zip unzip openjdk-17-jdk python3-pip \
    autoconf libtool pkg-config zlib1g-dev libncurses5-dev \
    libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev

# В папке проекта:
cd ai_assistant_apk/
buildozer android debug

# APK будет в: bin/ariaassistant-1.0.0-arm64-v8a-debug.apk
```

#### На Windows (через WSL2):
```bash
# Установи WSL2 с Ubuntu 22.04, затем те же команды выше
wsl --install -d Ubuntu-22.04
```

#### Онлайн (Google Colab — бесплатно):
```python
# Создай новый Colab ноутбук и выполни:
!pip install buildozer cython
!apt-get install -y git zip unzip openjdk-17-jdk
# Загрузи папку проекта в Colab, затем:
!buildozer android debug
# Скачай APK из папки bin/
```

### Шаг 4 — Установка на телефон
```
1. На телефоне: Настройки → Безопасность → Неизвестные источники → Разрешить
2. Перенеси APK на телефон (USB / Google Drive / Telegram себе)
3. Открой файл APK → Установить
4. Запусти ARIA → Настройки → вставь Groq API ключ
```

---

## 📱 КАК ПОЛЬЗОВАТЬСЯ

### Голосовые команды:
```
"Добавь встречу в 10:00 с командой"      → создаст задачу
"Что у меня запланировано на сегодня?"   → покажет расписание
"Составь план дня"                        → оптимизирует задачи
"Найди курс евро"                         → поиск в интернете
"Запиши в таблицу: потратил 500 рублей"  → Google Sheets
"Удали задачу 2"                          → удалит задачу
"Что такое квантовые компьютеры?"         → ИИ + поиск
```

### Обучение — что запоминает ARIA:
```
• В какое время ты обычно делаешь разные задачи
• Твои интересы (работа, спорт, здоровье...)
• Стиль общения (краткий или подробный)
• Частые запросы (адаптирует приоритеты)
• История разговоров (контекст)
```

---

## 📁 СТРУКТУРА ПРОЕКТА

```
ai_assistant_apk/
├── main.py                    # 🚀 Точка входа + Kivy UI
├── buildozer.spec             # 📦 Конфигурация Android сборки
├── requirements.txt           # 📋 Python зависимости
├── google_credentials.json    # 🔑 Google API (заполни своими данными)
│
├── core/
│   ├── ai_brain.py            # 🧠 ИИ + Groq + поиск в интернете
│   ├── voice_engine.py        # 🎙️ STT + TTS (Android + Desktop)
│   ├── memory.py              # 🎓 Память + система обучения
│   ├── scheduler.py           # 📅 Управление задачами
│   └── google_sheets.py       # 📊 Google Sheets интеграция
│
├── utils/
│   └── logger.py              # 🪵 Логирование
│
└── data/                      # 📂 Создаётся автоматически
    ├── aria_memory.db         # База данных (SQLite)
    └── aria.log               # Логи приложения
```

---

## 🔒 ПРИВАТНОСТЬ

| Данные | Где хранятся |
|--------|-------------|
| История разговоров | Только на твоём телефоне (SQLite) |
| Задачи и расписание | Только на твоём телефоне |
| Предпочтения | Только на твоём телефоне |
| Голосовые запросы | Обрабатываются Android локально |
| Запросы к ИИ | Отправляются в Groq (как обычный чат-запрос) |
| Google Sheets | Твой аккаунт Google |

---

## 🛠️ ТРЕБОВАНИЯ

| | Минимум | Рекомендуется |
|---|---|---|
| Android | 8.0 (API 26) | 10+ |
| RAM | 2 GB | 4 GB |
| Интернет | Нужен для ИИ/поиска | WiFi или 4G |
| Микрофон | Любой | Встроенный |

---

## 🚀 ДАЛЬНЕЙШЕЕ РАЗВИТИЕ

- **Wake Word** "Эй, ARIA" → Picovoice Porcupine (бесплатный тир)
- **Уведомления** → plyer.notification (уже подключён)
- **Умный дом** → Home Assistant API
- **Музыка** → Spotify / VLC API
- **Email** → Gmail API
- **Telegram бот** → python-telegram-bot

---

*ARIA v1.0 | Март 2026 | Полностью бесплатный стек*

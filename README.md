# 🤖 Jarvis — AI Content Autopilot

Telegram-бот + Ruflo Swarm для автоматического создания и публикации контента.
5 AI-агентов (Scout, Writer, Designer, Analyst, Reviewer), управление через меню в Telegram, деплой на Railway 24/7.

## Что умеет

- 📝 **Генерация постов** по любой теме (Claude API) — 6 стилей на выбор
- 📢 **Публикация** в Telegram-каналы и VK одной кнопкой
- 🔍 **Парсинг** сайтов, RSS, Telegram-каналов
- 📰 **Дайджесты** из собранных источников
- 🤖 **Ruflo Swarm** — 5 AI-агентов работают параллельно над задачей
- 🧠 **AI Память** — бот помнит предпочтения между сессиями
- ⏰ **Расписание** — автопубликации по cron 24/7
- 💬 **Свободный чат** — любое сообщение → ответ Claude
- 📊 **Аналитика и контент-планы** через Ruflo Analyst

## Быстрый старт (10 минут)

### Шаг 1: Получите ключи

1. **Telegram Bot Token**: откройте @BotFather в Telegram → `/newbot` → скопируйте токен
2. **Anthropic API Key**: зайдите на [console.anthropic.com](https://console.anthropic.com) → API Keys → Create
3. **Ваш Telegram ID**: напишите @userinfobot в Telegram → он вернёт ваш числовой ID

### Шаг 2: Форкните репозиторий

Нажмите **Fork** на GitHub (или создайте новый репо и запушьте код).

### Шаг 3: Деплой на Railway

1. Зайдите на [railway.com](https://railway.com) → войдите через GitHub
2. **New Project** → **Deploy from GitHub repo** → выберите этот репозиторий
3. Перейдите в **Variables** и добавьте:

```
TELEGRAM_BOT_TOKEN=ваш_токен_бота
ANTHROPIC_API_KEY=sk-ant-ваш_ключ
OWNER_TELEGRAM_ID=ваш_числовой_id
```

4. (Опционально) Добавьте каналы:
```
TELEGRAM_CHANNEL_ID=@ваш_канал
VK_API_TOKEN=ваш_vk_токен
VK_GROUP_ID=id_группы
```

5. Railway автоматически задеплоит. Через ~2 минуты бот заработает.

### Шаг 4: Проверьте

Откройте Telegram → найдите вашего бота → `/start`

## Команды бота

| Команда | Описание |
|---------|----------|
| `/post <тема>` | Создать пост + кнопки публикации |
| `/draft <тема>` | Только черновик |
| `/parse <url>` | Спарсить сайт/RSS/Telegram-канал |
| `/digest` | Дайджест из спарсенных источников |
| `/cron 10:00 описание` | Добавить задачу по расписанию |
| `/schedule` | Управление расписанием |
| `/channels` | Настройки каналов |
| `/stats` | Статистика |
| Любой текст | Свободный чат с Claude |

## Примеры использования

```
/post AI-тренды марта 2026
/parse https://habr.com/ru/flows/develop/
/parse https://t.me/durov
/digest
/cron 09:00 Собрать новости AI и опубликовать дайджест
/cron 18:00 Написать пост про продуктивность
```

## Стоимость

- **Railway**: ~$5/мес (Hobby план)
- **Claude API**: ~$5-20/мес (зависит от активности)
- **Итого**: ~$10-25/мес за полностью автоматический контент-менеджер

## Структура

```
jarvis/
├── src/
│   ├── index.js              # Бот + меню (кнопки, без команд)
│   ├── ruflo-agent.js        # Ruflo Swarm — 5 агентов, память, планы
│   ├── content-generator.js  # Генерация контента через Claude
│   ├── publisher.js          # Публикация в TG / VK
│   ├── parser.js             # Парсинг сайтов, RSS, TG-каналов
│   ├── scheduler.js          # Cron-планировщик
│   ├── database.js           # SQLite (черновики, память, задачи)
│   └── menu.js               # Утилиты навигации
├── Dockerfile
├── package.json
├── .env.example
└── README.md
```

## Лицензия

MIT

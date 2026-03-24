# Dockerfile для Claude Telegram Bot
# Базовый образ: Python 3.12 slim + ffmpeg для обработки аудио

FROM python:3.12-slim

# Метаданные образа
LABEL maintainer="Claude Telegram Bot"
LABEL description="AI-powered Telegram bot based on Claude API"

# Устанавливаем системные зависимости
# ffmpeg нужен для конвертации аудио (OGG → MP3 и т.д.)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем файлы зависимостей отдельно для кэширования слоёв Docker
COPY requirements.txt .

# Устанавливаем Python-зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Создаём непривилегированного пользователя для безопасности
RUN useradd --create-home --shell /bin/bash botuser && \
    chown -R botuser:botuser /app

USER botuser

# Переменные окружения по умолчанию
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Точка входа
CMD ["python", "bot.py"]

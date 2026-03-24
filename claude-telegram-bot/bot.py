"""
bot.py — Точка входа Telegram бота на базе Claude AI.
Обрабатывает текстовые и голосовые сообщения, команды управления.
Только OWNER_TELEGRAM_ID имеет доступ к боту.
"""

import asyncio
import logging
import os
from functools import wraps
from typing import Callable

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, Voice
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from orchestrator import Orchestrator

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Переменные окружения
BOT_TOKEN: str = os.environ["BOT_TOKEN"]
OWNER_TELEGRAM_ID: int = int(os.environ["OWNER_TELEGRAM_ID"])

# Инициализация бота и диспетчера
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()
orchestrator = Orchestrator()


def owner_only(handler: Callable) -> Callable:
    """
    Декоратор: разрешает выполнение хендлера только владельцу бота.
    Все остальные пользователи получают отказ без объяснений.
    """
    @wraps(handler)
    async def wrapper(message: Message, *args, **kwargs):
        if message.from_user and message.from_user.id == OWNER_TELEGRAM_ID:
            return await handler(message, *args, **kwargs)
        logger.warning(
            "Отклонён запрос от пользователя %s (не владелец)",
            message.from_user.id if message.from_user else "unknown",
        )
        # Молча игнорируем — не раскрываем существование бота
    return wrapper


def split_message(text: str, limit: int = 4096) -> list[str]:
    """
    Разбивает длинный текст на части для отправки в Telegram.
    Лимит сообщения — 4096 символов.
    """
    if len(text) <= limit:
        return [text]

    parts: list[str] = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break
        # Ищем ближайший перенос строки перед лимитом
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        parts.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return parts


@dp.message(Command("start"))
@owner_only
async def cmd_start(message: Message) -> None:
    """Приветственное сообщение и краткая справка."""
    text = (
        "<b>Привет! Я Claude AI Bot.</b>\n\n"
        "Отправь мне текстовое или голосовое сообщение — я отвечу с помощью Claude.\n\n"
        "<b>Доступные команды:</b>\n"
        "/start — это сообщение\n"
        "/help — подробная справка\n"
        "/status — статус системы\n"
        "/stop — остановить бота\n"
    )
    await message.answer(text)


@dp.message(Command("help"))
@owner_only
async def cmd_help(message: Message) -> None:
    """Подробная справка по возможностям бота."""
    text = (
        "<b>Справка по Claude AI Bot</b>\n\n"
        "<b>Возможности:</b>\n"
        "• Отправь текст — Claude ответит с учётом контекста\n"
        "• Отправь голосовое — транскрибирую через Groq Whisper и отвечу\n"
        "• Генерация изображений через Replicate\n"
        "• Парсинг сайтов и Telegram-каналов\n"
        "• Публикация постов в канал по расписанию\n"
        "• Генерация видео через Replicate\n"
        "• Синтез речи через Microsoft Edge TTS\n\n"
        "<b>Примеры запросов:</b>\n"
        "• «Сгенерируй изображение кота в стиле аниме»\n"
        "• «Разбери сайт https://example.com»\n"
        "• «Опубликуй в канал: Привет мир!»\n"
        "• «Запланируй пост на завтра в 10:00: ...»\n"
        "• «Синтезируй речь: Привет»\n\n"
        "<b>Команды:</b>\n"
        "/status — статус агентов и расписания\n"
        "/stop — завершить работу бота\n"
    )
    await message.answer(text)


@dp.message(Command("status"))
@owner_only
async def cmd_status(message: Message) -> None:
    """Показывает статус всех агентов и запланированных задач."""
    try:
        status = await orchestrator.get_status()
        await message.answer(status)
    except Exception as exc:
        logger.error("Ошибка получения статуса: %s", exc)
        await message.answer(f"<b>Ошибка статуса:</b> <code>{exc}</code>")


@dp.message(Command("stop"))
@owner_only
async def cmd_stop(message: Message) -> None:
    """Корректная остановка бота."""
    await message.answer("<b>Останавливаю бота...</b>")
    logger.info("Бот остановлен по команде владельца")
    await bot.session.close()
    asyncio.get_event_loop().stop()


@dp.message(F.voice)
@owner_only
async def handle_voice(message: Message) -> None:
    """
    Обработчик голосовых сообщений.
    Скачивает OGG, транскрибирует через Groq Whisper, передаёт в оркестратор.
    """
    thinking_msg = await message.answer("<i>Распознаю голосовое сообщение...</i>")
    try:
        voice: Voice = message.voice
        file = await bot.get_file(voice.file_id)
        file_path = file.file_path

        # Скачиваем голосовой файл
        ogg_bytes = await bot.download_file(file_path)
        raw_bytes = ogg_bytes.read()

        # Транскрибируем через VoiceAgent
        transcript = await orchestrator.transcribe_voice(raw_bytes)
        if not transcript:
            await thinking_msg.edit_text("<b>Не удалось распознать голосовое сообщение.</b>")
            return

        await thinking_msg.edit_text(
            f"<i>Распознано:</i> <code>{transcript}</code>\n<i>Обрабатываю...</i>"
        )

        # Передаём текст в оркестратор
        response = await orchestrator.process_message(transcript, message.from_user.id)
        await thinking_msg.delete()

        for part in split_message(response):
            await message.answer(part)

    except Exception as exc:
        logger.error("Ошибка обработки голосового: %s", exc)
        await thinking_msg.edit_text(f"<b>Ошибка обработки голосового:</b> <code>{exc}</code>")


@dp.message(F.text)
@owner_only
async def handle_text(message: Message) -> None:
    """
    Обработчик текстовых сообщений.
    Передаёт текст в оркестратор и возвращает ответ Claude.
    """
    thinking_msg = await message.answer("<i>Думаю...</i>")
    try:
        response = await orchestrator.process_message(
            message.text, message.from_user.id
        )
        await thinking_msg.delete()

        for part in split_message(response):
            await message.answer(part)

    except Exception as exc:
        logger.error("Ошибка обработки текста: %s", exc)
        await thinking_msg.edit_text(f"<b>Ошибка:</b> <code>{exc}</code>")


async def on_startup() -> None:
    """Инициализация при старте бота."""
    logger.info("Инициализация оркестратора...")
    await orchestrator.setup(bot)
    logger.info("Бот запущен. Owner ID: %s", OWNER_TELEGRAM_ID)

    # Уведомляем владельца
    try:
        await bot.send_message(
            OWNER_TELEGRAM_ID,
            "<b>Бот запущен и готов к работе!</b>\n/help — список команд",
        )
    except Exception as exc:
        logger.warning("Не удалось отправить уведомление о запуске: %s", exc)


async def on_shutdown() -> None:
    """Завершение работы бота."""
    logger.info("Завершение работы бота...")
    await orchestrator.shutdown()
    await bot.session.close()


async def main() -> None:
    """Главная функция запуска бота."""
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Запуск поллинга...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())

"""
agents/parser.py — Агент парсинга сайтов и Telegram-каналов.
Использует aiohttp + BeautifulSoup4 для сайтов и Telethon для TG-каналов.
"""

import logging
import os
from typing import Any

import aiohttp
from aiogram import Bot
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# User-Agent для HTTP-запросов
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}


class ParserAgent:
    """
    Агент для парсинга веб-сайтов и Telegram-каналов.
    Поддерживаемые инструменты: parse_website, parse_tg_channel.
    """

    TOOLS = ["parse_website", "parse_tg_channel"]

    def __init__(self) -> None:
        """Инициализация агента."""
        self.bot: Bot | None = None
        self.telethon_client = None
        self._telethon_available = False

    async def setup(self, bot: Bot) -> None:
        """
        Настройка агента. Инициализирует Telethon если доступны credentials.
        """
        self.bot = bot

        api_id = os.environ.get("TELETHON_API_ID")
        api_hash = os.environ.get("TELETHON_API_HASH")
        phone = os.environ.get("TELETHON_PHONE")

        if api_id and api_hash:
            try:
                from telethon import TelegramClient

                self.telethon_client = TelegramClient(
                    "session_bot",
                    int(api_id),
                    api_hash,
                )
                await self.telethon_client.start(phone=phone)
                self._telethon_available = True
                logger.info("Telethon клиент инициализирован")
            except Exception as exc:
                logger.warning("Telethon недоступен: %s", exc)
                self._telethon_available = False
        else:
            logger.info("TELETHON_API_ID/HASH не настроены — парсинг TG-каналов недоступен")

        logger.info("ParserAgent инициализирован")

    async def shutdown(self) -> None:
        """Завершение Telethon-сессии."""
        if self.telethon_client and self._telethon_available:
            try:
                await self.telethon_client.disconnect()
                logger.info("Telethon отключён")
            except Exception as exc:
                logger.error("Ошибка отключения Telethon: %s", exc)

    async def execute(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Выполняет инструмент агента.

        Параметры:
            tool_name: название инструмента
            params: параметры инструмента

        Возвращает dict с ключами: data, images, documents
        """
        try:
            if tool_name == "parse_website":
                return await self._parse_website(params)
            elif tool_name == "parse_tg_channel":
                return await self._parse_tg_channel(params)
            else:
                return {
                    "data": f"ParserAgent: неизвестный инструмент '{tool_name}'",
                    "images": [],
                    "documents": [],
                }
        except Exception as exc:
            logger.error("ParserAgent.execute('%s') ошибка: %s", tool_name, exc)
            return {
                "data": f"Ошибка ParserAgent при выполнении '{tool_name}': {exc}",
                "images": [],
                "documents": [],
            }

    async def _parse_website(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Парсит веб-сайт и возвращает текстовое содержимое.
        Параметры: url (str), selector (str, опционально).
        """
        url = params.get("url", "")
        selector = params.get("selector", "")

        if not url:
            return {"data": "Ошибка: URL не указан", "images": [], "documents": []}

        # Добавляем схему если отсутствует
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            async with aiohttp.ClientSession(headers=DEFAULT_HEADERS) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    response.raise_for_status()
                    content_type = response.content_type or ""

                    if "html" not in content_type and "text" not in content_type:
                        return {
                            "data": f"Неподдерживаемый тип контента: {content_type}",
                            "images": [],
                            "documents": [],
                        }

                    html = await response.text(errors="replace")

            soup = BeautifulSoup(html, "html.parser")

            # Удаляем ненужные теги
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "ads"]):
                tag.decompose()

            if selector:
                elements = soup.select(selector)
                if elements:
                    text = "\n\n".join(el.get_text(separator="\n", strip=True) for el in elements)
                else:
                    text = f"Элементы по селектору '{selector}' не найдены"
            else:
                # Пытаемся найти основной контент
                main = (
                    soup.find("main")
                    or soup.find("article")
                    or soup.find(id="content")
                    or soup.find(class_="content")
                    or soup.find("body")
                )
                text = main.get_text(separator="\n", strip=True) if main else soup.get_text(separator="\n", strip=True)

            # Убираем лишние пустые строки
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = "\n".join(lines)

            # Ограничиваем размер
            if len(text) > 8000:
                text = text[:8000] + "\n\n[... текст обрезан до 8000 символов ...]"

            title = soup.title.string.strip() if soup.title else url
            result_text = f"<b>Сайт:</b> {url}\n<b>Заголовок:</b> {title}\n\n{text}"

            logger.info("parse_website: %s — %d символов", url, len(text))
            return {"data": result_text, "images": [], "documents": []}

        except aiohttp.ClientResponseError as exc:
            logger.error("HTTP ошибка при парсинге %s: %s", url, exc)
            return {
                "data": f"HTTP ошибка {exc.status}: {exc.message}",
                "images": [],
                "documents": [],
            }
        except aiohttp.ClientError as exc:
            logger.error("Ошибка соединения при парсинге %s: %s", url, exc)
            return {
                "data": f"Ошибка соединения: {exc}",
                "images": [],
                "documents": [],
            }

    async def _parse_tg_channel(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Получает последние посты из Telegram-канала через Telethon.
        Параметры: channel (str), limit (int, по умолчанию 10).
        """
        channel = params.get("channel", "").strip().lstrip("@")
        limit = min(params.get("limit", 10), 50)  # Максимум 50 постов

        if not channel:
            return {"data": "Ошибка: канал не указан", "images": [], "documents": []}

        if not self._telethon_available or not self.telethon_client:
            return {
                "data": (
                    "Парсинг TG-каналов недоступен: TELETHON_API_ID/HASH не настроены. "
                    "Добавьте переменные окружения TELETHON_API_ID, TELETHON_API_HASH, TELETHON_PHONE."
                ),
                "images": [],
                "documents": [],
            }

        try:
            entity = await self.telethon_client.get_entity(channel)
            messages = await self.telethon_client.get_messages(entity, limit=limit)

            if not messages:
                return {
                    "data": f"Канал @{channel}: постов не найдено",
                    "images": [],
                    "documents": [],
                }

            posts = []
            for msg in messages:
                if not msg.text:
                    continue
                date_str = msg.date.strftime("%Y-%m-%d %H:%M") if msg.date else "неизвестно"
                post_text = msg.text[:500] + ("..." if len(msg.text) > 500 else "")
                posts.append(f"[{date_str}] {post_text}")

            result_text = f"<b>Канал:</b> @{channel}\n<b>Постов:</b> {len(posts)}\n\n"
            result_text += "\n\n---\n\n".join(posts)

            if len(result_text) > 8000:
                result_text = result_text[:8000] + "\n\n[... обрезано ...]"

            logger.info("parse_tg_channel: @%s — %d постов", channel, len(posts))
            return {"data": result_text, "images": [], "documents": []}

        except Exception as exc:
            logger.error("Ошибка парсинга канала @%s: %s", channel, exc)
            return {
                "data": f"Ошибка парсинга канала @{channel}: {exc}",
                "images": [],
                "documents": [],
            }

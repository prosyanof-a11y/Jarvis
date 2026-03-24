"""
agents/publisher.py — Агент публикации контента.
Публикует посты в Telegram-канал немедленно или по расписанию через APScheduler.
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Any

from aiogram import Bot
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore

logger = logging.getLogger(__name__)


class PublisherAgent:
    """
    Агент для публикации контента в Telegram-канал.
    Поддерживаемые инструменты: publish_now, schedule_post, list_scheduled, cancel_scheduled.
    """

    TOOLS = ["publish_now", "schedule_post", "list_scheduled", "cancel_scheduled"]

    def __init__(self) -> None:
        """Инициализация агента."""
        self.bot: Bot | None = None
        self.channel_id: str = ""
        self.scheduler: AsyncIOScheduler | None = None

    async def setup(self, bot: Bot) -> None:
        """
        Настройка агента. Инициализирует планировщик APScheduler.
        """
        self.bot = bot
        self.channel_id = os.environ.get("CHANNEL_ID", "")

        jobstores = {"default": MemoryJobStore()}
        self.scheduler = AsyncIOScheduler(jobstores=jobstores)
        self.scheduler.start()

        logger.info(
            "PublisherAgent инициализирован. Канал: %s",
            self.channel_id or "не настроен",
        )

    async def shutdown(self) -> None:
        """Остановка планировщика."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Планировщик остановлен")

    async def execute(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Выполняет инструмент агента.

        Параметры:
            tool_name: название инструмента
            params: параметры инструмента

        Возвращает dict с ключами: data, images, documents
        """
        try:
            if tool_name == "publish_now":
                return await self._publish_now(params)
            elif tool_name == "schedule_post":
                return await self._schedule_post(params)
            elif tool_name == "list_scheduled":
                return await self._list_scheduled(params)
            elif tool_name == "cancel_scheduled":
                return await self._cancel_scheduled(params)
            else:
                return {
                    "data": f"PublisherAgent: неизвестный инструмент '{tool_name}'",
                    "images": [],
                    "documents": [],
                }
        except Exception as exc:
            logger.error("PublisherAgent.execute('%s') ошибка: %s", tool_name, exc)
            return {
                "data": f"Ошибка PublisherAgent при выполнении '{tool_name}': {exc}",
                "images": [],
                "documents": [],
            }

    async def _publish_now(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Немедленно публикует пост в Telegram-канал.
        Параметры: text (str), image_url (str, опционально).
        """
        text = params.get("text", "")
        image_url = params.get("image_url", "")

        if not text:
            return {"data": "Ошибка: текст поста не указан", "images": [], "documents": []}

        if not self.channel_id:
            return {
                "data": "Ошибка: CHANNEL_ID не настроен",
                "images": [],
                "documents": [],
            }

        if not self.bot:
            return {"data": "Ошибка: бот не инициализирован", "images": [], "documents": []}

        try:
            if image_url:
                await self.bot.send_photo(
                    chat_id=self.channel_id,
                    photo=image_url,
                    caption=text,
                    parse_mode=ParseMode.HTML,
                )
            else:
                await self.bot.send_message(
                    chat_id=self.channel_id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                )

            logger.info("publish_now: пост опубликован в %s", self.channel_id)
            return {
                "data": f"Пост успешно опубликован в канал {self.channel_id}",
                "images": [],
                "documents": [],
            }

        except Exception as exc:
            logger.error("Ошибка публикации в канал: %s", exc)
            return {
                "data": f"Ошибка публикации: {exc}",
                "images": [],
                "documents": [],
            }

    async def _schedule_post(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Планирует публикацию поста на указанное время.
        Параметры: text (str), scheduled_time (str ISO 8601), image_url (str, опционально).
        """
        text = params.get("text", "")
        scheduled_time_str = params.get("scheduled_time", "")
        image_url = params.get("image_url", "")

        if not text:
            return {"data": "Ошибка: текст поста не указан", "images": [], "documents": []}

        if not scheduled_time_str:
            return {"data": "Ошибка: время публикации не указано", "images": [], "documents": []}

        if not self.scheduler:
            return {"data": "Ошибка: планировщик не инициализирован", "images": [], "documents": []}

        try:
            # Парсим время публикации
            if "T" in scheduled_time_str:
                scheduled_time = datetime.fromisoformat(scheduled_time_str)
            else:
                # Пробуем разные форматы
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M"]:
                    try:
                        scheduled_time = datetime.strptime(scheduled_time_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    return {
                        "data": f"Неверный формат времени: '{scheduled_time_str}'. Используй ISO 8601 (2024-01-15T10:00:00)",
                        "images": [],
                        "documents": [],
                    }

            now = datetime.now()
            if scheduled_time <= now:
                return {
                    "data": f"Время публикации {scheduled_time_str} уже прошло",
                    "images": [],
                    "documents": [],
                }

            job_id = f"post_{uuid.uuid4().hex[:8]}"

            self.scheduler.add_job(
                func=self._send_scheduled_post,
                trigger="date",
                run_date=scheduled_time,
                id=job_id,
                args=[text, image_url],
                name=f"Пост: {text[:50]}...",
            )

            logger.info("schedule_post: запланировано на %s, job_id=%s", scheduled_time, job_id)
            return {
                "data": (
                    f"Пост запланирован на {scheduled_time.strftime('%d.%m.%Y %H:%M')}\n"
                    f"ID задачи: <code>{job_id}</code>"
                ),
                "images": [],
                "documents": [],
            }

        except Exception as exc:
            logger.error("Ошибка планирования поста: %s", exc)
            return {
                "data": f"Ошибка планирования: {exc}",
                "images": [],
                "documents": [],
            }

    async def _send_scheduled_post(self, text: str, image_url: str = "") -> None:
        """
        Внутренний метод: отправляет запланированный пост.
        Вызывается планировщиком.
        """
        try:
            if image_url:
                await self.bot.send_photo(
                    chat_id=self.channel_id,
                    photo=image_url,
                    caption=text,
                    parse_mode=ParseMode.HTML,
                )
            else:
                await self.bot.send_message(
                    chat_id=self.channel_id,
                    text=text,
                    parse_mode=ParseMode.HTML,
                )
            logger.info("Запланированный пост отправлен в канал %s", self.channel_id)
        except Exception as exc:
            logger.error("Ошибка отправки запланированного поста: %s", exc)

    async def _list_scheduled(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Возвращает список всех запланированных задач.
        """
        if not self.scheduler:
            return {"data": "Планировщик не инициализирован", "images": [], "documents": []}

        try:
            jobs = self.scheduler.get_jobs()

            if not jobs:
                return {
                    "data": "Нет запланированных задач",
                    "images": [],
                    "documents": [],
                }

            lines = [f"<b>Запланированные задачи ({len(jobs)}):</b>\n"]
            for job in jobs:
                next_run = job.next_run_time
                next_run_str = (
                    next_run.strftime("%d.%m.%Y %H:%M:%S") if next_run else "неизвестно"
                )
                lines.append(
                    f"• <code>{job.id}</code>\n"
                    f"  Время: {next_run_str}\n"
                    f"  Задача: {job.name}"
                )

            return {"data": "\n".join(lines), "images": [], "documents": []}

        except Exception as exc:
            logger.error("Ошибка получения списка задач: %s", exc)
            return {
                "data": f"Ошибка получения списка задач: {exc}",
                "images": [],
                "documents": [],
            }

    async def _cancel_scheduled(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Отменяет запланированную задачу по ID.
        Параметры: job_id (str).
        """
        job_id = params.get("job_id", "")

        if not job_id:
            return {"data": "Ошибка: job_id не указан", "images": [], "documents": []}

        if not self.scheduler:
            return {"data": "Планировщик не инициализирован", "images": [], "documents": []}

        try:
            self.scheduler.remove_job(job_id)
            logger.info("Задача %s отменена", job_id)
            return {
                "data": f"Задача <code>{job_id}</code> успешно отменена",
                "images": [],
                "documents": [],
            }

        except Exception as exc:
            logger.error("Ошибка отмены задачи %s: %s", job_id, exc)
            return {
                "data": f"Ошибка отмены задачи '{job_id}': {exc}",
                "images": [],
                "documents": [],
            }

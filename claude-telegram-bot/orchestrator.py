"""
orchestrator.py — Центральный оркестратор на базе Claude API с tool_use.
Управляет агентами, обрабатывает сообщения через agentic loop (до 10 итераций).
"""

import logging
import os
from typing import Any

import anthropic
from aiogram import Bot

from agents.content import ContentAgent
from agents.parser import ParserAgent
from agents.publisher import PublisherAgent
from agents.video import VideoAgent
from agents.voice import VoiceAgent

logger = logging.getLogger(__name__)

# Описание инструментов для Claude (на русском)
TOOLS: list[dict] = [
    # === ContentAgent ===
    {
        "name": "generate_text",
        "description": (
            "Генерирует текстовый контент через Claude. Используй когда нужно написать "
            "статью, пост, описание, перефразировать текст или создать любой текстовый контент."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Подробное задание для генерации текста",
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Максимальное количество токенов (по умолчанию 1000)",
                    "default": 1000,
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "generate_image",
        "description": (
            "Генерирует изображение через Replicate (модель flux-schnell). "
            "Используй когда пользователь просит создать, нарисовать или сгенерировать картинку."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Описание изображения на английском языке",
                },
                "width": {
                    "type": "integer",
                    "description": "Ширина изображения (по умолчанию 1024)",
                    "default": 1024,
                },
                "height": {
                    "type": "integer",
                    "description": "Высота изображения (по умолчанию 1024)",
                    "default": 1024,
                },
            },
            "required": ["prompt"],
        },
    },
    # === ParserAgent ===
    {
        "name": "parse_website",
        "description": (
            "Парсит веб-сайт и извлекает текстовое содержимое. "
            "Используй когда нужно прочитать, проанализировать или получить информацию с сайта."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL сайта для парсинга",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS-селектор для извлечения конкретного элемента (опционально)",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "parse_tg_channel",
        "description": (
            "Получает последние посты из Telegram-канала через Telethon. "
            "Используй когда нужно прочитать или проанализировать содержимое TG-канала."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Username канала (без @) или ссылка на канал",
                },
                "limit": {
                    "type": "integer",
                    "description": "Количество последних постов (по умолчанию 10)",
                    "default": 10,
                },
            },
            "required": ["channel"],
        },
    },
    # === PublisherAgent ===
    {
        "name": "publish_now",
        "description": (
            "Немедленно публикует сообщение или контент в Telegram-канал. "
            "Используй когда нужно опубликовать пост прямо сейчас."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Текст для публикации (поддерживает HTML-разметку)",
                },
                "image_url": {
                    "type": "string",
                    "description": "URL изображения для прикрепления к посту (опционально)",
                },
            },
            "required": ["text"],
        },
    },
    {
        "name": "schedule_post",
        "description": (
            "Планирует публикацию поста в Telegram-канал на указанное время. "
            "Используй когда нужно опубликовать пост позже."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Текст для публикации",
                },
                "scheduled_time": {
                    "type": "string",
                    "description": "Время публикации в формате ISO 8601 (например, 2024-01-15T10:00:00)",
                },
                "image_url": {
                    "type": "string",
                    "description": "URL изображения (опционально)",
                },
            },
            "required": ["text", "scheduled_time"],
        },
    },
    {
        "name": "list_scheduled",
        "description": (
            "Возвращает список всех запланированных публикаций. "
            "Используй чтобы показать расписание постов."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "cancel_scheduled",
        "description": (
            "Отменяет запланированную публикацию по ID задачи. "
            "Используй когда нужно удалить пост из расписания."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "string",
                    "description": "ID задачи для отмены (из списка list_scheduled)",
                },
            },
            "required": ["job_id"],
        },
    },
    # === VideoAgent ===
    {
        "name": "generate_video",
        "description": (
            "Генерирует видео через Replicate. "
            "Используй когда нужно создать видеоролик по описанию."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Описание видео на английском языке",
                },
                "duration": {
                    "type": "integer",
                    "description": "Длительность видео в секундах (по умолчанию 4)",
                    "default": 4,
                },
            },
            "required": ["prompt"],
        },
    },
    # === VoiceAgent ===
    {
        "name": "transcribe_voice",
        "description": (
            "Транскрибирует аудио в текст через Groq Whisper. "
            "Используй когда нужно распознать речь из аудиофайла."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "audio_data": {
                    "type": "string",
                    "description": "Base64-encoded аудиоданные",
                },
                "language": {
                    "type": "string",
                    "description": "Язык аудио (например, 'ru', 'en'). По умолчанию автоопределение.",
                },
            },
            "required": ["audio_data"],
        },
    },
    {
        "name": "synthesize_voice",
        "description": (
            "Синтезирует речь из текста через Microsoft Edge TTS (бесплатно, без ключа). "
            "Возвращает MP3-файл. Используй когда нужно озвучить текст."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Текст для озвучки",
                },
                "voice": {
                    "type": "string",
                    "description": (
                        "Голос для синтеза. Русские: ru-RU-SvetlanaNeural, ru-RU-DmitryNeural. "
                        "По умолчанию ru-RU-SvetlanaNeural."
                    ),
                    "default": "ru-RU-SvetlanaNeural",
                },
            },
            "required": ["text"],
        },
    },
]

# Маппинг инструментов к агентам
TOOL_TO_AGENT: dict[str, str] = {
    "generate_text": "content",
    "generate_image": "content",
    "parse_website": "parser",
    "parse_tg_channel": "parser",
    "publish_now": "publisher",
    "schedule_post": "publisher",
    "list_scheduled": "publisher",
    "cancel_scheduled": "publisher",
    "generate_video": "video",
    "transcribe_voice": "voice",
    "synthesize_voice": "voice",
}

SYSTEM_PROMPT = """Ты — умный AI-ассистент, интегрированный в Telegram бот.
Ты помогаешь владельцу управлять контентом, публиковать посты в каналы,
генерировать изображения и видео, парсить сайты и Telegram-каналы.

Когда пользователь просит выполнить задачу, используй доступные инструменты.
Отвечай на русском языке. Будь конкретным и полезным.
Форматируй ответы с использованием HTML: <b>жирный</b>, <i>курсив</i>, <code>код</code>.
"""


class Orchestrator:
    """
    Центральный оркестратор. Управляет агентами и обрабатывает сообщения
    через Claude API с agentic loop.
    """

    def __init__(self) -> None:
        """Инициализация оркестратора."""
        self.client = anthropic.AsyncAnthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"]
        )
        self.agents: dict[str, Any] = {}
        self.bot: Bot | None = None
        self.conversation_history: list[dict] = []
        self._max_iterations = 10

    async def setup(self, bot: Bot) -> None:
        """
        Инициализирует всех агентов. Вызывается при старте бота.
        """
        self.bot = bot

        self.agents["content"] = ContentAgent()
        self.agents["parser"] = ParserAgent()
        self.agents["publisher"] = PublisherAgent()
        self.agents["video"] = VideoAgent()
        self.agents["voice"] = VoiceAgent()

        for name, agent in self.agents.items():
            try:
                await agent.setup(bot)
                logger.info("Агент '%s' инициализирован", name)
            except Exception as exc:
                logger.error("Ошибка инициализации агента '%s': %s", name, exc)

    async def shutdown(self) -> None:
        """Корректное завершение работы агентов."""
        for name, agent in self.agents.items():
            try:
                if hasattr(agent, "shutdown"):
                    await agent.shutdown()
                logger.info("Агент '%s' остановлен", name)
            except Exception as exc:
                logger.error("Ошибка остановки агента '%s': %s", name, exc)

    async def transcribe_voice(self, audio_bytes: bytes) -> str:
        """
        Транскрибирует голосовое сообщение.
        Делегирует VoiceAgent напрямую (без Claude loop).
        """
        try:
            voice_agent: VoiceAgent = self.agents["voice"]
            result = await voice_agent.execute("transcribe_voice", {"audio_bytes": audio_bytes})
            return result.get("data", "")
        except Exception as exc:
            logger.error("Ошибка транскрибации: %s", exc)
            return ""

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> dict:
        """
        Выполняет инструмент через соответствующий агент.
        Возвращает dict с ключами data, images, documents.
        """
        agent_name = TOOL_TO_AGENT.get(tool_name)
        if not agent_name or agent_name not in self.agents:
            return {"data": f"Инструмент '{tool_name}' не найден", "images": [], "documents": []}

        agent = self.agents[agent_name]
        try:
            result = await agent.execute(tool_name, tool_input)
            return result
        except Exception as exc:
            logger.error("Ошибка выполнения инструмента '%s': %s", tool_name, exc)
            return {
                "data": f"Ошибка выполнения '{tool_name}': {exc}",
                "images": [],
                "documents": [],
            }

    async def process_message(self, user_text: str, user_id: int) -> str:
        """
        Главный метод обработки сообщения через Claude API с agentic loop.
        Выполняет до 10 итераций вызовов инструментов.
        Возвращает HTML-форматированный ответ для Telegram.
        """
        # Добавляем сообщение пользователя в историю
        self.conversation_history.append({
            "role": "user",
            "content": user_text,
        })

        # Хранилище для медиафайлов, собранных во время выполнения
        collected_images: list[str] = []
        collected_documents: list[str] = []

        iteration = 0
        final_response = ""

        try:
            while iteration < self._max_iterations:
                iteration += 1
                logger.info("Agentic loop итерация %d/%d", iteration, self._max_iterations)

                response = await self.client.messages.create(
                    model="claude-opus-4-5",
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=self.conversation_history,
                )

                logger.info("Claude stop_reason: %s", response.stop_reason)

                # Если Claude завершил ответ без вызова инструментов
                if response.stop_reason == "end_turn":
                    for block in response.content:
                        if hasattr(block, "text"):
                            final_response = block.text
                    # Добавляем ответ ассистента в историю
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": response.content,
                    })
                    break

                # Если Claude хочет вызвать инструменты
                if response.stop_reason == "tool_use":
                    # Добавляем ответ ассистента с вызовами инструментов в историю
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": response.content,
                    })

                    # Выполняем все вызовы инструментов
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            logger.info(
                                "Вызов инструмента: %s, параметры: %s",
                                block.name,
                                block.input,
                            )
                            result = await self._execute_tool(block.name, block.input)

                            # Собираем медиафайлы
                            if result.get("images"):
                                collected_images.extend(result["images"])
                            if result.get("documents"):
                                collected_documents.extend(result["documents"])

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": str(result.get("data", "")),
                            })

                    # Добавляем результаты инструментов в историю
                    self.conversation_history.append({
                        "role": "user",
                        "content": tool_results,
                    })
                    continue

                # Неожиданный stop_reason
                logger.warning("Неожиданный stop_reason: %s", response.stop_reason)
                break

            else:
                logger.warning("Достигнут лимит итераций agentic loop (%d)", self._max_iterations)
                final_response = (
                    "Достигнут лимит итераций. Задача может быть выполнена частично."
                )

        except anthropic.APIError as exc:
            logger.error("Ошибка Claude API: %s", exc)
            return f"<b>Ошибка Claude API:</b> <code>{exc}</code>"
        except Exception as exc:
            logger.error("Неожиданная ошибка оркестратора: %s", exc)
            return f"<b>Внутренняя ошибка:</b> <code>{exc}</code>"

        # Отправляем медиафайлы если есть
        if self.bot and collected_images:
            for img_url in collected_images:
                try:
                    await self.bot.send_photo(
                        chat_id=int(os.environ["OWNER_TELEGRAM_ID"]),
                        photo=img_url,
                    )
                except Exception as exc:
                    logger.error("Ошибка отправки фото: %s", exc)

        if self.bot and collected_documents:
            for doc_url in collected_documents:
                try:
                    await self.bot.send_document(
                        chat_id=int(os.environ["OWNER_TELEGRAM_ID"]),
                        document=doc_url,
                    )
                except Exception as exc:
                    logger.error("Ошибка отправки документа: %s", exc)

        return final_response or "<i>Задача выполнена.</i>"

    async def get_status(self) -> str:
        """
        Возвращает HTML-форматированный статус всех агентов и расписания.
        """
        lines = ["<b>Статус системы</b>\n"]

        for name, agent in self.agents.items():
            status_emoji = "✅"
            lines.append(f"{status_emoji} <b>{name}</b>: активен")

        # Получаем список запланированных задач
        try:
            publisher: PublisherAgent = self.agents.get("publisher")
            if publisher:
                sched_result = await publisher.execute("list_scheduled", {})
                sched_data = sched_result.get("data", "")
                lines.append(f"\n<b>Расписание:</b>\n{sched_data}")
        except Exception as exc:
            logger.error("Ошибка получения расписания: %s", exc)
            lines.append("\n<b>Расписание:</b> ошибка получения")

        lines.append(f"\n<b>История диалога:</b> {len(self.conversation_history)} сообщений")
        lines.append(f"<b>Макс. итераций:</b> {self._max_iterations}")

        return "\n".join(lines)

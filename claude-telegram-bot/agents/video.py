"""
agents/video.py — Агент генерации видео через Replicate.
Использует модели Replicate для создания видеоконтента.
"""

import asyncio
import logging
import os
from typing import Any

import httpx
from aiogram import Bot

logger = logging.getLogger(__name__)

# URL API Replicate для генерации видео (модель minimax/video-01)
REPLICATE_PREDICTIONS_URL = "https://api.replicate.com/v1/predictions"
VIDEO_MODEL_VERSION = "minimax/video-01"


class VideoAgent:
    """
    Агент для генерации видео через Replicate.
    Поддерживаемые инструменты: generate_video.
    """

    TOOLS = ["generate_video"]

    def __init__(self) -> None:
        """Инициализация агента."""
        self.bot: Bot | None = None
        self.replicate_token: str = ""

    async def setup(self, bot: Bot) -> None:
        """
        Настройка агента. Загружает API-токен.
        """
        self.bot = bot
        self.replicate_token = os.environ.get("REPLICATE_API_TOKEN", "")

        if not self.replicate_token:
            logger.warning("REPLICATE_API_TOKEN не настроен — генерация видео недоступна")
        else:
            logger.info("VideoAgent инициализирован")

    async def execute(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Выполняет инструмент агента.

        Параметры:
            tool_name: название инструмента
            params: параметры инструмента

        Возвращает dict с ключами: data, images, documents
        """
        try:
            if tool_name == "generate_video":
                return await self._generate_video(params)
            else:
                return {
                    "data": f"VideoAgent: неизвестный инструмент '{tool_name}'",
                    "images": [],
                    "documents": [],
                }
        except Exception as exc:
            logger.error("VideoAgent.execute('%s') ошибка: %s", tool_name, exc)
            return {
                "data": f"Ошибка VideoAgent при выполнении '{tool_name}': {exc}",
                "images": [],
                "documents": [],
            }

    async def _generate_video(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Генерирует видео через Replicate.
        Параметры: prompt (str), duration (int, по умолчанию 4).
        """
        prompt = params.get("prompt", "")
        duration = params.get("duration", 4)

        if not prompt:
            return {"data": "Ошибка: prompt не указан", "images": [], "documents": []}

        if not self.replicate_token:
            return {
                "data": "Ошибка: REPLICATE_API_TOKEN не настроен",
                "images": [],
                "documents": [],
            }

        try:
            headers = {
                "Authorization": f"Bearer {self.replicate_token}",
                "Content-Type": "application/json",
            }

            # Создаём предсказание
            payload = {
                "version": VIDEO_MODEL_VERSION,
                "input": {
                    "prompt": prompt,
                    "duration": duration,
                    "resolution": "720p",
                    "aspect_ratio": "16:9",
                },
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    REPLICATE_PREDICTIONS_URL,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                result = response.json()

            prediction_id = result.get("id")
            if not prediction_id:
                return {
                    "data": f"Replicate: не получен ID предсказания. Ответ: {result}",
                    "images": [],
                    "documents": [],
                }

            logger.info("generate_video: запущено предсказание %s", prediction_id)

            # Ждём результата (видео генерируется долго)
            video_url = await self._poll_video_prediction(prediction_id, headers)

            if not video_url:
                return {
                    "data": "Видео не было сгенерировано. Попробуйте ещё раз.",
                    "images": [],
                    "documents": [],
                }

            logger.info("generate_video: видео готово: %s", video_url)
            return {
                "data": f"Видео сгенерировано: {video_url}",
                "images": [],
                "documents": [video_url],
            }

        except httpx.HTTPStatusError as exc:
            logger.error("Ошибка Replicate HTTP: %d — %s", exc.response.status_code, exc.response.text)
            return {
                "data": f"Ошибка Replicate API ({exc.response.status_code}): {exc.response.text}",
                "images": [],
                "documents": [],
            }
        except TimeoutError as exc:
            logger.error("Таймаут генерации видео: %s", exc)
            return {
                "data": f"Таймаут: видео не было сгенерировано за отведённое время. {exc}",
                "images": [],
                "documents": [],
            }
        except Exception as exc:
            logger.error("Ошибка generate_video: %s", exc)
            return {
                "data": f"Ошибка генерации видео: {exc}",
                "images": [],
                "documents": [],
            }

    async def _poll_video_prediction(
        self,
        prediction_id: str,
        headers: dict,
        max_wait: int = 300,
        poll_interval: int = 5,
    ) -> str | None:
        """
        Поллинг статуса предсказания Replicate до получения URL видео.
        Видео генерируется долго — ждём до 5 минут.
        """
        url = f"{REPLICATE_PREDICTIONS_URL}/{prediction_id}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            elapsed = 0
            while elapsed < max_wait:
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

                try:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                except Exception as exc:
                    logger.warning("Ошибка поллинга предсказания %s: %s", prediction_id, exc)
                    continue

                status = data.get("status")
                logger.info(
                    "Видео %s: статус=%s, прошло=%dс",
                    prediction_id,
                    status,
                    elapsed,
                )

                if status == "succeeded":
                    output = data.get("output")
                    if isinstance(output, list) and output:
                        return output[0]
                    elif isinstance(output, str):
                        return output
                    return None

                elif status in ("failed", "canceled"):
                    error = data.get("error", "неизвестная ошибка")
                    raise RuntimeError(f"Replicate prediction {status}: {error}")

        raise TimeoutError(
            f"Видео prediction {prediction_id} не завершилось за {max_wait} секунд"
        )

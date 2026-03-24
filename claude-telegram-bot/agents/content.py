"""
agents/content.py — Агент генерации контента.
Генерирует текст через Claude и изображения через Replicate (flux-schnell).
"""

import logging
import os
from typing import Any

import anthropic
import httpx
from aiogram import Bot

logger = logging.getLogger(__name__)

REPLICATE_API_URL = "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions"


class ContentAgent:
    """
    Агент для генерации текстового и визуального контента.
    Поддерживаемые инструменты: generate_text, generate_image.
    """

    TOOLS = ["generate_text", "generate_image"]

    def __init__(self) -> None:
        """Инициализация агента."""
        self.bot: Bot | None = None
        self.claude_client: anthropic.AsyncAnthropic | None = None
        self.replicate_token: str = ""

    async def setup(self, bot: Bot) -> None:
        """
        Настройка агента. Инициализирует API-клиенты.
        """
        self.bot = bot
        self.claude_client = anthropic.AsyncAnthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"]
        )
        self.replicate_token = os.environ.get("REPLICATE_API_TOKEN", "")
        logger.info("ContentAgent инициализирован")

    async def execute(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Выполняет инструмент агента.

        Параметры:
            tool_name: название инструмента (generate_text, generate_image)
            params: параметры инструмента

        Возвращает dict с ключами: data, images, documents
        """
        try:
            if tool_name == "generate_text":
                return await self._generate_text(params)
            elif tool_name == "generate_image":
                return await self._generate_image(params)
            else:
                return {
                    "data": f"ContentAgent: неизвестный инструмент '{tool_name}'",
                    "images": [],
                    "documents": [],
                }
        except Exception as exc:
            logger.error("ContentAgent.execute('%s') ошибка: %s", tool_name, exc)
            return {
                "data": f"Ошибка ContentAgent при выполнении '{tool_name}': {exc}",
                "images": [],
                "documents": [],
            }

    async def _generate_text(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Генерирует текст через Claude API.
        Параметры: prompt (str), max_tokens (int, по умолчанию 1000).
        """
        prompt = params.get("prompt", "")
        max_tokens = params.get("max_tokens", 1000)

        if not prompt:
            return {"data": "Ошибка: prompt не указан", "images": [], "documents": []}

        try:
            response = await self.claude_client.messages.create(
                model="claude-opus-4-5",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text if response.content else ""
            logger.info("generate_text: сгенерировано %d символов", len(text))
            return {"data": text, "images": [], "documents": []}

        except anthropic.APIError as exc:
            logger.error("Ошибка Claude API в generate_text: %s", exc)
            return {
                "data": f"Ошибка Claude API: {exc}",
                "images": [],
                "documents": [],
            }

    async def _generate_image(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Генерирует изображение через Replicate flux-schnell.
        Параметры: prompt (str), width (int), height (int).
        """
        prompt = params.get("prompt", "")
        width = params.get("width", 1024)
        height = params.get("height", 1024)

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
                "Prefer": "wait",
            }
            payload = {
                "input": {
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "num_outputs": 1,
                    "output_format": "webp",
                    "output_quality": 80,
                }
            }

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    REPLICATE_API_URL,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                result = response.json()

            # Извлекаем URL изображения
            output = result.get("output")
            if isinstance(output, list) and output:
                image_url = output[0]
            elif isinstance(output, str):
                image_url = output
            else:
                # Если нужно поллить статус
                prediction_id = result.get("id")
                if prediction_id:
                    image_url = await self._poll_prediction(prediction_id)
                else:
                    return {
                        "data": f"Replicate: неожиданный формат ответа: {result}",
                        "images": [],
                        "documents": [],
                    }

            logger.info("generate_image: изображение сгенерировано: %s", image_url)
            return {
                "data": f"Изображение сгенерировано: {image_url}",
                "images": [image_url],
                "documents": [],
            }

        except httpx.HTTPStatusError as exc:
            logger.error("Ошибка Replicate HTTP: %s — %s", exc.response.status_code, exc.response.text)
            return {
                "data": f"Ошибка Replicate API ({exc.response.status_code}): {exc.response.text}",
                "images": [],
                "documents": [],
            }
        except Exception as exc:
            logger.error("Ошибка generate_image: %s", exc)
            return {
                "data": f"Ошибка генерации изображения: {exc}",
                "images": [],
                "documents": [],
            }

    async def _poll_prediction(self, prediction_id: str, max_wait: int = 60) -> str:
        """
        Поллинг статуса предсказания Replicate до получения результата.
        """
        import asyncio

        url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
        headers = {
            "Authorization": f"Bearer {self.replicate_token}",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            for _ in range(max_wait // 2):
                await asyncio.sleep(2)
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                status = data.get("status")

                if status == "succeeded":
                    output = data.get("output")
                    if isinstance(output, list) and output:
                        return output[0]
                    elif isinstance(output, str):
                        return output

                elif status in ("failed", "canceled"):
                    raise RuntimeError(f"Replicate prediction {status}: {data.get('error')}")

        raise TimeoutError(f"Replicate prediction {prediction_id} не завершилось за {max_wait}с")

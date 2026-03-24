"""
agents/voice.py — Агент для работы с голосом.
Транскрибирует аудио через Groq Whisper (STT) и синтезирует речь через edge-tts (TTS).
"""

import base64
import io
import logging
import os
import tempfile
from typing import Any

import edge_tts
from aiogram import Bot
from groq import AsyncGroq

logger = logging.getLogger(__name__)

# Поддерживаемые голоса edge-tts (русские)
RUSSIAN_VOICES = {
    "female": "ru-RU-SvetlanaNeural",
    "male": "ru-RU-DmitryNeural",
    "default": "ru-RU-SvetlanaNeural",
}

# Поддерживаемые голоса edge-tts (английские)
ENGLISH_VOICES = {
    "female": "en-US-JennyNeural",
    "male": "en-US-GuyNeural",
}


class VoiceAgent:
    """
    Агент для работы с голосом.
    Поддерживаемые инструменты: transcribe_voice, synthesize_voice.
    """

    TOOLS = ["transcribe_voice", "synthesize_voice"]

    def __init__(self) -> None:
        """Инициализация агента."""
        self.bot: Bot | None = None
        self.groq_client: AsyncGroq | None = None

    async def setup(self, bot: Bot) -> None:
        """
        Настройка агента. Инициализирует Groq API клиент.
        """
        self.bot = bot

        groq_key = os.environ.get("GROQ_API_KEY", "")
        if groq_key:
            self.groq_client = AsyncGroq(api_key=groq_key)
            logger.info("VoiceAgent: Groq Whisper инициализирован")
        else:
            logger.warning("GROQ_API_KEY не настроен — транскрибация недоступна")

        logger.info("VoiceAgent инициализирован")

    async def execute(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Выполняет инструмент агента.

        Параметры:
            tool_name: название инструмента
            params: параметры инструмента

        Возвращает dict с ключами: data, images, documents
        """
        try:
            if tool_name == "transcribe_voice":
                return await self._transcribe_voice(params)
            elif tool_name == "synthesize_voice":
                return await self._synthesize_voice(params)
            else:
                return {
                    "data": f"VoiceAgent: неизвестный инструмент '{tool_name}'",
                    "images": [],
                    "documents": [],
                }
        except Exception as exc:
            logger.error("VoiceAgent.execute('%s') ошибка: %s", tool_name, exc)
            return {
                "data": f"Ошибка VoiceAgent при выполнении '{tool_name}': {exc}",
                "images": [],
                "documents": [],
            }

    async def _transcribe_voice(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Транскрибирует аудио в текст через Groq Whisper.
        Принимает audio_data (base64 str) или audio_bytes (bytes).
        """
        if not self.groq_client:
            return {
                "data": "Ошибка: GROQ_API_KEY не настроен",
                "images": [],
                "documents": [],
            }

        language = params.get("language", None)

        # Получаем аудиоданные
        audio_bytes: bytes | None = None

        if "audio_bytes" in params:
            # Прямые байты (из handle_voice в bot.py)
            audio_bytes = params["audio_bytes"]
        elif "audio_data" in params:
            # Base64-encoded строка (из tool_use)
            audio_data_b64 = params["audio_data"]
            try:
                audio_bytes = base64.b64decode(audio_data_b64)
            except Exception as exc:
                return {
                    "data": f"Ошибка декодирования base64: {exc}",
                    "images": [],
                    "documents": [],
                }
        else:
            return {
                "data": "Ошибка: audio_data или audio_bytes не переданы",
                "images": [],
                "documents": [],
            }

        try:
            # Создаём временный файл для Groq API
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = tmp_file.name

            try:
                with open(tmp_path, "rb") as audio_file:
                    transcription_params: dict = {
                        "file": ("audio.ogg", audio_file, "audio/ogg"),
                        "model": "whisper-large-v3",
                        "response_format": "text",
                    }
                    if language:
                        transcription_params["language"] = language

                    transcription = await self.groq_client.audio.transcriptions.create(
                        **transcription_params
                    )
            finally:
                # Удаляем временный файл
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

            # Groq возвращает строку при response_format="text"
            text = transcription if isinstance(transcription, str) else transcription.text
            text = text.strip()

            logger.info("transcribe_voice: '%s...'", text[:50])
            return {"data": text, "images": [], "documents": []}

        except Exception as exc:
            logger.error("Ошибка Groq Whisper: %s", exc)
            return {
                "data": f"Ошибка транскрибации: {exc}",
                "images": [],
                "documents": [],
            }

    async def _synthesize_voice(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Синтезирует речь из текста через Microsoft Edge TTS (бесплатно, без ключа).
        Возвращает путь к MP3-файлу.
        Параметры: text (str), voice (str, по умолчанию ru-RU-SvetlanaNeural).
        """
        text = params.get("text", "")
        voice = params.get("voice", RUSSIAN_VOICES["default"])

        if not text:
            return {"data": "Ошибка: текст не указан", "images": [], "documents": []}

        # Ограничиваем длину текста
        if len(text) > 3000:
            text = text[:3000]
            logger.warning("Текст обрезан до 3000 символов для TTS")

        try:
            # Создаём временный MP3-файл
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(tmp_path)

            # Проверяем что файл создан
            file_size = os.path.getsize(tmp_path)
            if file_size == 0:
                os.unlink(tmp_path)
                return {
                    "data": "Ошибка: edge-tts вернул пустой файл",
                    "images": [],
                    "documents": [],
                }

            logger.info(
                "synthesize_voice: %d байт, голос=%s, текст='%s...'",
                file_size,
                voice,
                text[:30],
            )

            # Отправляем аудио владельцу
            if self.bot:
                owner_id = os.environ.get("OWNER_TELEGRAM_ID")
                if owner_id:
                    try:
                        with open(tmp_path, "rb") as audio_file:
                            await self.bot.send_audio(
                                chat_id=int(owner_id),
                                audio=audio_file,
                                caption=f"<i>Синтезированная речь ({voice})</i>",
                                parse_mode="HTML",
                            )
                    except Exception as send_exc:
                        logger.error("Ошибка отправки аудио: %s", send_exc)
                    finally:
                        try:
                            os.unlink(tmp_path)
                        except OSError:
                            pass

            return {
                "data": f"Аудио синтезировано и отправлено. Голос: {voice}. Символов: {len(text)}",
                "images": [],
                "documents": [],
            }

        except edge_tts.exceptions.NoAudioReceived as exc:
            logger.error("edge-tts не вернул аудио: %s", exc)
            return {
                "data": f"Ошибка TTS: аудио не получено. Проверьте голос '{voice}'. {exc}",
                "images": [],
                "documents": [],
            }
        except Exception as exc:
            logger.error("Ошибка synthesize_voice: %s", exc)
            return {
                "data": f"Ошибка синтеза речи: {exc}",
                "images": [],
                "documents": [],
            }

    @staticmethod
    def list_voices() -> list[str]:
        """Возвращает список доступных русских голосов."""
        return list(RUSSIAN_VOICES.values()) + list(ENGLISH_VOICES.values())

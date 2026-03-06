"""
🎙️🔊 ГОЛОСОВОЙ ДВИЖОК ДЛЯ ANDROID
=====================================
STT: Android SpeechRecognizer (через plyer) → Whisper как fallback
TTS: Android TextToSpeech (через plyer) → pyttsx3 как fallback

На Android: используется нативный SpeechRecognizer — лучшее качество,
офлайн-режим поддерживается начиная с Android 10+
"""

import threading
import os
import platform
from utils.logger import log

# Определяем платформу
IS_ANDROID = os.path.exists('/proc/version') and 'android' in open('/proc/version').read().lower() \
             if os.path.exists('/proc/version') else False


class VoiceEngine:
    def __init__(self):
        self._tts_engine = None
        self._init_tts()

    # ─── ИНИЦИАЛИЗАЦИЯ TTS ────────────────────────────────────────────────────
    def _init_tts(self):
        if IS_ANDROID:
            self._init_android_tts()
        else:
            self._init_desktop_tts()

    def _init_android_tts(self):
        """Android Text-to-Speech через plyer."""
        try:
            from plyer import tts
            self._tts_engine = "android"
            log("✅ Android TTS готов")
        except ImportError:
            log("⚠️ plyer не установлен")
            self._init_desktop_tts()

    def _init_desktop_tts(self):
        """Desktop TTS через pyttsx3."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')

            # Ищем русский голос
            for v in voices:
                if 'russian' in v.name.lower() or 'ru' in v.id.lower():
                    engine.setProperty('voice', v.id)
                    break

            engine.setProperty('rate', 160)
            engine.setProperty('volume', 1.0)
            self._tts_engine = engine
            log("✅ Desktop TTS (pyttsx3) готов")
        except Exception as e:
            log(f"⚠️ pyttsx3 не доступен: {e}")
            self._tts_engine = None

    # ─── СИНТЕЗ РЕЧИ ─────────────────────────────────────────────────────────
    def speak(self, text: str):
        """Произносит текст."""
        if not text:
            return

        # Очищаем текст от markdown-разметки для речи
        import re
        clean = re.sub(r'\[/?[a-z/]+[^\]]*\]', '', text)  # KV markup
        clean = re.sub(r'[✦✅⚠️📅📊🗑️🎓●]', '', clean)   # Эмодзи
        clean = clean.strip()

        if IS_ANDROID and self._tts_engine == "android":
            self._speak_android(clean)
        elif self._tts_engine and self._tts_engine != "android":
            self._speak_pyttsx3(clean)
        else:
            log(f"[TTS]: {clean}")

    def _speak_android(self, text: str):
        try:
            from plyer import tts
            tts.speak(text)
        except Exception as e:
            log(f"❌ Android TTS error: {e}")

    def _speak_pyttsx3(self, text: str):
        try:
            self._tts_engine.say(text)
            self._tts_engine.runAndWait()
        except Exception as e:
            log(f"❌ pyttsx3 error: {e}")

    # ─── РАСПОЗНАВАНИЕ РЕЧИ ───────────────────────────────────────────────────
    def listen(self, timeout: int = 6) -> str:
        """
        Записывает голос и возвращает текст.
        Android: использует нативный SpeechRecognizer
        Desktop: использует Whisper
        """
        if IS_ANDROID:
            return self._listen_android(timeout)
        else:
            return self._listen_whisper(timeout)

    def _listen_android(self, timeout: int) -> str:
        """
        Android Speech Recognition через SpeechRecognizer API.
        Вызывается через Kivy Android API (pyjnius).
        """
        try:
            from jnius import autoclass, cast
            from android import mActivity

            SpeechRecognizer = autoclass('android.speech.SpeechRecognizer')
            RecognizerIntent = autoclass('android.speech.RecognizerIntent')
            Intent = autoclass('android.content.Intent')
            Locale = autoclass('java.util.Locale')

            result_holder = {'text': '', 'done': threading.Event()}

            class RecognitionListener(autoclass('android.speech.RecognitionListener')):
                def onResults(self, bundle):
                    results = bundle.getStringArrayList(RecognizerIntent.EXTRA_RESULTS)
                    if results and results.size() > 0:
                        result_holder['text'] = results.get(0)
                    result_holder['done'].set()

                def onError(self, error):
                    result_holder['done'].set()

                # Остальные методы интерфейса
                def onBeginningOfSpeech(self): pass
                def onBufferReceived(self, b): pass
                def onEndOfSpeech(self): pass
                def onEvent(self, t, b): pass
                def onPartialResults(self, b): pass
                def onRmsChanged(self, v): pass
                def onReadyForSpeech(self, b): pass

            recognizer = SpeechRecognizer.createSpeechRecognizer(mActivity)
            listener = RecognitionListener()
            recognizer.setRecognitionListener(listener)

            intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                           RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, "ru-RU")
            intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)

            recognizer.startListening(intent)
            result_holder['done'].wait(timeout=timeout + 2)
            recognizer.destroy()

            return result_holder['text']

        except Exception as e:
            log(f"❌ Android STT error: {e}")
            return self._listen_whisper(timeout)

    def _listen_whisper(self, duration: int = 6) -> str:
        """Desktop: Whisper STT."""
        try:
            import whisper
            import sounddevice as sd
            import numpy as np
            import soundfile as sf
            import tempfile

            log(f"🎤 Запись {duration} сек...")
            audio = sd.rec(int(duration * 16000), samplerate=16000, channels=1, dtype=np.float32)
            sd.wait()

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_path = f.name
                sf.write(tmp_path, audio, 16000)

            model = whisper.load_model("base")
            result = model.transcribe(tmp_path, language="ru", fp16=False)
            os.unlink(tmp_path)
            return result["text"].strip()

        except Exception as e:
            log(f"❌ Whisper error: {e}")
            return ""

"""
╔══════════════════════════════════════════════════════╗
║         ARIA — AI Personal Assistant                 ║
║         Android APK | KivyMD | Python                ║
╚══════════════════════════════════════════════════════╝
"""

import os
os.environ['KIVY_NO_ENV_CONFIG'] = '1'

from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.properties import StringProperty, BooleanProperty, ListProperty
from kivy.metrics import dp

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager

import threading
from core.voice_engine import VoiceEngine
from core.ai_brain import AIBrain
from core.memory import MemorySystem
from core.scheduler import Scheduler
from core.google_sheets import GoogleSheetsManager
from utils.logger import log

# ─── KV DESIGN (Cyberpunk / Neon Dark Theme) ─────────────────────────────────
KV = '''
#:import get_color_from_hex kivy.utils.get_color_from_hex
#:import Animation kivy.animation.Animation

<MainScreen>:
    name: "main"
    canvas.before:
        Color:
            rgba: get_color_from_hex("#0A0A0F")
        Rectangle:
            pos: self.pos
            size: self.size
        # Grid lines (декоративные)
        Color:
            rgba: get_color_from_hex("#00FFD115")
        Line:
            points: [0, self.height*0.5, self.width, self.height*0.5]
            width: 0.5

    MDBoxLayout:
        orientation: "vertical"
        spacing: dp(8)
        padding: [dp(16), dp(40), dp(16), dp(20)]

        # ── HEADER ─────────────────────────────────────
        MDBoxLayout:
            size_hint_y: None
            height: dp(60)
            spacing: dp(10)

            MDBoxLayout:
                orientation: "vertical"
                size_hint_x: 0.7

                MDLabel:
                    text: "ARIA"
                    font_name: "Roboto"
                    font_style: "H4"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: get_color_from_hex("#00FFD1")
                    size_hint_y: None
                    height: dp(36)

                MDLabel:
                    text: app.status_text
                    font_style: "Caption"
                    theme_text_color: "Custom"
                    text_color: get_color_from_hex("#888899")
                    size_hint_y: None
                    height: dp(18)

            MDBoxLayout:
                size_hint_x: 0.3
                spacing: dp(8)

                # Кнопка расписания
                MDIconButton:
                    icon: "calendar-month"
                    theme_icon_color: "Custom"
                    icon_color: get_color_from_hex("#00FFD1")
                    on_release: app.show_schedule()

                # Кнопка настроек
                MDIconButton:
                    icon: "cog-outline"
                    theme_icon_color: "Custom"
                    icon_color: get_color_from_hex("#888899")
                    on_release: app.go_settings()

        # ── ИНДИКАТОР ПАМЯТИ И ОБУЧЕНИЯ ─────────────────
        MDCard:
            size_hint_y: None
            height: dp(54)
            padding: [dp(16), dp(8)]
            radius: [dp(12)]
            md_bg_color: get_color_from_hex("#0D0D1A")
            elevation: 0
            line_color: get_color_from_hex("#00FFD130")

            MDBoxLayout:
                spacing: dp(20)

                MDBoxLayout:
                    orientation: "vertical"
                    MDLabel:
                        text: "ПАМЯТЬ"
                        font_style: "Overline"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("#555566")
                    MDLabel:
                        text: app.memory_count
                        font_style: "Subtitle2"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("#00FFD1")

                MDBoxLayout:
                    orientation: "vertical"
                    MDLabel:
                        text: "ОБУЧЕНИЙ"
                        font_style: "Overline"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("#555566")
                    MDLabel:
                        text: app.learning_count
                        font_style: "Subtitle2"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("#BD00FF")

                MDBoxLayout:
                    orientation: "vertical"
                    MDLabel:
                        text: "ЗАДАЧИ"
                        font_style: "Overline"
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("#555566")
                    MDLabel:
                        text: app.task_count
                        font_style: "Subtitle2"
                        bold: True
                        theme_text_color: "Custom"
                        text_color: get_color_from_hex("#FF6B35")

        # ── ЧАТ-ЛЕНТА ───────────────────────────────────
        ScrollView:
            id: scroll_view
            do_scroll_x: False
            bar_width: dp(2)
            bar_color: get_color_from_hex("#00FFD150")

            MDBoxLayout:
                id: chat_box
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(12)
                padding: [0, dp(8), 0, dp(8)]

        # ── КНОПКА ГОЛОСА ───────────────────────────────
        MDBoxLayout:
            size_hint_y: None
            height: dp(140)
            orientation: "vertical"
            spacing: dp(12)

            # Анимированная кнопка микрофона
            FloatLayout:
                size_hint_y: None
                height: dp(100)

                # Внешнее кольцо (пульсирует во время записи)
                Widget:
                    id: pulse_ring
                    size_hint: None, None
                    size: dp(90), dp(90)
                    pos_hint: {"center_x": 0.5, "center_y": 0.5}
                    canvas:
                        Color:
                            rgba: get_color_from_hex("#00FFD120") if not app.is_listening else get_color_from_hex("#00FFD140")
                        Ellipse:
                            pos: self.pos
                            size: self.size

                MDFloatingActionButton:
                    id: mic_button
                    icon: "microphone"
                    size_hint: None, None
                    size: dp(70), dp(70)
                    pos_hint: {"center_x": 0.5, "center_y": 0.5}
                    md_bg_color: get_color_from_hex("#00FFD1") if not app.is_listening else get_color_from_hex("#FF4466")
                    theme_icon_color: "Custom"
                    icon_color: get_color_from_hex("#0A0A0F")
                    elevation: 8
                    on_press: app.toggle_voice()

            # Текстовый ввод
            MDBoxLayout:
                size_hint_y: None
                height: dp(44)
                spacing: dp(8)

                MDTextField:
                    id: text_input
                    hint_text: "Или напиши здесь..."
                    mode: "rectangle"
                    fill_color_normal: get_color_from_hex("#0D0D1A")
                    line_color_normal: get_color_from_hex("#00FFD130")
                    line_color_focus: get_color_from_hex("#00FFD1")
                    hint_text_color_normal: get_color_from_hex("#555566")
                    text_color_normal: get_color_from_hex("#EEEEFF")
                    font_size: "14sp"
                    on_text_validate: app.send_text(self.text)

                MDIconButton:
                    icon: "send"
                    theme_icon_color: "Custom"
                    icon_color: get_color_from_hex("#00FFD1")
                    on_release: app.send_text(text_input.text)

<SettingsScreen>:
    name: "settings"
    canvas.before:
        Color:
            rgba: get_color_from_hex("#0A0A0F")
        Rectangle:
            pos: self.pos
            size: self.size

    MDBoxLayout:
        orientation: "vertical"
        padding: [dp(16), dp(40), dp(16), dp(20)]
        spacing: dp(16)

        MDBoxLayout:
            size_hint_y: None
            height: dp(50)
            MDIconButton:
                icon: "arrow-left"
                theme_icon_color: "Custom"
                icon_color: get_color_from_hex("#00FFD1")
                on_release: app.go_main()
            MDLabel:
                text: "Настройки"
                font_style: "H6"
                theme_text_color: "Custom"
                text_color: get_color_from_hex("#EEEEFF")

        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(12)

                # API ключи
                MDCard:
                    size_hint_y: None
                    height: dp(200)
                    padding: dp(16)
                    radius: [dp(12)]
                    md_bg_color: get_color_from_hex("#0D0D1A")
                    elevation: 0
                    line_color: get_color_from_hex("#00FFD130")

                    MDBoxLayout:
                        orientation: "vertical"
                        spacing: dp(12)

                        MDLabel:
                            text: "API Ключи"
                            font_style: "Subtitle1"
                            bold: True
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("#00FFD1")
                            size_hint_y: None
                            height: dp(24)

                        MDTextField:
                            id: groq_key
                            hint_text: "Groq API Key (бесплатно)"
                            mode: "rectangle"
                            fill_color_normal: get_color_from_hex("#12121F")
                            line_color_normal: get_color_from_hex("#333344")
                            line_color_focus: get_color_from_hex("#00FFD1")
                            hint_text_color_normal: get_color_from_hex("#555566")
                            text_color_normal: get_color_from_hex("#EEEEFF")
                            password: True
                            text: app.groq_api_key

                        MDTextField:
                            id: sheets_id
                            hint_text: "Google Sheets ID"
                            mode: "rectangle"
                            fill_color_normal: get_color_from_hex("#12121F")
                            line_color_normal: get_color_from_hex("#333344")
                            line_color_focus: get_color_from_hex("#00FFD1")
                            hint_text_color_normal: get_color_from_hex("#555566")
                            text_color_normal: get_color_from_hex("#EEEEFF")
                            text: app.sheets_id

                        MDRaisedButton:
                            text: "Сохранить"
                            md_bg_color: get_color_from_hex("#00FFD1")
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("#0A0A0F")
                            on_release: app.save_settings(groq_key.text, sheets_id.text)

                # Google Sheets статус
                MDCard:
                    size_hint_y: None
                    height: dp(80)
                    padding: dp(16)
                    radius: [dp(12)]
                    md_bg_color: get_color_from_hex("#0D0D1A")
                    elevation: 0
                    line_color: get_color_from_hex("#BD00FF30")

                    MDBoxLayout:
                        spacing: dp(12)
                        MDIcon:
                            icon: "google-spreadsheet"
                            theme_icon_color: "Custom"
                            icon_color: get_color_from_hex("#BD00FF")
                            size_hint_x: None
                            width: dp(32)
                        MDBoxLayout:
                            orientation: "vertical"
                            MDLabel:
                                text: "Google Sheets"
                                font_style: "Subtitle2"
                                bold: True
                                theme_text_color: "Custom"
                                text_color: get_color_from_hex("#EEEEFF")
                            MDLabel:
                                text: app.sheets_status
                                font_style: "Caption"
                                theme_text_color: "Custom"
                                text_color: get_color_from_hex("#888899")

                # Персонализация
                MDCard:
                    size_hint_y: None
                    height: dp(130)
                    padding: dp(16)
                    radius: [dp(12)]
                    md_bg_color: get_color_from_hex("#0D0D1A")
                    elevation: 0
                    line_color: get_color_from_hex("#FF6B3530")

                    MDBoxLayout:
                        orientation: "vertical"
                        spacing: dp(8)
                        MDLabel:
                            text: "Имя ассистента"
                            font_style: "Subtitle2"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("#FF6B35")
                            size_hint_y: None
                            height: dp(20)
                        MDTextField:
                            id: assistant_name
                            hint_text: "ARIA"
                            text: app.assistant_name_setting
                            mode: "rectangle"
                            fill_color_normal: get_color_from_hex("#12121F")
                            line_color_focus: get_color_from_hex("#FF6B35")
                            text_color_normal: get_color_from_hex("#EEEEFF")
                        MDLabel:
                            text: "Обучение включено: автоматически запоминает предпочтения"
                            font_style: "Caption"
                            theme_text_color: "Custom"
                            text_color: get_color_from_hex("#555566")
                            size_hint_y: None
                            height: dp(30)

<ScheduleScreen>:
    name: "schedule"
    canvas.before:
        Color:
            rgba: get_color_from_hex("#0A0A0F")
        Rectangle:
            pos: self.pos
            size: self.size

    MDBoxLayout:
        orientation: "vertical"
        padding: [dp(16), dp(40), dp(16), dp(20)]
        spacing: dp(12)

        MDBoxLayout:
            size_hint_y: None
            height: dp(50)
            MDIconButton:
                icon: "arrow-left"
                theme_icon_color: "Custom"
                icon_color: get_color_from_hex("#00FFD1")
                on_release: app.go_main()
            MDLabel:
                text: "Расписание"
                font_style: "H6"
                theme_text_color: "Custom"
                text_color: get_color_from_hex("#EEEEFF")
            MDIconButton:
                icon: "google-spreadsheet"
                theme_icon_color: "Custom"
                icon_color: get_color_from_hex("#BD00FF")
                on_release: app.sync_to_sheets()

        ScrollView:
            id: schedule_scroll
            MDBoxLayout:
                id: schedule_box
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(8)
'''

# ─── BUBBLE WIDGETS ───────────────────────────────────────────────────────────
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import get_color_from_hex
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout


def make_bubble(text: str, is_user: bool):
    """Создаёт пузырь сообщения с cyberpunk стилем."""
    from kivy.uix.boxlayout import BoxLayout as KBox
    outer = MDBoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        padding=[dp(8), 0],
        spacing=dp(4),
    )

    bubble = MDCard(
        size_hint_x=0.82,
        md_bg_color=get_color_from_hex("#0D0D1A") if not is_user else get_color_from_hex("#001A14"),
        radius=[dp(16), dp(16), dp(4) if is_user else dp(16), dp(4) if not is_user else dp(16)],
        elevation=0,
        line_color=get_color_from_hex("#00FFD130") if is_user else get_color_from_hex("#BD00FF20"),
        padding=[dp(14), dp(10)],
    )

    lbl = MDLabel(
        text=text,
        theme_text_color="Custom",
        text_color=get_color_from_hex("#EEEEFF"),
        font_style="Body2",
        size_hint_y=None,
        markup=True,
    )
    lbl.bind(texture_size=lambda *_: setattr(lbl, 'height', lbl.texture_size[1]))
    bubble.add_widget(lbl)

    # Выравнивание по стороне
    if is_user:
        outer.add_widget(MDBoxLayout(size_hint_x=0.18))
        outer.add_widget(bubble)
    else:
        outer.add_widget(bubble)
        outer.add_widget(MDBoxLayout(size_hint_x=0.18))

    outer.bind(minimum_height=outer.setter('height'))
    return outer


# ─── APP CLASS ────────────────────────────────────────────────────────────────

class MainScreen(MDScreen): pass
class SettingsScreen(MDScreen): pass
class ScheduleScreen(MDScreen): pass


class ARIAApp(MDApp):
    # Observable properties для KV
    status_text       = StringProperty("● готова к работе")
    memory_count      = StringProperty("0")
    learning_count    = StringProperty("0")
    task_count        = StringProperty("0")
    is_listening      = BooleanProperty(False)
    groq_api_key      = StringProperty("")
    sheets_id         = StringProperty("")
    sheets_status     = StringProperty("Не подключено")
    assistant_name_setting = StringProperty("ARIA")

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Teal"
        Builder.load_string(KV)

        self.sm = MDScreenManager()
        self.sm.add_widget(MainScreen())
        self.sm.add_widget(SettingsScreen())
        self.sm.add_widget(ScheduleScreen())

        # Инициализация компонентов
        self._init_components()
        # Обновление UI каждые 30 секунд
        Clock.schedule_interval(self._update_stats, 30)
        return self.sm

    def _init_components(self):
        """Запускает все подсистемы в фоне."""
        def _init():
            self.memory   = MemorySystem()
            self.scheduler = Scheduler()
            self.voice    = VoiceEngine()
            self.sheets   = GoogleSheetsManager()
            self.ai       = AIBrain(memory=self.memory)

            # Загрузка сохранённых настроек
            settings = self.memory.get_settings()
            self.groq_api_key = settings.get("groq_api_key", "")
            self.sheets_id    = settings.get("sheets_id", "")
            self.assistant_name_setting = settings.get("assistant_name", "ARIA")

            if self.groq_api_key:
                self.ai.set_api_key(self.groq_api_key)

            if self.sheets_id:
                ok = self.sheets.connect(self.sheets_id)
                Clock.schedule_once(lambda dt: setattr(
                    self, 'sheets_status',
                    "✓ Подключено" if ok else "✗ Ошибка подключения"
                ))

            self._update_stats()
            Clock.schedule_once(lambda dt: self._add_bubble(
                f"👋 Привет! Я {self.assistant_name_setting}, твой персональный ИИ-ассистент.\n"
                "Нажми кнопку микрофона или напиши сообщение. Я умею:\n"
                "[color=#00FFD1]• управлять расписанием[/color]\n"
                "[color=#BD00FF]• работать с Google Таблицами[/color]\n"
                "[color=#FF6B35]• учиться твоим привычкам[/color]\n"
                "[color=#888899]• искать информацию в интернете[/color]",
                is_user=False
            ))
        threading.Thread(target=_init, daemon=True).start()

    def _update_stats(self, dt=None):
        def _do():
            if hasattr(self, 'memory'):
                stats = self.memory.get_stats()
                Clock.schedule_once(lambda dt: self._set_stats(stats))
        threading.Thread(target=_do, daemon=True).start()

    def _set_stats(self, stats):
        self.memory_count   = str(stats.get("memories", 0))
        self.learning_count = str(stats.get("learnings", 0))
        if hasattr(self, 'scheduler'):
            tasks = self.scheduler.get_today_tasks()
            self.task_count = str(len([t for t in tasks if not t['done']]))

    def _add_bubble(self, text: str, is_user: bool):
        """Добавляет пузырь в чат-ленту."""
        chat_box = self.root.get_screen("main").ids.chat_box
        bubble = make_bubble(text, is_user)
        chat_box.add_widget(bubble)
        # Прокрутка вниз
        scroll = self.root.get_screen("main").ids.scroll_view
        Clock.schedule_once(lambda dt: setattr(scroll, 'scroll_y', 0), 0.1)

    # ─── ГОЛОСОВОЙ ВВОД ────────────────────────────────────────────────────────
    def toggle_voice(self):
        if self.is_listening:
            return
        self.is_listening = True
        self.status_text = "● слушаю..."
        threading.Thread(target=self._do_listen, daemon=True).start()

    def _do_listen(self):
        text = self.voice.listen()
        self.is_listening = False
        if text:
            Clock.schedule_once(lambda dt: self._process_input(text))
        else:
            Clock.schedule_once(lambda dt: setattr(self, 'status_text', "● готова к работе"))

    # ─── ТЕКСТОВЫЙ ВВОД ────────────────────────────────────────────────────────
    def send_text(self, text: str):
        if not text.strip():
            return
        inp = self.root.get_screen("main").ids.text_input
        inp.text = ""
        self._process_input(text)

    # ─── ОБРАБОТКА ЗАПРОСА ─────────────────────────────────────────────────────
    def _process_input(self, text: str):
        self._add_bubble(text, is_user=True)
        self.status_text = "● думаю..."
        threading.Thread(target=self._get_response, args=(text,), daemon=True).start()

    def _get_response(self, text: str):
        try:
            response = self.ai.process(text, scheduler=self.scheduler, sheets=self.sheets)
            # Озвучиваем
            self.voice.speak(response)
            Clock.schedule_once(lambda dt: self._add_bubble(response, is_user=False))
            Clock.schedule_once(lambda dt: self._update_stats())
        except Exception as e:
            err = f"⚠️ Ошибка: {str(e)}"
            Clock.schedule_once(lambda dt: self._add_bubble(err, is_user=False))
        finally:
            Clock.schedule_once(lambda dt: setattr(self, 'status_text', "● готова к работе"))

    # ─── НАВИГАЦИЯ ─────────────────────────────────────────────────────────────
    def go_settings(self):
        self.root.current = "settings"

    def go_main(self):
        self.root.current = "main"

    def show_schedule(self):
        self.root.current = "schedule"
        Clock.schedule_once(self._render_schedule, 0.1)

    def _render_schedule(self, dt):
        box = self.root.get_screen("schedule").ids.schedule_box
        box.clear_widgets()
        tasks = self.scheduler.get_today_tasks() if hasattr(self, 'scheduler') else []

        if not tasks:
            box.add_widget(MDLabel(
                text="Задач на сегодня нет.\nСкажи: [color=#00FFD1]«добавь встречу в 14:00»[/color]",
                theme_text_color="Custom",
                text_color=get_color_from_hex("#888899"),
                halign="center",
                markup=True,
                size_hint_y=None,
                height=dp(80),
            ))
            return

        for task in tasks:
            card = MDCard(
                size_hint_y=None,
                height=dp(68),
                padding=[dp(16), dp(10)],
                radius=[dp(10)],
                md_bg_color=get_color_from_hex("#0D0D1A"),
                elevation=0,
                line_color=get_color_from_hex("#00FFD130") if not task['done'] else get_color_from_hex("#22332A"),
            )
            inner = MDBoxLayout(spacing=dp(12))
            color = "#00FFD1" if not task['done'] else "#334433"
            inner.add_widget(MDLabel(
                text=f"[b][color={color}]{task['time']}[/color][/b]",
                markup=True,
                size_hint_x=None,
                width=dp(60),
                theme_text_color="Custom",
                text_color=get_color_from_hex(color),
            ))
            inner.add_widget(MDLabel(
                text=f"{'[s]' if task['done'] else ''}{task['task']}{'[/s]' if task['done'] else ''}",
                markup=True,
                theme_text_color="Custom",
                text_color=get_color_from_hex("#888899" if task['done'] else "#EEEEFF"),
            ))
            card.add_widget(inner)
            box.add_widget(card)

    # ─── НАСТРОЙКИ ─────────────────────────────────────────────────────────────
    def save_settings(self, api_key: str, sheet_id: str):
        if hasattr(self, 'memory'):
            self.memory.save_settings({
                "groq_api_key": api_key,
                "sheets_id":    sheet_id,
                "assistant_name": self.assistant_name_setting,
            })
        if api_key and hasattr(self, 'ai'):
            self.ai.set_api_key(api_key)
            self.groq_api_key = api_key
        if sheet_id and hasattr(self, 'sheets'):
            ok = self.sheets.connect(sheet_id)
            self.sheets_status = "✓ Подключено" if ok else "✗ Ошибка"
            self.sheets_id = sheet_id
        self._add_bubble("✅ Настройки сохранены!", is_user=False)
        self.go_main()

    def sync_to_sheets(self):
        """Синхронизирует расписание с Google Таблицами."""
        def _do():
            if hasattr(self, 'sheets') and hasattr(self, 'scheduler'):
                tasks = self.scheduler.get_today_tasks()
                ok = self.sheets.sync_schedule(tasks)
                msg = "✅ Расписание синхронизировано с Google Таблицами!" if ok \
                      else "⚠️ Ошибка синхронизации. Проверь настройки."
                Clock.schedule_once(lambda dt: self._add_bubble(msg, is_user=False))
        threading.Thread(target=_do, daemon=True).start()


if __name__ == "__main__":
    ARIAApp().run()

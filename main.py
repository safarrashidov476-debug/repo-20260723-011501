# -*- coding: utf-8 -*-
"""
Ovozli Labirint - Ko'zi ojiz foydalanuvchilar uchun audio o'yin
Boshqaruv: ekranni surish (swipe)   - yuqoriga/pastga/chapga/o'ngga yurish
           ikki marta bosish        - ko'rsatmani qayta eshitish
           uzoq bosish (long press) - hozirgi holatni ovozda aytish
           uch marta bosish         - ovozni almashtirish (Madina / Sardor)
"""
import os
import time

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.utils import platform

from audio_manager import AudioManager
from tts_manager import TTSManager
from game_logic import Maze
import texts

# ------------------------------------------------------------------
# GitHub'dagi audio-effektlar manifesti shu manzilda joylashishi kerak.
# Buni o'z GitHub repo manzilingizga almashtiring.
# ------------------------------------------------------------------
MANIFEST_URL = "https://raw.githubusercontent.com/USERNAME/REPO_NAME/main/assets/manifest.json"

DEFAULT_VOICE = "madina"
VOICE_CYCLE = ["madina", "sardor"]


def get_storage_dir():
    """Android va desktop uchun mos yozish mumkin bo'lgan papka."""
    if platform == "android":
        from android.storage import app_storage_path  # noqa
        base = app_storage_path()
    else:
        base = os.path.join(os.path.expanduser("~"), ".ovozli_labirint")
    os.makedirs(base, exist_ok=True)
    return base


class GameWidget(Widget):
    SWIPE_MIN_DISTANCE = 40
    MULTI_TAP_WINDOW = 0.4
    LONG_PRESS_SECONDS = 0.6

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.storage_dir = get_storage_dir()
        self.audio = AudioManager(self.storage_dir, MANIFEST_URL)
        self.tts = TTSManager()
        self.voice = DEFAULT_VOICE
        self.maze = None

        self._touch_start = None
        self._touch_start_time = 0
        self._tap_times = []  # oxirgi tap vaqtlari (double/triple tap uchun)
        self._long_press_ev = None

        Clock.schedule_once(self._boot, 0)

    # ---------------- BOOT / SETUP ----------------
    def _boot(self, dt):
        self.tts.speak(texts.LOADING_TEXT, self.voice)
        Clock.schedule_once(self._download_and_start, 0.2)

    def _download_and_start(self, dt):
        # Faqat tovush effektlari internetdan yuklanadi.
        # Ovozli ko'rsatmalar qurilmaning o'z TTS'i orqali aytiladi -
        # shuning uchun internet bo'lmasa ham o'yin ishlayveradi.
        ok = self.audio.sync_manifest()
        if ok:
            self.audio.download_effects()
        else:
            self.tts.speak(texts.NO_INTERNET_TEXT, self.voice)
        self.start_new_game(first_time=True)

    def start_new_game(self, first_time=False):
        self.maze = Maze(width=6, height=6)
        if first_time:
            self.tts.speak(texts.INSTRUCTIONS_TEXT, self.voice)
        else:
            self.audio.play_effect("start")
        Clock.schedule_once(lambda dt: self._announce_position(), 0.3)

    # ---------------- TOUCH / GESTURE HANDLING ----------------
    def on_touch_down(self, touch):
        self._touch_start = (touch.x, touch.y)
        self._touch_start_time = time.time()
        self._long_press_ev = Clock.schedule_once(
            lambda dt: self._on_long_press(), self.LONG_PRESS_SECONDS
        )
        return True

    def on_touch_up(self, touch):
        if self._long_press_ev:
            self._long_press_ev.cancel()
            self._long_press_ev = None

        if self._touch_start is None:
            return True

        dx = touch.x - self._touch_start[0]
        dy = touch.y - self._touch_start[1]
        distance = (dx ** 2 + dy ** 2) ** 0.5

        if distance < self.SWIPE_MIN_DISTANCE:
            self._register_tap()
        else:
            direction = self._swipe_direction(dx, dy)
            self._move(direction)

        self._touch_start = None
        return True

    @staticmethod
    def _swipe_direction(dx, dy):
        if abs(dx) > abs(dy):
            return "right" if dx > 0 else "left"
        else:
            return "up" if dy > 0 else "down"

    # ---------------- TAP COUNTING (1/2/3 marta bosish) ----------------
    def _register_tap(self):
        now = time.time()
        # Eskirgan taplarni tashlab yuboramiz
        self._tap_times = [t for t in self._tap_times if now - t < self.MULTI_TAP_WINDOW]
        self._tap_times.append(now)

        count = len(self._tap_times)
        if count == 3:
            self._tap_times = []
            self._on_triple_tap()
        else:
            # Ikki tapdan keyin biroz kutamiz - uchinchisi kelishi mumkin
            Clock.schedule_once(self._resolve_tap_count, self.MULTI_TAP_WINDOW)

    def _resolve_tap_count(self, dt):
        count = len(self._tap_times)
        if count == 2:
            self._tap_times = []
            self._on_double_tap()
        elif count == 1:
            self._tap_times = []
            # Bitta bosish - hozircha alohida amal yo'q, e'tiborsiz qoldiramiz

    # ---------------- GAME ACTIONS ----------------
    def _move(self, direction):
        if not self.maze:
            return
        result = self.maze.move(direction)
        if result == "wall":
            self.audio.play_effect("wall")
        elif result == "moved":
            self.audio.play_effect("footstep")
        elif result == "coin":
            self.audio.play_effect("coin")
        elif result == "win":
            self.audio.play_effect("win")
            Clock.schedule_once(lambda dt: self.start_new_game(), 2.0)
            return
        self._announce_position()

    def _announce_position(self):
        pos_text = self.maze.describe_position()
        self.tts.speak(pos_text, self.voice)

    def _on_double_tap(self):
        self.tts.speak(texts.INSTRUCTIONS_TEXT, self.voice)

    def _on_triple_tap(self):
        idx = VOICE_CYCLE.index(self.voice)
        self.voice = VOICE_CYCLE[(idx + 1) % len(VOICE_CYCLE)]
        self.tts.speak(texts.voice_switched_text(self.voice), self.voice)

    def _on_long_press(self):
        self._announce_position()


class OvozliLabirintApp(App):
    def build(self):
        return GameWidget()


if __name__ == "__main__":
    OvozliLabirintApp().run()

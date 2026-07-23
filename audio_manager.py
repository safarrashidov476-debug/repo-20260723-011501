# -*- coding: utf-8 -*-
"""
AudioManager: faqat ovoz EFFEKTLARINI (footstep, wall, coin, win, start)
GitHub'dan avtomatik yuklab oladi, keshlaydi va ijro etadi.

Ovozli ko'rsatmalar va boshqa gapiriladigan matnlar endi tts_manager.py
orqali qurilmaning o'z ovoz tizimida aytiladi - bu fayl faqat qisqa
tovush effektlari bilan ishlaydi.
"""
import os
import json
import urllib.request

from kivy.core.audio import SoundLoader
from kivy.logger import Logger


class AudioManager:
    def __init__(self, storage_dir, manifest_url):
        self.storage_dir = storage_dir
        self.effects_dir = os.path.join(storage_dir, "effects")
        os.makedirs(self.effects_dir, exist_ok=True)

        self.manifest_url = manifest_url
        self.manifest = {}
        self._sounds_cache = {}

    # ---------------- MANIFEST / DOWNLOAD ----------------
    def sync_manifest(self):
        """manifest.json faylini GitHub'dan yuklab oladi."""
        try:
            with urllib.request.urlopen(self.manifest_url, timeout=10) as resp:
                self.manifest = json.loads(resp.read().decode("utf-8"))
            return True
        except Exception as e:
            Logger.warning(f"AudioManager: manifest yuklanmadi -> {e}")
            local_path = os.path.join(self.storage_dir, "manifest.json")
            if os.path.exists(local_path):
                with open(local_path, "r", encoding="utf-8") as f:
                    self.manifest = json.load(f)
                return True
            return False
        finally:
            if self.manifest:
                local_path = os.path.join(self.storage_dir, "manifest.json")
                with open(local_path, "w", encoding="utf-8") as f:
                    json.dump(self.manifest, f, ensure_ascii=False)

    def _download_file(self, url, dest_path):
        if os.path.exists(dest_path):
            return True
        try:
            urllib.request.urlretrieve(url, dest_path)
            return True
        except Exception as e:
            Logger.warning(f"AudioManager: yuklab bo'lmadi {url} -> {e}")
            return False

    def download_effects(self):
        """manifest ichidagi barcha ovoz effektlarini yuklab oladi."""
        effects = self.manifest.get("effects", {})
        for name, url in effects.items():
            dest = os.path.join(self.effects_dir, f"{name}.mp3")
            self._download_file(url, dest)

    # ---------------- PLAYBACK ----------------
    def _get_sound(self, path):
        if path in self._sounds_cache:
            return self._sounds_cache[path]
        if not os.path.exists(path):
            return None
        sound = SoundLoader.load(path)
        self._sounds_cache[path] = sound
        return sound

    def play_effect(self, name):
        path = os.path.join(self.effects_dir, f"{name}.mp3")
        sound = self._get_sound(path)
        if sound:
            sound.play()
        else:
            Logger.warning(f"AudioManager: effekt topilmadi -> {name}")

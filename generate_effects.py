# -*- coding: utf-8 -*-
"""
Bu skript o'yin uchun kerakli barcha tovush effektlarini (footstep, wall,
coin, win, start) NOLDAN, dasturiy tarzda sintez qiladi - hech qanday
tashqi sayt yoki litsenziya kerak emas.

Ishlatish (kompyuteringizda, bir marta):
    pip install numpy
    python generate_effects.py

Natija: assets/audio/effects/ papkasida 5 ta mp3 fayl hosil bo'ladi.
Shundan keyin ularni GitHub repoga qo'shib, push qilsangiz bo'ldi -
ilova ularni avtomatik yuklab oladi.

Eslatma: bu fayl ffmpeg o'rnatilgan bo'lishini talab qiladi (wav -> mp3
konvertatsiyasi uchun). Aksariyat tizimlarda ffmpeg tayyor bo'ladi;
bo'lmasa: sudo apt install ffmpeg (Linux) yoki brew install ffmpeg (Mac).
"""
import os
import struct
import subprocess
import wave
import math
import random

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "assets", "audio", "effects")
SAMPLE_RATE = 44100


def _write_wav(path, samples, sample_rate=SAMPLE_RATE):
    with wave.open(path, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)  # 16-bit
        f.setframerate(sample_rate)
        frames = b"".join(struct.pack("<h", int(s)) for s in samples)
        f.writeframes(frames)


def _envelope(i, n, attack=0.05, release=0.3):
    """Tovush boshida/oxirida keskin "click" bo'lmasligi uchun tekislash."""
    a = int(n * attack)
    r = int(n * release)
    if i < a:
        return i / max(a, 1)
    if i > n - r:
        return max(0.0, (n - i) / max(r, 1))
    return 1.0


def tone(freq, duration, volume=0.5, sample_rate=SAMPLE_RATE, wave_shape="sine"):
    n = int(sample_rate * duration)
    samples = []
    for i in range(n):
        t = i / sample_rate
        if wave_shape == "sine":
            v = math.sin(2 * math.pi * freq * t)
        elif wave_shape == "square":
            v = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
        else:
            v = math.sin(2 * math.pi * freq * t)
        env = _envelope(i, n)
        samples.append(v * env * volume * 32767)
    return samples


def noise_burst(duration, volume=0.4, sample_rate=SAMPLE_RATE):
    n = int(sample_rate * duration)
    samples = []
    for i in range(n):
        env = _envelope(i, n, attack=0.02, release=0.5)
        v = random.uniform(-1, 1)
        samples.append(v * env * volume * 32767)
    return samples


def mix(*sample_lists):
    length = max(len(s) for s in sample_lists)
    result = [0.0] * length
    for s in sample_lists:
        for i, v in enumerate(s):
            result[i] += v
    # Clipping oldini olish
    peak = max(1.0, max(abs(v) for v in result) / 32767)
    return [v / peak for v in result]


def concat(*sample_lists):
    out = []
    for s in sample_lists:
        out.extend(s)
    return out


def build_effects():
    effects = {}

    # Qadam tovushi: qisqa, past chastotali "tap"
    effects["footstep"] = noise_burst(0.08, volume=0.3)

    # Devorga urilish: past, quruq "dud" tovushi
    effects["wall"] = mix(
        tone(120, 0.18, volume=0.5, wave_shape="square"),
        noise_burst(0.1, volume=0.2),
    )

    # Tanga: ikkita yuqori chastotali "ding"
    effects["coin"] = concat(
        tone(880, 0.08, volume=0.4),
        tone(1320, 0.12, volume=0.4),
    )

    # G'alaba: yuqoriga ko'tariluvchi arpeggio
    effects["win"] = concat(
        tone(523, 0.12, volume=0.4),  # Do
        tone(659, 0.12, volume=0.4),  # Mi
        tone(784, 0.12, volume=0.4),  # Sol
        tone(1046, 0.25, volume=0.45),  # Yuqori Do
    )

    # Yangi o'yin boshlanishi: yumshoq ikki tonli signal
    effects["start"] = concat(
        tone(440, 0.15, volume=0.35),
        tone(660, 0.2, volume=0.35),
    )

    return effects


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    effects = build_effects()

    for name, samples in effects.items():
        wav_path = os.path.join(OUTPUT_DIR, f"{name}.wav")
        mp3_path = os.path.join(OUTPUT_DIR, f"{name}.mp3")
        _write_wav(wav_path, samples)

        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame",
                 "-qscale:a", "4", mp3_path],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            os.remove(wav_path)
            print(f"OK: {mp3_path}")
        except Exception as e:
            print(f"Diqqat: mp3'ga o'girib bo'lmadi ({name}), wav qoladi -> {e}")

    print(
        "\nTayyor. assets/audio/effects/ ichidagi fayllarni GitHub repoga "
        "qo'shib push qiling - ilova ularni avtomatik yuklab oladi."
    )


if __name__ == "__main__":
    main()

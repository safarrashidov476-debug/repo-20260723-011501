# -*- coding: utf-8 -*-
"""O'yindagi barcha o'zbekcha matnlar shu yerda saqlanadi."""

INSTRUCTIONS_TEXT = (
    "Xush kelibsiz, Ovozli Labirint o'yiniga. "
    "Ekranni yuqoriga suring, old tomonga yurish uchun. "
    "Ekranni pastga suring, orqaga qaytish uchun. "
    "Ekranni chapga yoki o'ngga suring, shu tomonlarga yurish uchun. "
    "Devorga tegib qolsangiz, maxsus tovush eshitasiz. "
    "Tanga topsangiz, jarangli tovush chalinadi. "
    "Chiqish nuqtasiga yetsangiz, g'alaba tovushi chalinadi va yangi labirint boshlanadi. "
    "Ekranga ikki marta bosing, ushbu ko'rsatmani qayta eshitish uchun. "
    "Ekranni bosib turing, hozirgi joylashuvingizni eshitish uchun. "
    "Ekranga uch marta bosing, ovozni almashtirish uchun. "
    "Omad tilaymiz!"
)

LOADING_TEXT = "Yuklanmoqda, biroz kuting"

NO_INTERNET_TEXT = (
    "Internet aloqasi topilmadi. Iltimos, internetga ulaning va "
    "ilovani qayta oching."
)

VOICE_NAMES_UZ = {
    "madina": "Madina",
    "sardor": "Sardor",
}


def voice_switched_text(voice_key):
    return f"Ovoz almashtirildi: {VOICE_NAMES_UZ.get(voice_key, voice_key)}"

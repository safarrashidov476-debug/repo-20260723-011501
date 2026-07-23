# Ovozli Labirint — ko'zi ojizlar uchun audio o'yin

To'liq ovoz orqali boshqariladigan Android o'yini. Ekranga barmoq bilan
suriladi (yuqoriga/pastga/chapga/o'ngga), har bir harakat tovush effekti
bilan tasdiqlanadi, gapiriladigan barcha matnlar esa qurilmaning o'z ovoz
tizimi (Android TextToSpeech) orqali aytiladi — **hech qanday tashqi
xizmat (Azure va h.k.) yoki qo'shimcha to'lov shart emas.**

## Qanday ishlaydi

- **main.py** — o'yin ekrani, gesturlarni (surish/bosish) ushlaydi
- **game_logic.py** — labirint mantig'i (devor, tanga, chiqish)
- **audio_manager.py** — GitHub'dan tovush EFFEKTLARINI avtomatik yuklab oladi
- **tts_manager.py** — qurilmaning o'z ovoz tizimi orqali gapiradi
  ("Madina" va "Sardor" — ovoz balandligi/tezligi orqali farqlanadigan
  ikki profil)
- **texts.py** — barcha o'zbekcha matnlar shu yerda
- **generate_effects.py** — tovush effektlarini (qadam, devor, tanga,
  g'alaba) noldan dasturiy generatsiya qiladi — tayyor holda
  `assets/audio/effects/` papkasida allaqachon mavjud

## "Madina" va "Sardor" haqida

Bu ikki ovoz — qurilmangizda o'rnatilgan standart TextToSpeech
dvigateli asosida, ovoz balandligi (pitch) va tezligi (rate) orqali
farqlanadi:
- **Madina** — balandroq va odatdagi tezlikda (ayolga xos ohang)
- **Sardor** — pastroq va biroz sekinroq (erkakka xos ohang)

Bu — haqiqiy alohida diktor ovozlari emas, balki bitta tizim ovozining
ikki xil sozlamasi. Agar qurilmangizda bir nechta til/ovoz o'rnatilgan
bo'lsa, ular ham avtomatik tekshiriladi. Natija qurilmadan qurilmaga
biroz farq qilishi mumkin, chunki bu Android'ning o'zida o'rnatilgan
TTS dvigateliga (Google TTS, Samsung TTS va h.k.) bog'liq.

**Eslatma:** o'zbek tili ba'zi eski qurilmalarda TTS dvigateliga
o'rnatilmagan bo'lishi mumkin — bunda tizim rus yoki ingliz tilidagi
standart ovozida gapiradi (baribir tushunarli bo'ladi, faqat talaffuz
tabiiyroq bo'lmasligi mumkin). Zamonaviy Android telefonlarda (Google
TTS orqali) o'zbek tili odatda mavjud.

## O'rnatish qadamlari

### 1. Loyihani GitHub'ga yuklang
```
git init
git remote add origin https://github.com/USERNAME/REPO_NAME.git
git add .
git commit -m "Ovozli Labirint"
git push -u origin main
```

### 2. manifest.json va MANIFEST_URL'ni yangilang
`assets/manifest.json` va `main.py` ichidagi `MANIFEST_URL`dagi
`USERNAME/REPO_NAME` qismlarini o'zingizning GitHub username/repo
nomingizga almashtiring.

Tovush effektlari (`assets/audio/effects/*.mp3`) allaqachon loyiha
ichida tayyor — qo'shimcha hech narsa qilish shart emas, faqat push
qilsangiz bo'ldi.

Agar effektlarni o'zingiz qayta generatsiya qilmoqchi bo'lsangiz:
```
pip install numpy
python generate_effects.py
```
(bu ffmpeg o'rnatilgan bo'lishini talab qiladi)

### 3. GitHub'ga push qiling — APK avtomatik yig'iladi
`.github/workflows/build_apk.yml` fayli har push'da GitHub Actions
orqali avtomatik APK yig'adi:

1. GitHub repo sahifasida **Actions** bo'limiga o'ting
2. Oxirgi ishlagan workflow'ni oching
3. Pastda **Artifacts** qismidan `ovozli-labirint-apk` ni yuklab oling

## Boshqaruv (foydalanuvchi uchun)

| Harakat | Natija |
|---|---|
| Ekranni yuqoriga surish | Oldinga yurish |
| Ekranni pastga surish | Orqaga yurish |
| Ekranni chapga/o'ngga surish | Shu tomonga yurish |
| Ikki marta bosish | Ko'rsatmani qayta eshitish |
| Uch marta bosish | Ovozni almashtirish (Madina ↔ Sardor) |
| Bosib turish (uzoq bosish) | Hozirgi joylashuvni eshitish |

## Eslatma

- Ilova internetsiz ham to'liq ishlaydi — faqat birinchi marta ochilganda
  tovush effektlarini yuklab olish uchun internet kerak (keyinchalik
  keshdan foydalaniladi).
- Barcha gapiriladigan matnlar (ko'rsatma, joylashuv, ovoz almashtirish
  xabari) to'liq offline, qurilmaning o'z TTS tizimi orqali ishlaydi.

# -*- coding: utf-8 -*-
"""
TTSManager: qurilmaning o'rnatilgan ovoz tizimi (Android TextToSpeech)
orqali matnni ovozga aylantiradi. Internet yoki tashqi xizmat (Azure va
h.k.) shart emas - hammasi telefonning o'zida, offline ishlaydi.

"Madina" va "Sardor" - ikki xil ovoz sifatida taqdim etiladi: ovoz
balandligi (pitch) va tezligi (rate) orqali farqlanadi, chunki aksariyat
qurilmalarda faqat bitta standart TTS dvigateli o'rnatilgan bo'ladi.
Agar qurilmada bir nechta ovoz/til o'rnatilgan bo'lsa, ular ham avtomatik
tekshiriladi.
"""
from kivy.utils import platform
from kivy.logger import Logger

try:
    from plyer import tts as plyer_tts
except Exception:
    plyer_tts = None

_android_available = False
if platform == "android":
    try:
        from jnius import autoclass, PythonJavaClass, java_method

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        AndroidTextToSpeech = autoclass("android.speech.tts.TextToSpeech")
        Locale = autoclass("java.util.Locale")

        class _TTSInitListener(PythonJavaClass):
            __javainterfaces__ = ["android/speech/tts/TextToSpeech$OnInitListener"]
            __javacontext__ = "app"

            def __init__(self, callback):
                super().__init__()
                self.callback = callback

            @java_method("(I)V")
            def onInit(self, status):
                self.callback(status)

        _android_available = True
    except Exception as e:
        Logger.warning(f"TTSManager: pyjnius/android tts mavjud emas -> {e}")


class TTSManager:
    # "Ovoz profillari": pitch (balandlik) va rate (tezlik) orqali
    # ikki xil eshitiladigan ovoz hosil qilinadi
    VOICE_PROFILES = {
        "madina": {"pitch": 1.18, "rate": 1.0},
        "sardor": {"pitch": 0.82, "rate": 0.95},
    }

    def __init__(self):
        self.engine = None
        self.ready = False
        self._listener = None  # java listener obyektini "tirik" saqlash uchun

        if platform == "android" and _android_available:
            self._init_android()

    def _init_android(self):
        def on_init(status):
            # status == 0  ->  TextToSpeech.SUCCESS
            self.ready = status == 0
            if self.ready:
                try:
                    self.engine.setLanguage(Locale("uz"))
                except Exception:
                    # Ba'zi qurilmalarda o'zbek tili yo'q bo'lishi mumkin,
                    # bunda tizim standart tilida gapiradi (baribir ishlaydi)
                    pass

        try:
            self._listener = _TTSInitListener(on_init)
            self.engine = AndroidTextToSpeech(
                PythonActivity.mActivity, self._listener
            )
        except Exception as e:
            Logger.warning(f"TTSManager: android tts ishga tushmadi -> {e}")
            self.engine = None

    def speak(self, text, voice="madina"):
        profile = self.VOICE_PROFILES.get(voice, self.VOICE_PROFILES["madina"])

        if platform == "android" and self.engine is not None:
            try:
                self.engine.setPitch(profile["pitch"])
                self.engine.setSpeechRate(profile["rate"])
                QUEUE_FLUSH = 0  # android.speech.tts.TextToSpeech.QUEUE_FLUSH
                self.engine.speak(text, QUEUE_FLUSH, None, "utt_" + str(id(text)))
                return
            except Exception as e:
                Logger.warning(f"TTSManager: android speak xato -> {e}")

        # Desktopda test qilish yoki android tts ishlamay qolgan holat uchun
        if plyer_tts:
            try:
                plyer_tts.speak(message=text)
                return
            except Exception as e:
                Logger.warning(f"TTSManager: plyer tts xato -> {e}")

        Logger.info(f"TTS (matn, ovoz chiqmadi): {text}")

    def stop(self):
        if platform == "android" and self.engine is not None:
            try:
                self.engine.stop()
            except Exception:
                pass

package uz.safar.ttsproxy

import android.media.AudioFormat
import android.os.Bundle
import android.speech.tts.SynthesisCallback
import android.speech.tts.SynthesisRequest
import android.speech.tts.TextToSpeech
import android.speech.tts.TextToSpeechService
import android.speech.tts.UtteranceProgressListener
import android.speech.tts.Voice
import android.util.Log
import java.io.File
import java.io.RandomAccessFile
import java.util.Locale
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/**
 * TTS proxy engine: groups phone number digits into readable blocks before
 * delegating the actual speech synthesis to RHVoice.
 *
 * RHVoice must be installed on the device; this service performs no synthesis
 * of its own, it only pre-processes text and forwards it.
 */
class PhoneGroupingTtsService : TextToSpeechService() {

    private data class VoiceDef(val name: String, val locale: Locale)

    companion object {
        private const val TAG = "PhoneGroupingTts"
        private const val RHVOICE_PACKAGE = "com.github.olga_yakovleva.rhvoice.android"
        private const val ENGINE_INIT_TIMEOUT_SEC = 5L
        private const val SYNTH_TIMEOUT_SEC = 15L
        private const val MIN_VALID_WAV_SIZE = 44L

        // Must match the <voice android:name="..."/> entries in res/xml/tts_engine.xml
        private val VOICES = listOf(
            VoiceDef("uzb", Locale("uz")),
            VoiceDef("rus", Locale("ru")),
            VoiceDef("eng", Locale.ENGLISH)
        )
        private val DEFAULT_VOICE = VOICES[0]

        private fun findVoice(code: String?): VoiceDef? {
            if (code.isNullOrBlank()) return null
            val normalized = code.trim().lowercase(Locale.ROOT)
            return VOICES.firstOrNull {
                it.name == normalized ||
                    it.locale.language.equals(normalized, ignoreCase = true) ||
                    runCatching { it.locale.isO3Language }.getOrNull()?.equals(normalized, ignoreCase = true) == true
            }
        }
    }

    private lateinit var engine: TextToSpeech
    @Volatile private var engineReady = false
    @Volatile private var stopRequested = false
    @Volatile private var activeLocale: Locale = DEFAULT_VOICE.locale
    @Volatile private var appliedLocale: Locale? = null
    private val initLatch = CountDownLatch(1)

    override fun onCreate() {
        super.onCreate()
        engine = TextToSpeech(this, { status ->
            engineReady = status == TextToSpeech.SUCCESS
            if (!engineReady) {
                Log.w(TAG, "Underlying RHVoice engine failed to initialize (status=$status)")
            }
            initLatch.countDown()
        }, RHVOICE_PACKAGE)
    }

    override fun onDestroy() {
        if (::engine.isInitialized) {
            runCatching { engine.shutdown() }
        }
        super.onDestroy()
    }

    // ---------------------------------------------------------------------
    // Legacy language-based API (still required, always invoked on API 21+
    // for clients that haven't migrated to the Voice API).
    // ---------------------------------------------------------------------

    override fun onIsLanguageAvailable(lang: String?, country: String?, variant: String?): Int {
        return if (findVoice(lang) != null) TextToSpeech.LANG_AVAILABLE else TextToSpeech.LANG_NOT_SUPPORTED
    }

    override fun onLoadLanguage(lang: String?, country: String?, variant: String?): Int {
        val voice = findVoice(lang) ?: return TextToSpeech.LANG_NOT_SUPPORTED
        activeLocale = voice.locale
        return TextToSpeech.LANG_AVAILABLE
    }

    override fun onGetLanguage(): Array<String> = try {
        val locale = activeLocale
        arrayOf(locale.isO3Language, locale.isO3Country, "")
    } catch (e: Exception) {
        Log.w(TAG, "Failed to resolve ISO3 locale, falling back to English", e)
        arrayOf("eng", "", "")
    }

    // ---------------------------------------------------------------------
    // Modern Voice-based API.
    // ---------------------------------------------------------------------

    override fun onGetVoices(): MutableList<Voice> =
        VOICES.map { v ->
            Voice(
                v.name,
                v.locale,
                Voice.QUALITY_NORMAL,
                Voice.LATENCY_NORMAL,
                /* requiresNetworkConnection = */ false,
                emptySet()
            )
        }.toMutableList()

    override fun onGetDefaultVoiceNameFor(lang: String?, country: String?, variant: String?): String =
        findVoice(lang)?.name ?: DEFAULT_VOICE.name

    override fun onIsValidVoiceName(voiceName: String?): Int =
        if (VOICES.any { it.name == voiceName }) TextToSpeech.SUCCESS else TextToSpeech.ERROR

    override fun onLoadVoice(voiceName: String?): Int {
        val voice = VOICES.firstOrNull { it.name == voiceName } ?: return TextToSpeech.ERROR
        activeLocale = voice.locale
        return TextToSpeech.SUCCESS
    }

    override fun onStop() {
        stopRequested = true
        if (::engine.isInitialized) {
            runCatching { engine.stop() }
        }
    }

    // ---------------------------------------------------------------------
    // Text pre-processing.
    // ---------------------------------------------------------------------

    private fun groupPhoneNumbers(text: String): String {
        var result = text
        // +998 followed by 9 digits -> +998 XX XXX XX XX
        result = result.replace(
            Regex("(?<!\\d)\\+998(\\d{2})(\\d{3})(\\d{2})(\\d{2})(?!\\d)"),
            "+998 $1 $2 $3 $4"
        )
        // bare 9-digit local numbers -> XX XXX XX XX
        result = result.replace(
            Regex("(?<!\\d)(\\d{2})(\\d{3})(\\d{2})(\\d{2})(?!\\d)"),
            "$1 $2 $3 $4"
        )
        return result
    }

    /**
     * Splits text at sentence/clause punctuation so the first chunk can be
     * synthesized and streamed quickly instead of waiting on the whole utterance.
     */
    private fun splitIntoChunks(text: String): List<String> {
        val parts = text.split(Regex("(?<=[.!?;:,])\\s+"))
            .map { it.trim() }
            .filter { it.isNotEmpty() }
        return parts.ifEmpty { listOf(text).filter { it.isNotEmpty() } }
    }

    // ---------------------------------------------------------------------
    // Synthesis.
    // ---------------------------------------------------------------------

    override fun onSynthesizeText(request: SynthesisRequest, callback: SynthesisCallback) {
        stopRequested = false

        if (!engineReady) {
            initLatch.await(ENGINE_INIT_TIMEOUT_SEC, TimeUnit.SECONDS)
        }
        if (!engineReady) {
            Log.e(TAG, "RHVoice engine is not ready, cannot synthesize")
            callback.error()
            return
        }

        applyRequestSettings(request)

        val fullText = groupPhoneNumbers(request.charSequenceText.toString())
        val chunks = splitIntoChunks(fullText)
        if (chunks.isEmpty()) {
            callback.error()
            return
        }

        var started = false

        for ((index, chunk) in chunks.withIndex()) {
            if (stopRequested) break

            val outFile = File(cacheDir, "tts_${System.nanoTime()}_$index.wav")
            try {
                if (synthesizeChunkToFile(chunk, outFile)) {
                    if (stopRequested) break
                    if (outFile.exists() && outFile.length() > MIN_VALID_WAV_SIZE) {
                        if (streamWavToCallback(outFile, callback, isFirstChunk = !started)) {
                            started = true
                        }
                    } else {
                        Log.w(TAG, "Chunk $index produced no usable audio, skipping")
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to synthesize/stream chunk $index", e)
            } finally {
                outFile.delete()
            }
        }

        if (!started) {
            callback.error()
        } else {
            callback.done()
        }
    }

    /** Applies the requested voice/language, speech rate, and pitch to the delegate engine. */
    private fun applyRequestSettings(request: SynthesisRequest) {
        val requestedVoice = findVoice(request.voiceName) ?: findVoice(request.language)
        val targetLocale = requestedVoice?.locale ?: activeLocale
        if (appliedLocale != targetLocale) {
            val result = engine.setLanguage(targetLocale)
            if (result >= TextToSpeech.LANG_AVAILABLE) {
                appliedLocale = targetLocale
                activeLocale = targetLocale
            } else {
                Log.w(TAG, "Delegate engine rejected locale $targetLocale (result=$result)")
            }
        }

        if (request.speechRate > 0) {
            engine.setSpeechRate(request.speechRate / 100f)
        }
        if (request.pitch > 0) {
            engine.setPitch(request.pitch / 100f)
        }
    }

    /**
     * Synthesizes [chunk] into [outFile] and blocks until the delegate engine
     * reports completion, an error, or the timeout elapses.
     * Returns false if the request could not even be enqueued.
     */
    private fun synthesizeChunkToFile(chunk: String, outFile: File): Boolean {
        val latch = CountDownLatch(1)
        val utteranceId = "u${System.nanoTime()}"

        engine.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {}
            override fun onDone(utteranceId: String?) { latch.countDown() }
            @Deprecated("Deprecated in Java", ReplaceWith(""))
            override fun onError(utteranceId: String?) { latch.countDown() }
            override fun onError(utteranceId: String?, errorCode: Int) { latch.countDown() }
        })

        val params = Bundle()
        val enqueueResult = engine.synthesizeToFile(chunk, params, outFile, utteranceId)
        if (enqueueResult != TextToSpeech.SUCCESS) {
            Log.w(TAG, "synthesizeToFile failed to enqueue (result=$enqueueResult)")
            return false
        }

        var waitedMs = 0L
        val stepMs = 50L
        val timeoutMs = TimeUnit.SECONDS.toMillis(SYNTH_TIMEOUT_SEC)
        while (latch.count > 0 && !stopRequested && waitedMs < timeoutMs) {
            latch.await(stepMs, TimeUnit.MILLISECONDS)
            waitedMs += stepMs
        }
        return true
    }

    /**
     * Parses the WAV header of [file] (robust to extra/odd-sized chunks such as
     * "LIST" or "fact", unlike a fixed 44-byte offset assumption), then streams
     * the raw PCM data to [callback].
     */
    private fun streamWavToCallback(file: File, callback: SynthesisCallback, isFirstChunk: Boolean): Boolean {
        RandomAccessFile(file, "r").use { raf ->
            if (raf.length() < 12) return false
            val riffHeader = ByteArray(12)
            raf.readFully(riffHeader)
            val isRiffWave = riffHeader[0] == 'R'.code.toByte() && riffHeader[1] == 'I'.code.toByte() &&
                riffHeader[8] == 'W'.code.toByte() && riffHeader[9] == 'A'.code.toByte()
            if (!isRiffWave) {
                Log.w(TAG, "File ${file.name} is not a valid RIFF/WAVE file")
                return false
            }

            var sampleRate = 22050
            var channels = 1
            var bitsPerSample = 16
            var dataChunkFound = false

            while (!dataChunkFound && raf.filePointer + 8 <= raf.length()) {
                val chunkIdBytes = ByteArray(4)
                raf.readFully(chunkIdBytes)
                val chunkId = String(chunkIdBytes, Charsets.US_ASCII)
                val chunkSize = readLeInt(raf)
                if (chunkSize < 0) break

                when (chunkId) {
                    "fmt " -> {
                        val fmt = ByteArray(chunkSize)
                        raf.readFully(fmt)
                        if (fmt.size >= 16) {
                            channels = leShort(fmt, 2)
                            sampleRate = leInt(fmt, 4)
                            bitsPerSample = leShort(fmt, 14)
                        }
                    }
                    "data" -> {
                        dataChunkFound = true
                    }
                    else -> {
                        raf.skipBytes(chunkSize)
                    }
                }
                // RIFF chunks are word-aligned; skip the pad byte for odd sizes.
                if (chunkId != "data" && chunkSize % 2 != 0 && raf.filePointer < raf.length()) {
                    raf.skipBytes(1)
                }
            }

            if (!dataChunkFound) {
                Log.w(TAG, "No 'data' chunk found in ${file.name}")
                return false
            }

            if (isFirstChunk) {
                val audioFormat = if (bitsPerSample == 8) {
                    AudioFormat.ENCODING_PCM_8BIT
                } else {
                    AudioFormat.ENCODING_PCM_16BIT
                }
                callback.start(sampleRate, audioFormat, channels)
            }

            val buffer = ByteArray(callback.maxBufferSize)
            var bytesRead: Int
            while (!stopRequested && raf.read(buffer).also { bytesRead = it } > 0) {
                callback.audioAvailable(buffer, 0, bytesRead)
            }
        }
        return true
    }

    private fun readLeInt(raf: RandomAccessFile): Int {
        val b = ByteArray(4)
        raf.readFully(b)
        return leInt(b, 0)
    }

    private fun leInt(b: ByteArray, off: Int): Int =
        (b[off].toInt() and 0xFF) or
            ((b[off + 1].toInt() and 0xFF) shl 8) or
            ((b[off + 2].toInt() and 0xFF) shl 16) or
            ((b[off + 3].toInt() and 0xFF) shl 24)

    private fun leShort(b: ByteArray, off: Int): Int =
        (b[off].toInt() and 0xFF) or ((b[off + 1].toInt() and 0xFF) shl 8)
}

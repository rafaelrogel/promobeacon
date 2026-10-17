package com.promobeacon.manager.domain.model

import java.text.Normalizer

/**
 * IEEE 802.11 SSID Standards & Safe Transliteration Helper
 */
object SsidStandardsHelper {
    const val MAX_SSID_BYTES = 32

    fun getByteCount(text: String): Int {
        return text.toByteArray(Charsets.UTF_8).size
    }

    /**
     * Transliterates accented characters (ã -> a, ç -> c), replaces special symbols (• -> -),
     * strips emojis and unsafe chars, and securely clamps to 32 BYTES.
     */
    fun toSafeSsid(text: String): String {
        if (text.isBlank()) return "PromoBeacon_WiFi"
        
        // 1. Decompose unicode accents
        val nfd = Normalizer.normalize(text, Normalizer.Form.NFD)
        var clean = nfd.replace("\\p{InCombiningDiacriticalMarks}+".toRegex(), "")
        
        // 2. Replace bullet points, pipes, slashes with hyphens
        clean = clean.replace("[•|/]".toRegex(), "-")
        
        // 3. Remove non-ASCII and emojis
        clean = clean.replace("[^\\x20-\\x7E]".toRegex(), "")
        
        // 4. Remove dangerous shell/HTML injection chars (<, >, ", `, \)
        clean = clean.replace("[<>\"`\\\\]".toRegex(), "")
        clean = clean.replace("\\s+".toRegex(), " ").trim()

        // 5. Clamp to 32 bytes
        var result = clean
        while (result.toByteArray(Charsets.UTF_8).size > MAX_SSID_BYTES && result.isNotEmpty()) {
            result = result.dropLast(1)
        }

        return if (result.isBlank()) "PromoBeacon_WiFi" else result
    }

    /**
     * Returns a human-friendly standard warning if the SSID deviates from the IEEE 802.11 standard.
     */
    fun getStandardWarning(text: String): String? {
        val bytes = getByteCount(text)
        if (bytes > MAX_SSID_BYTES) {
            return "Aviso do Padrão Wi-Fi (IEEE 802.11): O nome possui $bytes bytes e excede o limite universal de 32 bytes. Aparelhos podem falhar ao conectar."
        }
        val hasNonAscii = text.any { it.code < 32 || it.code > 126 }
        if (hasNonAscii) {
            return "Padrão Wi-Fi: Acentos (ã, é, ç) e emojis no Wi-Fi podem aparecer desconfigurados no Windows ou celulares antigos. Sugerimos usar nome simplificado no Wi-Fi e completo no portal."
        }
        val hasUnsafe = text.any { it in listOf('<', '>', '"', '`', '\\') }
        if (hasUnsafe) {
            return "Atenção: Caracteres especiais (<, >, \", `, \\) serão removidos pelo rádio do dispositivo."
        }
        return null
    }
}

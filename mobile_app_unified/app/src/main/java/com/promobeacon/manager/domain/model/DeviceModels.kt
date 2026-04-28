package com.promobeacon.manager.domain.model

/**
 * Device Mode Enum
 */
enum class DeviceMode(val value: Byte) {
    MODE_G(0x00),
    MODE_E(0x01),
    UNKNOWN(0xFF.toByte());

    companion object {
        fun fromValue(value: Byte): DeviceMode {
            return entries.find { it.value == value } ?: UNKNOWN
        }
    }
}

/**
 * Connection State Enum
 */
enum class ConnectionState {
    DISCONNECTED,
    CONNECTING,
    CONNECTED,
    DISCONNECTING
}

/**
 * Device Status Data Class
 *
 * @property mode Current device mode
 * @property isAdvertising Whether advertising
 * @property isConnected Whether connected
 * @property uptimeMs Uptime in milliseconds
 * @property rssi Signal strength in dBm
 * @property clientCount Connected client count
 * @property promoText Promotion text
 */
data class DeviceStatus(
    val mode: DeviceMode = DeviceMode.UNKNOWN,
    val isAdvertising: Boolean = false,
    val isConnected: Boolean = false,
    val uptimeMs: Long = 0,
    val rssi: Int = 0,
    val clientCount: Int = 0,
    val promoText: String = ""
)

/**
 * G Mode Configuration Data Class
 *
 * @property ssid WiFi network name
 * @property password WiFi password (empty string for open network)
 * @property promoText Promotion text
 * @property portalHtml Captive portal HTML content
 */
data class GModeConfig(
    val ssid: String = "PromoBeacon",
    val password: String = "",
    val promoText: String = "VISITE-NOS",
    val portalHtml: String = "",
    val newAdminPassword: String = ""
)

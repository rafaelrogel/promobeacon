package com.promobeacon.manager.domain.repository

import com.promobeacon.manager.domain.model.*
import kotlinx.coroutines.flow.Flow

/**
 * Device Repository Interface
 * Defines standard methods for communicating with PromoBeacon devices
 */
interface DeviceRepository {
    /**
     * Scan for nearby devices
     *
     * @param timeoutMs Scan timeout in milliseconds
     * @return Device list Flow
     */
    fun scanDevices(timeoutMs: Int = 10000): Flow<List<ScannedDevice>>

    /**
     * Stop scanning
     */
    fun stopScan()

    /**
     * Connect to a device
     *
     * @param device Target device
     * @return Whether connection was successful
     */
    suspend fun connect(device: ScannedDevice): Result<Unit>

    /**
     * Disconnect
     */
    suspend fun disconnect()

    /**
     * Get connection status
     *
     * @return Connection status Flow
     */
    fun getConnectionState(): Flow<ConnectionState>

    /**
     * Get device status
     *
     * @return Device status Flow
     */
    fun getDeviceStatus(): Flow<DeviceStatus>

    /**
     * Update G mode configuration
     *
     * @param config G mode configuration
     * @return Operation result
     */
    suspend fun updateGModeConfig(config: GModeConfig): Result<Unit>

    /**
     * Read G mode configuration
     *
     * @return G mode configuration
     */
    suspend fun readGModeConfig(): Result<GModeConfig>

    /**
     * Reboot device
     *
     * @return Operation result
     */
    suspend fun reboot(): Result<Unit>

    /**
     * Factory reset
     *
     * @return Operation result
     */
    suspend fun resetToDefaults(): Result<Unit>

    /**
     * Export client statistics to CSV file
     *
     * @param deviceIp Device IP address
     * @return Operation result with saved file path
     */
    suspend fun exportStatsToCsv(deviceIp: String): Result<String>

    /**
     * Upload custom portal page content
     *
     * @param htmlContent HTML content
     * @return Upload progress Flow with percentage (0-100) and status
     */
    suspend fun uploadPortalContent(htmlContent: String): Flow<UploadProgress>
}

/**
 * Scanned Device Data Class
 *
 * @property name Device name
 * @property address MAC address
 * @property rssi Signal strength
 * @property isPromoBeacon Whether this is a PromoBeacon device
 */
data class ScannedDevice(
    val name: String,
    val address: String,
    val rssi: Int,
    val isPromoBeacon: Boolean = name.contains("PromoBeacon", ignoreCase = true)
) {
    /**
     * Get signal level
     */
    fun getSignalLevel(): SignalLevel {
        return when {
            rssi >= -50 -> SignalLevel.EXCELLENT
            rssi >= -60 -> SignalLevel.GOOD
            rssi >= -70 -> SignalLevel.FAIR
            else -> SignalLevel.POOR
        }
    }
}

/**
 * Upload progress status
 */
sealed class UploadProgress {
    /**
     * Upload started
     */
    data class Started(val totalBytes: Int) : UploadProgress()

    /**
     * Upload in progress
     */
    data class InProgress(
        val percentage: Int,
        val sentBytes: Int,
        val totalChunks: Int
    ) : UploadProgress()

    /**
     * Upload completed
     */
    data class Completed(val totalBytes: Int) : UploadProgress()

    /**
     * Upload error
     */
    data class Error(val message: String) : UploadProgress()
}

/**
 * Signal level enum
 */
enum class SignalLevel {
    EXCELLENT,
    GOOD,
    FAIR,
    POOR
}

package com.promobeacon.manager.data.repository

import android.util.Log
import com.promobeacon.manager.data.ble.BleClient
import com.promobeacon.manager.data.ble.BleConstants
import com.promobeacon.manager.data.ble.ConnectionState as BleConnectionState
import com.promobeacon.manager.domain.model.*
import com.promobeacon.manager.domain.repository.DeviceRepository
import com.promobeacon.manager.domain.repository.ScannedDevice
import com.promobeacon.manager.domain.repository.UploadProgress
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import javax.inject.Inject
import javax.inject.Singleton
import dagger.hilt.android.qualifiers.ApplicationContext

/**
 * Device Repository Implementation
 */
@Singleton
class DeviceRepositoryImpl @Inject constructor(
    private val bleClient: BleClient,
    @ApplicationContext private val context: android.content.Context
) : DeviceRepository {

    private val gson = Gson()

    // Cached configuration
    @Volatile
    private var cachedGModeConfig: GModeConfig? = null

    override fun scanDevices(timeoutMs: Int): Flow<List<ScannedDevice>> = flow {
        bleClient.startScan()
        delay(200)

        val startTime = System.currentTimeMillis()
        while (System.currentTimeMillis() - startTime < timeoutMs) {
            val error = bleClient.scanError.value
            if (error != null) {
                bleClient.stopScan()
                throw Exception("BLE scan failed with error code: $error")
            }
            emit(bleClient.scanResults.value)
            delay(500)
        }

        bleClient.stopScan()
        emit(bleClient.scanResults.value)
    }.flowOn(Dispatchers.IO)

    override fun stopScan() {
        bleClient.stopScan()
    }

    override suspend fun connect(device: ScannedDevice): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            bleClient.connect(device).collect { state ->
                if (state == BleConnectionState.CONNECTED || state == BleConnectionState.DISCONNECTED) {
                    return@collect
                }
            }

            if (bleClient.connectionState.value == BleConnectionState.CONNECTED) {
                bleClient.readStatus()
                Result.success(Unit)
            } else {
                Result.failure(Exception("Connection failed"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun disconnect() = withContext(Dispatchers.IO) {
        bleClient.disconnect()
    }

    override fun getConnectionState(): Flow<com.promobeacon.manager.domain.model.ConnectionState> {
        return bleClient.connectionState.map { state ->
            when (state) {
                BleConnectionState.CONNECTED -> com.promobeacon.manager.domain.model.ConnectionState.CONNECTED
                BleConnectionState.CONNECTING -> com.promobeacon.manager.domain.model.ConnectionState.CONNECTING
                BleConnectionState.DISCONNECTING -> com.promobeacon.manager.domain.model.ConnectionState.DISCONNECTING
                BleConnectionState.DISCONNECTED -> com.promobeacon.manager.domain.model.ConnectionState.DISCONNECTED
            }
        }
    }

    override fun getDeviceStatus(): Flow<DeviceStatus> {
        return bleClient.deviceStatus.map { data ->
            parseStatus(data)
        }
    }

    override suspend fun updateGModeConfig(config: GModeConfig): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            // Write promotion text (this also updates AP SSID on firmware side)
            val promoSuccess = bleClient.writePromoText(config.promoText)
            if (!promoSuccess) {
                return@withContext Result.failure(Exception("Failed to write promotion text"))
            }

            // Write SSID if it differs from promo text
            if (config.ssid != config.promoText) {
                val ssidSuccess = bleClient.writeSsid(config.ssid)
                if (!ssidSuccess) {
                    return@withContext Result.failure(Exception("Failed to write SSID"))
                }
            }

            // Write WiFi password if provided
            if (config.password.isNotEmpty()) {
                val passwordSuccess = bleClient.writeWifiPassword(config.password)
                if (!passwordSuccess) {
                    return@withContext Result.failure(Exception("Failed to write WiFi password"))
                }
            }

            // Update cache
            cachedGModeConfig = config

            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun readGModeConfig(): Result<GModeConfig> = withContext(Dispatchers.IO) {
        cachedGModeConfig?.let {
            return@withContext Result.success(it)
        }
        try {
            val promoText = bleClient.readPromoText() ?: ""
            val deviceName = bleClient.readDeviceName() ?: promoText
            val config = GModeConfig(
                ssid = deviceName,
                promoText = promoText,
                password = "",
                newAdminPassword = ""
            )
            cachedGModeConfig = config
            Result.success(config)
        } catch (e: Exception) {
            val config = cachedGModeConfig ?: GModeConfig()
            Result.success(config)
        }
    }

    override suspend fun reboot(): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val success = bleClient.writeConfig(BleConstants.CMD_REBOOT.toByte())
            if (success) Result.success(Unit) else Result.failure(Exception("Reboot command failed"))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    override suspend fun resetToDefaults(): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val success = bleClient.writeConfig(BleConstants.CMD_RESET_DEFAULTS.toByte())

            if (success) {
                // Clear cache
                cachedGModeConfig = null
                delay(500) // Wait for reset to complete
                Result.success(Unit)
            } else {
                Result.failure(Exception("Factory reset failed"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    /**
     * Parse device status data
     *
     * Status data format (DeviceStatus):
     * - Byte 0: Current mode (0=G, 1=E)
     * - Byte 1: Advertising status (0=not advertising, 1=advertising)
     * - Byte 2: Connection status (0=disconnected, 1=connected)
     * - Byte 3-6: Uptime (uint32, milliseconds)
     * - Byte 7: RSSI
     * - Byte 8: Client count
     * - Byte 9-28: Message (20 bytes)
     * - Byte 29-60: Promotion text (32 bytes)
     *
     * Note: The packed StatusPacket (CHAR_STATS) now uses 8 bytes:
     * [flags(1) | clients(1) | session_duration_sec(4) | portal_avg(1) | battery(1)]
     */
    private fun parseStatus(data: ByteArray?): DeviceStatus {
        if (data == null || data.size < 30) {
            return DeviceStatus()
        }
        
        Log.d(tag, "Received status packet: size=${data.size}, auth_byte=${data.getOrNull(97)}")

        return try {
            val modeValue = data.getOrNull(0) ?: 0.toByte()
            val isAdvertising = data.getOrNull(1) == 1.toByte()
            val isConnected = data.getOrNull(2) == 1.toByte()
            
            val uptimeMs = ((data.getOrNull(3)?.toInt() ?: 0) and 0xFF) or
                    (((data.getOrNull(4)?.toInt() ?: 0) and 0xFF) shl 8) or
                    (((data.getOrNull(5)?.toInt() ?: 0) and 0xFF) shl 16) or
                    (((data.getOrNull(6)?.toInt() ?: 0) and 0xFF) shl 24)
            
            val rssi = data.getOrNull(7)?.toInt() ?: 0
            val clientCount = data.getOrNull(8)?.toInt() ?: 0

            // Promo text starts at index 31 (after mode(1), adv(1), conn(1), uptime(4), rssi(1), clients(1), wifi(1), message(21))
            val promoTextBytes = data.copyOfRange(31, minOf(64, data.size))
            val promoText = String(promoTextBytes, Charsets.UTF_8).trimEnd { it.code == 0 }
            
            // Authentication bit added at the absolute end of the status packet (index 97)
            val isAuthenticated = data.getOrNull(97) == 1.toByte()

            DeviceStatus(
                mode = DeviceMode.fromValue(modeValue),
                isAdvertising = isAdvertising,
                isConnected = isConnected,
                isAuthenticated = isAuthenticated,
                uptimeMs = uptimeMs.toLong() and 0xFFFFFFFFL,
                rssi = rssi,
                clientCount = clientCount,
                promoText = promoText
            )
        } catch (e: Exception) {
            DeviceStatus()
        }
    }

    override suspend fun uploadPortalContent(htmlContent: String): Flow<UploadProgress> = flow {
        try {
            // Validate HTML content
            if (htmlContent.isBlank()) {
                emit(UploadProgress.Error("HTML content cannot be empty"))
                return@flow
            }

            val contentBytes = htmlContent.toByteArray(Charsets.UTF_8)
            val totalSize = contentBytes.size

            // Check size limit (32KB)
            val maxSize = 32 * 1024
            if (totalSize > maxSize) {
                emit(UploadProgress.Error("HTML content too large, max ${maxSize / 1024}KB supported"))
                return@flow
            }

            emit(UploadProgress.Started(totalSize))

            // Calculate CRC32
            val crc32 = bleClient.calculateCrc32(contentBytes)
            Log.d(tag, "Starting portal upload: size=$totalSize, crc=0x${crc32.toString(16)}")

            // Start upload
            val startSuccess = bleClient.portalStartUpload(totalSize, crc32)
            if (!startSuccess) {
                emit(UploadProgress.Error("Failed to start upload"))
                return@flow
            }

            // Chunked transfer
            val chunkSize = BleConstants.PORTAL_CHUNK_SIZE
            val totalChunks = (totalSize + chunkSize - 1) / chunkSize
            var sentChunks = 0

            for (i in 0 until totalSize step chunkSize) {
                val endIndex = minOf(i + chunkSize, totalSize)
                val chunk = contentBytes.copyOfRange(i, endIndex)

                val chunkNum = i / chunkSize
                val sendSuccess = bleClient.portalSendChunk(chunkNum, chunk)

                if (!sendSuccess) {
                    bleClient.portalAbortUpload()
                    emit(UploadProgress.Error("Failed to transfer chunk ${chunkNum + 1}"))
                    return@flow
                }

                sentChunks++
                val progress = (sentChunks.toFloat() / totalChunks * 100).toInt()
                emit(UploadProgress.InProgress(progress, sentChunks, totalChunks))

                // Delay to avoid BLE buffer overflow
                delay(30)
            }

            // Complete upload
            val completeSuccess = bleClient.portalCompleteUpload()
            if (!completeSuccess) {
                emit(UploadProgress.Error("Failed to complete upload"))
                return@flow
            }

            // Wait for device processing and verification
            delay(500)

            // Request device status to confirm
            bleClient.portalRequestStatus()

            emit(UploadProgress.Completed(totalSize))
            Log.i(tag, "Portal upload completed successfully")

        } catch (e: Exception) {
            Log.e(tag, "Portal upload failed", e)
            bleClient.portalAbortUpload()
            emit(UploadProgress.Error("Upload failed: ${e.message}"))
        }
    }.flowOn(Dispatchers.IO)

    override suspend fun exportStatsToCsv(deviceIp: String): Result<String> = withContext(Dispatchers.IO) {
        val url = URL("http://$deviceIp/stats.csv")
        val connection = url.openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "GET"
            connection.connectTimeout = 10000
            connection.readTimeout = 30000

            val responseCode = connection.responseCode
            if (responseCode != HttpURLConnection.HTTP_OK) {
                val errorBody = connection.errorStream?.bufferedReader()?.use { it.readText() }
                return@withContext Result.failure(Exception("HTTP error: $responseCode - $errorBody"))
            }

            val inputStream = connection.inputStream
            val csvContent = inputStream.bufferedReader().use { it.readText() }

            if (csvContent.isEmpty()) {
                return@withContext Result.failure(Exception("No data received"))
            }

            // Generate file name
            val timestamp = java.text.SimpleDateFormat("yyyyMMdd_HHmmss", java.util.Locale.getDefault())
                .format(java.util.Date())
            val fileName = "promobeacon_stats_$timestamp.csv"

            // Save to external files directory
            val file = File(context.getExternalFilesDir(null), fileName)
            file.writeText(csvContent)

            Log.d(tag, "CSV saved to: ${file.absolutePath}")
            Result.success(file.absolutePath)
        } catch (e: Exception) {
            Log.e(tag, "CSV export failed", e)
            Result.failure(e)
        } finally {
            connection.disconnect()
        }
    }

    private val tag = "DeviceRepository"
}

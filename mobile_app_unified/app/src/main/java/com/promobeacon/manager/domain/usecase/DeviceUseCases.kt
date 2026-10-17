package com.promobeacon.manager.domain.usecase

import com.promobeacon.manager.domain.model.*
import com.promobeacon.manager.domain.repository.DeviceRepository
import com.promobeacon.manager.domain.repository.ScannedDevice
import com.promobeacon.manager.domain.repository.UploadProgress
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import java.nio.charset.StandardCharsets
import javax.inject.Inject

/**
 * Scan Devices Use Case
 */
class ScanDevicesUseCase @Inject constructor(
    private val repository: DeviceRepository
) {
    operator fun invoke(timeoutMs: Int = 10000): Flow<List<ScannedDevice>> {
        return repository.scanDevices(timeoutMs)
    }

    fun stop() {
        repository.stopScan()
    }
}

/**
 * Connect Device Use Case
 */
class ConnectDeviceUseCase @Inject constructor(
    private val repository: DeviceRepository
) {
    suspend operator fun invoke(device: ScannedDevice): Result<Unit> {
        return repository.connect(device)
    }
}

/**
 * Disconnect Device Use Case
 */
class DisconnectDeviceUseCase @Inject constructor(
    private val repository: DeviceRepository
) {
    suspend operator fun invoke(): Result<Unit> {
        return try {
            repository.disconnect()
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}

/**
 * Get Connection State Use Case
 */
class GetConnectionStateUseCase @Inject constructor(
    private val repository: DeviceRepository
) {
    operator fun invoke(): Flow<ConnectionState> {
        return repository.getConnectionState()
    }
}

/**
 * Get Device Status Use Case
 */
class GetDeviceStatusUseCase @Inject constructor(
    private val repository: DeviceRepository
) {
    operator fun invoke(): Flow<DeviceStatus> {
        return repository.getDeviceStatus()
    }
}

/**
 * Update G Mode Configuration Use Case
 */
class UpdateGModeConfigUseCase @Inject constructor(
    private val repository: DeviceRepository
) {
    suspend operator fun invoke(config: GModeConfig): Result<Unit> {
        // Validate configuration using IEEE 802.11 standards (max 32 bytes)
        val ssidBytes = config.ssid.toByteArray(Charsets.UTF_8).size
        if (ssidBytes > 32) {
            return Result.failure(IllegalArgumentException("SSID excede o limite universal de 32 bytes ($ssidBytes bytes). Ajuste o nome da rede."))
        }
        if (config.ssid.isBlank()) {
            return Result.failure(IllegalArgumentException("SSID cannot be empty"))
        }

        return repository.updateGModeConfig(config)
    }
}

/**
 * Read G Mode Configuration Use Case
 */
class ReadGModeConfigUseCase @Inject constructor(
    private val repository: DeviceRepository
) {
    suspend operator fun invoke(): Result<GModeConfig> {
        return repository.readGModeConfig()
    }
}

/**
 * Refresh G Mode Configuration Use Case
 */
class RefreshGModeConfigUseCase @Inject constructor(
    private val repository: DeviceRepository
) {
    suspend operator fun invoke(): Result<GModeConfig> {
        return repository.refreshGModeConfig()
    }
}

/**
 * Reboot Device Use Case
 */
class RebootDeviceUseCase @Inject constructor(
    private val repository: DeviceRepository
) {
    suspend operator fun invoke(): Result<Unit> {
        return repository.reboot()
    }
}

/**
 * Factory Reset Use Case
 */
class ResetToDefaultsUseCase @Inject constructor(
    private val repository: DeviceRepository
) {
    suspend operator fun invoke(): Result<Unit> {
        return repository.resetToDefaults()
    }
}

/**
 * Export Statistics to CSV Use Case
 */
class ExportStatsToCsvUseCase @Inject constructor(
    private val repository: DeviceRepository
) {
    suspend operator fun invoke(deviceIp: String): Result<String> {
        if (deviceIp.isBlank()) {
            return Result.failure(IllegalArgumentException("Device IP address cannot be empty"))
        }
        // Simple IP format validation
        val ipPattern = Regex("^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}$")
        if (!ipPattern.matches(deviceIp)) {
            return Result.failure(IllegalArgumentException("Invalid IP address format"))
        }
        return repository.exportStatsToCsv(deviceIp)
    }
}

/**
 * Upload Portal Page Use Case
 *
 * Validates captive portal HTML for offline compliance:
 * - Content cannot be blank
 * - Content must not exceed max payload size (32KB)
 * - Proactively warns/rejects external resources (images, scripts, styles) that fail on an offline captive portal unless explicitly allowed.
 */
class UploadPortalUseCase @Inject constructor(
    private val repository: DeviceRepository
) {
    suspend operator fun invoke(
        htmlContent: String,
        allowExternalResources: Boolean = false
    ): Flow<UploadProgress> {
        // Validate HTML content
        if (htmlContent.isBlank()) {
            return flowOf(UploadProgress.Error("HTML content cannot be empty"))
        }

        val contentBytes = htmlContent.toByteArray(StandardCharsets.UTF_8)
        val maxSize = 32 * 1024 // 32KB

        if (contentBytes.size > maxSize) {
            return flowOf(UploadProgress.Error("HTML content too large, max ${maxSize / 1024}KB supported"))
        }

        if (!allowExternalResources) {
            val externalResource = findExternalResource(htmlContent)
            if (externalResource != null) {
                return flowOf(
                    UploadProgress.Error(
                        "HTML contains external resource '$externalResource'. PromoBeacon operates offline; embed images as Base64/SVG and inline all CSS/JS."
                    )
                )
            }
        }

        return repository.uploadPortalContent(htmlContent)
    }

    companion object {
        private val EXTERNAL_RESOURCE_REGEX = Regex(
            """(?i)(?:\bsrc\s*=\s*["']?(https?://[^\s"'>]+)["']?|<link\b[^>]*\bhref\s*=\s*["']?(https?://[^\s"'>]+)["']?|@import\s+(?:url\()?["']?(https?://[^\s"')]+)["']?\))"""
        )

        /**
         * Scans HTML content for external URLs (images, scripts, external CSS) that would fail offline.
         * Returns the first offending URL found, or null if compliant.
         */
        fun findExternalResource(html: String): String? {
            val match = EXTERNAL_RESOURCE_REGEX.find(html) ?: return null
            return match.groupValues.drop(1).firstOrNull { it.isNotEmpty() } ?: match.value
        }
    }
}


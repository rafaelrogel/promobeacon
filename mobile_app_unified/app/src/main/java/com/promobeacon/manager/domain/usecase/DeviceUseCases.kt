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
        // Validate configuration
        if (config.ssid.length > 32) {
            return Result.failure(IllegalArgumentException("SSID cannot exceed 32 characters"))
        }
        if (config.ssid.isBlank()) {
            return Result.failure(IllegalArgumentException("SSID cannot be empty"))
        }
        if (config.promoText.length > 32) {
            return Result.failure(IllegalArgumentException("Promotion text cannot exceed 32 characters"))
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
 */
class UploadPortalUseCase @Inject constructor(
    private val repository: DeviceRepository
) {
    suspend operator fun invoke(htmlContent: String): Flow<UploadProgress> {
        // Validate HTML content
        if (htmlContent.isBlank()) {
            return flowOf(UploadProgress.Error("HTML content cannot be empty"))
        }

        val contentBytes = htmlContent.toByteArray(StandardCharsets.UTF_8)
        val maxSize = 32 * 1024 // 32KB

        if (contentBytes.size > maxSize) {
            return flowOf(UploadProgress.Error("HTML content too large, max ${maxSize / 1024}KB supported"))
        }

        return repository.uploadPortalContent(htmlContent)
    }
}

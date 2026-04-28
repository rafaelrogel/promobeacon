package com.promobeacon.manager.ui.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.promobeacon.manager.data.ble.AuthenticationState
import com.promobeacon.manager.data.ble.BleClient
import com.promobeacon.manager.domain.model.ConnectionState
import com.promobeacon.manager.domain.model.DeviceStatus
import com.promobeacon.manager.domain.model.GModeConfig
import com.promobeacon.manager.domain.repository.UploadProgress
import com.promobeacon.manager.domain.usecase.*
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * Dashboard Page UI State
 */
data class DashboardUiState(
    val connectionState: ConnectionState = ConnectionState.DISCONNECTED,
    val deviceStatus: DeviceStatus = DeviceStatus(),
    val gModeConfig: GModeConfig = GModeConfig(),
    val authenticationState: AuthenticationState = AuthenticationState.NOT_AUTHENTICATED,
    val isLoading: Boolean = false,
    val isSaving: Boolean = false,
    val isUploading: Boolean = false,
    val uploadProgress: Int = 0,
    val uploadTotalBytes: Int = 0,
    val error: String? = null,
    val successMessage: String? = null
)

/**
 * Dashboard Page ViewModel
 */
@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val bleClient: BleClient,
    private val getConnectionStateUseCase: GetConnectionStateUseCase,
    private val getDeviceStatusUseCase: GetDeviceStatusUseCase,
    private val readGModeConfigUseCase: ReadGModeConfigUseCase,
    private val updateGModeConfigUseCase: UpdateGModeConfigUseCase,
    private val rebootDeviceUseCase: RebootDeviceUseCase,
    private val resetToDefaultsUseCase: ResetToDefaultsUseCase,
    private val exportStatsToCsvUseCase: ExportStatsToCsvUseCase,
    private val uploadPortalUseCase: UploadPortalUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow(DashboardUiState())
    val uiState: StateFlow<DashboardUiState> = _uiState.asStateFlow()

    init {
        // Monitor connection state
        viewModelScope.launch {
            getConnectionStateUseCase().collect { state ->
                _uiState.update { it.copy(connectionState = state) }
            }
        }

        // Monitor device status
        viewModelScope.launch {
            getDeviceStatusUseCase().collect { status ->
                _uiState.update { it.copy(deviceStatus = status) }

                // Load G mode configuration when connected
                if (status.isConnected && _uiState.value.gModeConfig.ssid.isEmpty()) {
                    loadGModeConfig()
                }
            }
        }

        // Monitor authentication state
        viewModelScope.launch {
            bleClient.authenticationState.collect { state ->
                _uiState.update { it.copy(
                    authenticationState = state,
                    isLoading = if (state == AuthenticationState.AUTHENTICATED || 
                                   state == AuthenticationState.FAILED ||
                                   state == AuthenticationState.LOCKED) false else it.isLoading
                ) }
            }
        }
    }

    /**
     * Check if authentication is required
     */
    fun isAuthenticationRequired(): Boolean {
        return _uiState.value.authenticationState == AuthenticationState.REQUIRED ||
               _uiState.value.authenticationState == AuthenticationState.NOT_AUTHENTICATED
    }

    /**
     * Get the current authentication state
     */
    fun getAuthenticationState(): AuthenticationState {
        return _uiState.value.authenticationState
    }

    /**
     * Manually trigger authentication flow
     */
    fun triggerAuthentication() {
        _uiState.update { it.copy(authenticationState = AuthenticationState.REQUIRED) }
    }

    /**
     * Update G mode configuration
     */
    fun updateGModeConfig(config: GModeConfig) {
        viewModelScope.launch {
            _uiState.update { it.copy(isSaving = true, error = null) }

            // 1. Update standard config (SSID, WiFi Pass, Promo Text)
            val result = updateGModeConfigUseCase(config)

            if (result.isSuccess) {
                // 2. Update Admin Password if provided
                if (config.newAdminPassword.isNotEmpty()) {
                    val passwordResult = bleClient.writeAdminPassword(config.newAdminPassword)
                    if (!passwordResult) {
                        _uiState.update {
                            it.copy(
                                isSaving = false,
                                error = "Failed to update Admin Password. Session may have expired."
                            )
                        }
                        return@launch
                    }
                }

                _uiState.update {
                    it.copy(
                        isSaving = false,
                        gModeConfig = config.copy(newAdminPassword = ""), // Clear for next time
                        successMessage = if (config.newAdminPassword.isNotEmpty()) 
                            "Configuration and Admin Password updated" 
                            else "Configuration saved"
                    )
                }
            } else {
                _uiState.update {
                    it.copy(
                        isSaving = false,
                        error = result.exceptionOrNull()?.message ?: "Save failed"
                    )
                }
            }
        }
    }

    /**
     * Load G mode configuration
     */
    private fun loadGModeConfig() {
        viewModelScope.launch {
            val result = readGModeConfigUseCase()
            if (result.isSuccess) {
                _uiState.update { it.copy(gModeConfig = result.getOrDefault(GModeConfig())) }
            }
        }
    }

    /**
     * Reboot device
     */
    fun reboot() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }

            val result = rebootDeviceUseCase()

            if (result.isSuccess) {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        successMessage = "Device rebooting..."
                    )
                }
            } else {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        error = result.exceptionOrNull()?.message ?: "Reboot failed"
                    )
                }
            }
        }
    }

    /**
     * Factory reset
     */
    fun resetToDefaults() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }

            val result = resetToDefaultsUseCase()

            if (result.isSuccess) {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        successMessage = "Factory settings restored"
                    )
                }
                // Reload configuration
                loadGModeConfig()
            } else {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        error = result.exceptionOrNull()?.message ?: "Reset failed"
                    )
                }
            }
        }
    }

    /**
     * Clear error
     */
    fun clearError() {
        _uiState.update { it.copy(error = null) }
    }

    /**
     * Clear success message
     */
    fun clearSuccessMessage() {
        _uiState.update { it.copy(successMessage = null) }
    }

    /**
     * Export client statistics to CSV
     *
     * @param deviceIp Device IP address
     */
    fun exportStatsCsv(deviceIp: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }

            val result = exportStatsToCsvUseCase(deviceIp)

            if (result.isSuccess) {
                val filePath = result.getOrNull() ?: ""
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        successMessage = "Statistics exported to: $filePath"
                    )
                }
            } else {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        error = result.exceptionOrNull()?.message ?: "Export failed, please verify connection to device WiFi network"
                    )
                }
            }
        }
    }

    /**
     * Upload custom portal page content
     *
     * @param htmlContent HTML content
     */
    fun uploadPortalContent(htmlContent: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isUploading = true, uploadProgress = 0, error = null) }

            uploadPortalUseCase(htmlContent).collect { progress ->
                when (progress) {
                    is UploadProgress.Started -> {
                        _uiState.update {
                            it.copy(uploadTotalBytes = progress.totalBytes, uploadProgress = 0)
                        }
                    }
                    is UploadProgress.InProgress -> {
                        _uiState.update {
                            it.copy(uploadProgress = progress.percentage)
                        }
                    }
                    is UploadProgress.Completed -> {
                        _uiState.update {
                            it.copy(
                                isUploading = false,
                                uploadProgress = 100,
                                successMessage = "Portal page uploaded successfully (${progress.totalBytes} bytes)"
                            )
                        }
                    }
                    is UploadProgress.Error -> {
                        _uiState.update {
                            it.copy(
                                isUploading = false,
                                uploadProgress = 0,
                                error = progress.message
                            )
                        }
                    }
                }
            }
        }
    }

    /**
     * Reset upload state
     */
    fun resetUploadState() {
        _uiState.update { it.copy(isUploading = false, uploadProgress = 0, uploadTotalBytes = 0) }
    }

    /**
     * Disconnect current device
     */
    fun disconnect() {
        bleClient.disconnect()
        _uiState.update { it.copy(
            connectionState = ConnectionState.DISCONNECTED,
            isLoading = false,
            isSaving = false,
            isUploading = false
        ) }
    }

    /**
     * Authenticate with token
     */
    fun authenticate(token: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            val result = bleClient.authenticate(token)
            
            if (!result) {
                _uiState.update { 
                    it.copy(
                        isLoading = false, 
                        error = "Failed to send authentication command"
                    ) 
                }
                return@launch
            }

            // Safety timeout: if state doesn't change from AUTHENTICATING/NOT_AUTHENTICATED 
            // within 5 seconds, stop loading
            delay(5000)
            if (_uiState.value.isLoading) {
                _uiState.update { it.copy(isLoading = false) }
            }
        }
    }
}

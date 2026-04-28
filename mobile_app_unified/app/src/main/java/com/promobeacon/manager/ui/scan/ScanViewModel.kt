package com.promobeacon.manager.ui.scan

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.promobeacon.manager.domain.model.ConnectionState
import com.promobeacon.manager.domain.repository.ScannedDevice
import com.promobeacon.manager.domain.usecase.*
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * Scan Page UI State
 */
data class ScanUiState(
    val isScanning: Boolean = false,
    val devices: List<ScannedDevice> = emptyList(),
    val connectingDevice: ScannedDevice? = null,
    val connectionState: ConnectionState = ConnectionState.DISCONNECTED,
    val error: String? = null
)

/**
 * Scan Page ViewModel
 */
@HiltViewModel
class ScanViewModel @Inject constructor(
    private val scanDevicesUseCase: ScanDevicesUseCase,
    private val connectDeviceUseCase: ConnectDeviceUseCase,
    private val getConnectionStateUseCase: GetConnectionStateUseCase,
    private val getDeviceStatusUseCase: GetDeviceStatusUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow(ScanUiState())
    val uiState: StateFlow<ScanUiState> = _uiState.asStateFlow()

    // Navigation state
    private val _navigationEvent = MutableSharedFlow<NavigationEvent>()
    val navigationEvent: SharedFlow<NavigationEvent> = _navigationEvent.asSharedFlow()

    init {
        // Monitor connection state
        viewModelScope.launch {
            getConnectionStateUseCase().collect { state ->
                _uiState.update { it.copy(connectionState = state) }

                // Navigate to dashboard on successful connection
                if (state == ConnectionState.CONNECTED) {
                    _navigationEvent.emit(NavigationEvent.NavigateToDashboard)
                }
            }
        }
    }

    /**
     * Start scanning
     */
    fun startScan() {
        viewModelScope.launch {
            _uiState.update { it.copy(isScanning = true, error = null) }

            scanDevicesUseCase(timeoutMs = 15000).collect { devices ->
                _uiState.update { it.copy(devices = devices) }
            }

            _uiState.update { it.copy(isScanning = false) }
        }
    }

    /**
     * Stop scanning
     */
    fun stopScan() {
        scanDevicesUseCase.stop()
        _uiState.update { it.copy(isScanning = false) }
    }

    /**
     * Connect to device
     */
    fun connectDevice(device: ScannedDevice) {
        viewModelScope.launch {
            _uiState.update { it.copy(connectionState = ConnectionState.CONNECTING, connectingDevice = device) }

            val result = connectDeviceUseCase(device)

            if (result.isFailure) {
                _uiState.update {
                    it.copy(
                        connectionState = ConnectionState.DISCONNECTED,
                        connectingDevice = null,
                        error = result.exceptionOrNull()?.message ?: "Connection failed"
                    )
                }
            }
            // On success, navigation will happen via connection state Flow
        }
    }

    /**
     * Clear error
     */
    fun clearError() {
        _uiState.update { it.copy(error = null) }
    }

    override fun onCleared() {
        super.onCleared()
        scanDevicesUseCase.stop()
    }
}

/**
 * Navigation Events
 */
sealed class NavigationEvent {
    object NavigateToDashboard : NavigationEvent()
}

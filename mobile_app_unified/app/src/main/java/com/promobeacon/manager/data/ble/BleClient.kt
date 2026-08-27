package com.promobeacon.manager.data.ble

import android.Manifest
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattDescriptor
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.bluetooth.le.BluetoothLeScanner
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanSettings
import android.os.ParcelUuid
import android.content.Context
import android.content.pm.PackageManager
import android.util.Log
import androidx.core.content.ContextCompat
import com.promobeacon.manager.domain.model.DeviceMode
import com.promobeacon.manager.domain.repository.ScannedDevice
import com.promobeacon.manager.domain.repository.SignalLevel
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import javax.inject.Inject
import javax.inject.Singleton
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.CompletableDeferred

/**
 * BLE GATT service UUID constants
 */
object BleConstants {
    // Unified service UUID
    const val PROMO_SERVICE_UUID = "12345678-1234-1234-1234-123456789ABC"

    // Characteristic UUIDs
    const val CHAR_MODE_CONTROL = "12345679-1234-1234-1234-123456789ABC"
    const val CHAR_MESSAGE = "1234567A-1234-1234-1234-123456789ABC"
    const val CHAR_CONFIG = "1234567B-1234-1234-1234-123456789ABC"
    const val CHAR_STATUS = "1234567C-1234-1234-1234-123456789ABC"
    const val CHAR_PROMO_TEXT = "1234567D-1234-1234-1234-123456789ABC"
    const val CHAR_PORTAL_DATA = "12345681-1234-1234-1234-123456789ABC"  // Portal data chunks
    const val CHAR_PORTAL_CTRL = "12345682-1234-1234-1234-123456789ABC"  // Portal control & status
    const val CHAR_AUTH = "12345683-1234-1234-1234-123456789ABC"  // Authentication
    const val CHAR_DEVICE_NAME = "12345684-1234-1234-1234-123456789ABC" // Custom Device Name
    const val CHAR_AUTH_STATUS = "12345685-1234-1234-1234-123456789ABC"  // Auth status
    const val CHAR_ADMIN_PASSWORD = "12345686-1234-1234-1234-123456789ABC"  // Admin password change
    const val CHAR_STATS = "1234567E-1234-1234-1234-123456789ABC"         // Aggregated stats
    const val CHAR_SESSIONS = "1234567F-1234-1234-1234-123456789ABC"      // Session history
    const val CHAR_SESSION_CTRL = "12345680-1234-1234-1234-123456789ABC"  // Session control commands

    // Command constants
    const val CMD_MODE_G = 0x00
    const val CMD_MODE_E = 0x01
    const val CMD_REBOOT = 0x02
    const val CMD_RESET_DEFAULTS = 0x03

    // Portal content upload commands
    const val PORTAL_CMD_START = 0x10
    const val PORTAL_CMD_DATA = 0x11
    const val PORTAL_CMD_END = 0x12
    const val PORTAL_CMD_ABORT = 0x13
    const val PORTAL_CMD_STATUS = 0x14
    const val PORTAL_CMD_RESET = 0x15

    // Authentication commands
    const val AUTH_CMD_LOGIN = 0x01    // Submit authentication token
    const val AUTH_CMD_LOGOUT = 0x02    // Clear authentication
    const val AUTH_CMD_SET_TOKEN = 0x03    // Set new auth token (requires auth)
    const val AUTH_CMD_GET_TOKEN_HINT = 0x04    // Get token hint (first 4 chars)

    // Authentication status values
    const val AUTH_STATUS_IDLE = 0x00
    const val AUTH_STATUS_REQUIRED = 0x01
    const val AUTH_STATUS_SUCCESS = 0x02
    const val AUTH_STATUS_FAILED = 0x03
    const val AUTH_STATUS_LOCKED = 0x04

    // Transfer parameters
    const val PORTAL_CHUNK_SIZE = 128  // Reduced for better compatibility with standard MTU
    const val PORTAL_MAX_SIZE = 32768  // 32KB max HTML size
}

/**
 * BLE client class
 * Encapsulates Bluetooth GATT operations
 */
@Singleton
class BleClient @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private val tag = "BleClient"
    private val PROMOBEACON_SERVICE_UUID = "12345678-1234-1234-1234-123456789ABC"
    private var scanFallbackJob: Job? = null
    private var isScanFallbackActive = false

    private var bluetoothManager: BluetoothManager? = null
    private var bluetoothAdapter: android.bluetooth.BluetoothAdapter? = null
    private var bluetoothScanner: BluetoothLeScanner? = null
    private var bluetoothGatt: BluetoothGatt? = null
    private var connectionJob: Job? = null

    private val scope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    // Status flows
    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private val _deviceStatus = MutableStateFlow<ByteArray?>(null)
    val deviceStatus: StateFlow<ByteArray?> = _deviceStatus.asStateFlow()

    private val writeMutex = Mutex()
    private val descriptorMutex = Mutex()


    internal var adminPasswordChar: BluetoothGattCharacteristic? = null
    internal var deviceNameChar: BluetoothGattCharacteristic? = null

    private val _scanResults = MutableStateFlow<List<ScannedDevice>>(emptyList())
    val scanResults: StateFlow<List<ScannedDevice>> = _scanResults.asStateFlow()

    private val _scanError = MutableStateFlow<Int?>(null)
    val scanError: StateFlow<Int?> = _scanError.asStateFlow()

    private var isScanning = false

    // Characteristic references
    private var modeControlChar: BluetoothGattCharacteristic? = null
    private var messageChar: BluetoothGattCharacteristic? = null
    private var configChar: BluetoothGattCharacteristic? = null
    private var statusChar: BluetoothGattCharacteristic? = null
    internal var promoTextChar: BluetoothGattCharacteristic? = null
    private var portalDataChar: BluetoothGattCharacteristic? = null  // Portal data chunks
    private var portalCtrlChar: BluetoothGattCharacteristic? = null   // Portal control & status
    private var authChar: BluetoothGattCharacteristic? = null        // Authentication
    private var authStatusChar: BluetoothGattCharacteristic? = null  // Auth status
    private var statsChar: BluetoothGattCharacteristic? = null
    private var sessionsChar: BluetoothGattCharacteristic? = null
    private var sessionCtrlChar: BluetoothGattCharacteristic? = null

    private val pendingReads = mutableMapOf<String, CompletableDeferred<String?>>()
    private var pendingWrite: CompletableDeferred<Boolean>? = null
    private var pendingDescriptorWrite: CompletableDeferred<Boolean>? = null

    // Authentication state
    private val _authenticationState = MutableStateFlow(AuthenticationState.NOT_AUTHENTICATED)
    val authenticationState: StateFlow<AuthenticationState> = _authenticationState.asStateFlow()

    // Portal upload state
    private var portalUploadInProgress = false
    private var portalUploadProgress = MutableStateFlow(0f)

    // GATT callback
    private val gattCallback = object : BluetoothGattCallback() {
        override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
            Log.d(tag, "onConnectionStateChange: status=$status, newState=$newState")

            if (gatt != bluetoothGatt && newState == BluetoothProfile.STATE_DISCONNECTED) {
                Log.d(tag, "Ignoring stale disconnect from old GATT")
                return
            }

            if (status == BluetoothGatt.GATT_SUCCESS) {
                if (newState == BluetoothProfile.STATE_CONNECTED) {
                    Log.d(tag, "Connected to GATT server, requesting MTU...")
                    bluetoothGatt?.requestMtu(512)
                } else if (newState == BluetoothProfile.STATE_DISCONNECTED) {
                    _authenticationState.value = AuthenticationState.NOT_AUTHENTICATED
                    _connectionState.value = ConnectionState.DISCONNECTED
                    Log.d(tag, "Disconnected from GATT server")
                    close()
                }
            } else {
                Log.e(tag, "Connection error: $status")
                _authenticationState.value = AuthenticationState.NOT_AUTHENTICATED
                _connectionState.value = ConnectionState.DISCONNECTED
                close()
            }
        }

        override fun onMtuChanged(gatt: BluetoothGatt, mtu: Int, status: Int) {
            Log.d(tag, "onMtuChanged: mtu=$mtu, status=$status")
            discoverServices()
        }

        override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
            Log.d(tag, "onServicesDiscovered: status=$status")

            if (status == BluetoothGatt.GATT_SUCCESS) {
                Log.d(tag, "Services discovered")
                scope.launch(Dispatchers.IO) {
                    findCharacteristics(gatt)
                    _connectionState.value = ConnectionState.CONNECTED
                    delay(300)
                    readAuthStatus()
                }
            } else {
                Log.w(tag, "onServicesDiscovered failed: $status")
                _authenticationState.value = AuthenticationState.NOT_AUTHENTICATED
                _connectionState.value = ConnectionState.DISCONNECTED
                close()
            }
        }

        override fun onCharacteristicRead(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic, status: Int) {
            Log.d(tag, "onCharacteristicRead: ${characteristic.uuid}, status=$status")

            val uuid = characteristic.uuid.toString()
            val deferred = pendingReads.remove(uuid)
            if (deferred != null) {
                if (status == BluetoothGatt.GATT_SUCCESS) {
                    val value = characteristic.getStringValue(0)
                    deferred.complete(value)
                } else {
                    deferred.complete(null)
                }
                return
            }

            if (status == BluetoothGatt.GATT_SUCCESS) {
                // Note: characteristic.uuid.toString() is always lowercase; constants are uppercase
                when (characteristic.uuid.toString().lowercase()) {
                    BleConstants.CHAR_STATUS.lowercase() -> {
                        _deviceStatus.value = characteristic.value
                    }
                    BleConstants.CHAR_AUTH_STATUS.lowercase() -> {
                        // Crucial: Update auth state even from manual read fallback
                        if (characteristic.value.isNotEmpty()) {
                            updateAuthenticationState(characteristic.value[0])
                        }
                    }
                }
            }
        }

        override fun onCharacteristicChanged(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic) {
            Log.d(tag, "onCharacteristicChanged: ${characteristic.uuid}")

            val uuid = characteristic.uuid.toString().lowercase()
            if (uuid == BleConstants.CHAR_STATUS.lowercase()) {
                _deviceStatus.value = characteristic.value
            } else if (uuid == BleConstants.CHAR_AUTH_STATUS.lowercase()) {
                // Update authentication state from notification
                if (characteristic.value.isNotEmpty()) {
                    updateAuthenticationState(characteristic.value[0])
                }
            } else if (uuid == BleConstants.CHAR_PORTAL_CTRL.lowercase()) {
                // Handle portal status notifications
                if (characteristic.value.isNotEmpty()) {
                    val status = characteristic.value[0]
                    val progress = if (characteristic.value.size > 1) characteristic.value[1] else 0
                    portalUploadProgress.value = progress / 100f
                }
            }
        }

        override fun onCharacteristicWrite(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic, status: Int) {
            Log.d(tag, "onCharacteristicWrite: ${characteristic.uuid}, status=$status")
            if (status == 5 /* GATT_INSUFFICIENT_AUTHENTICATION */) {
                _authenticationState.value = AuthStateReducer.reduce(_authenticationState.value, AuthEvent.WRITE_REJECTED_BY_AUTH)
            }
            pendingWrite?.complete(status == BluetoothGatt.GATT_SUCCESS)
            pendingWrite = null
        }

        override fun onDescriptorWrite(gatt: BluetoothGatt, descriptor: BluetoothGattDescriptor, status: Int) {
            Log.d(tag, "onDescriptorWrite: ${descriptor.uuid}, status=$status")
            pendingDescriptorWrite?.complete(status == BluetoothGatt.GATT_SUCCESS)
            pendingDescriptorWrite = null
        }
    }

    /**
     * Initialize BLE client
     */
    fun initialize(): Boolean {
        bluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
        bluetoothAdapter = bluetoothManager?.adapter

        if (bluetoothAdapter == null) {
            Log.e(tag, "Bluetooth adapter not available")
            return false
        }

        if (!bluetoothAdapter!!.isEnabled) {
            Log.e(tag, "Bluetooth is not enabled")
            return false
        }

        bluetoothScanner = bluetoothAdapter?.bluetoothLeScanner
        return true
    }

    /**
     * Check BLE permissions
     */
    fun hasRequiredPermissions(): Boolean {
        return ContextCompat.checkSelfPermission(context, Manifest.permission.BLUETOOTH_SCAN) == PackageManager.PERMISSION_GRANTED &&
               ContextCompat.checkSelfPermission(context, Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED
    }

    /**
     * Start scanning for devices
     */
    fun startScan() {
        if (!hasRequiredPermissions()) {
            Log.w(tag, "Missing required BLE permissions (SCAN and CONNECT)")
            return
        }

        if (isScanning) {
            Log.d(tag, "Already scanning")
            return
        }

        _scanError.value = null
        _scanResults.value = emptyList()
        isScanning = true
        isScanFallbackActive = false
        
        // Cancel any previous fallback timer
        scanFallbackJob?.cancel()

        val scanFilter = ScanFilter.Builder()
            .setServiceUuid(ParcelUuid.fromString(PROMOBEACON_SERVICE_UUID))
            .build()

        val scanSettings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            .setReportDelay(0)
            .build()

        try {
            Log.d(tag, "Starting scan (unfiltered for maximum compatibility)")
            // Start unfiltered immediately - the scanCallback filters by UUID/name
            bluetoothScanner?.startScan(null, scanSettings, scanCallback)

            // Start fallback timer: if nothing found after 8s, show ALL BLE devices
            scanFallbackJob = scope.launch {
                delay(8000)
                if (_scanResults.value.isEmpty() && isScanning && !isScanFallbackActive) {
                    Log.w(tag, "No PromoBeacon found, switching to show-all mode for debugging")
                    isScanFallbackActive = true
                    // Continue scanning - callback will now show all devices
                }
            }
        } catch (e: SecurityException) {
            Log.e(tag, "Security exception during scan", e)
            isScanning = false
        }
    }

    /**
     * Stop scanning for devices
     */
    fun stopScan() {
        if (!isScanning) return

        try {
            scanFallbackJob?.cancel()
            scanFallbackJob = null
            bluetoothScanner?.stopScan(scanCallback)
            isScanning = false
            isScanFallbackActive = false
            Log.d(tag, "Scan stopped")
        } catch (e: SecurityException) {
            Log.e(tag, "Security exception during stop scan", e)
        }
    }

    /**
     * Connect to device
     */
    fun connect(device: ScannedDevice): Flow<ConnectionState> = flow {
        emit(ConnectionState.CONNECTING)

        try {
            // Stop scanning
            stopScan()

            // Disconnect existing connection safely
            val oldGatt = bluetoothGatt
            bluetoothGatt = null
            oldGatt?.disconnect()
            oldGatt?.close()
            delay(200)

            val bluetoothDevice = bluetoothAdapter?.getRemoteDevice(device.address)
            if (bluetoothDevice == null) {
                emit(ConnectionState.DISCONNECTED)
                return@flow
            }

            // Connect
            _authenticationState.value = AuthenticationState.NOT_AUTHENTICATED
            _connectionState.value = ConnectionState.CONNECTING

            bluetoothGatt = bluetoothDevice.connectGatt(
                context,
                false,
                gattCallback,
                BluetoothDevice.TRANSPORT_LE
            )

            // Wait for connection state change
            val finalState = kotlinx.coroutines.withTimeoutOrNull(30_000L) {
                _connectionState.first { it != ConnectionState.CONNECTING }
            } ?: ConnectionState.DISCONNECTED
            _connectionState.emit(finalState)

            emit(_connectionState.value)
        } catch (e: SecurityException) {
            Log.e(tag, "Security exception during connect", e)
            emit(ConnectionState.DISCONNECTED)
        }
    }.flowOn(Dispatchers.IO)

    /**
     * Disconnect
     */
    fun disconnect() {
        try {
            bluetoothGatt?.disconnect()
            close()
        } catch (e: SecurityException) {
            Log.e(tag, "Security exception during disconnect", e)
        }
    }

    /**
     * Close GATT connection
     */
    private fun close() {
        try {
            bluetoothGatt?.close()
            modeControlChar = null
            messageChar = null
            configChar = null
            statusChar = null
            promoTextChar = null
            portalDataChar = null
            portalCtrlChar = null
            authChar = null
            authStatusChar = null
            adminPasswordChar = null
            deviceNameChar = null
            statsChar = null
            sessionsChar = null
            sessionCtrlChar = null
            bluetoothGatt = null
        } catch (e: SecurityException) {
            Log.e(tag, "Security exception during close", e)
        } finally {
            _authenticationState.value = AuthenticationState.NOT_AUTHENTICATED
            _deviceStatus.value = null
            portalUploadProgress.value = 0f
            portalUploadInProgress = false
            pendingReads.clear()
            pendingWrite = null
            pendingDescriptorWrite = null
        }
    }

    /**
     * Discover services
     */
    private fun discoverServices() {
        try {
            bluetoothGatt?.discoverServices()
        } catch (e: SecurityException) {
            Log.e(tag, "Security exception during discoverServices", e)
        }
    }

    /**
     * Find characteristics
     */
    private suspend fun findCharacteristics(gatt: BluetoothGatt) {
        val service = gatt.getService(java.util.UUID.fromString(BleConstants.PROMO_SERVICE_UUID))
        if (service == null) {
            Log.w(tag, "Service not found")
            return
        }

        modeControlChar = service.getCharacteristic(java.util.UUID.fromString(BleConstants.CHAR_MODE_CONTROL))
        messageChar = service.getCharacteristic(java.util.UUID.fromString(BleConstants.CHAR_MESSAGE))
        configChar = service.getCharacteristic(java.util.UUID.fromString(BleConstants.CHAR_CONFIG))
        statusChar = service.getCharacteristic(java.util.UUID.fromString(BleConstants.CHAR_STATUS))
        promoTextChar = service.getCharacteristic(java.util.UUID.fromString(BleConstants.CHAR_PROMO_TEXT))
        adminPasswordChar = service.getCharacteristic(java.util.UUID.fromString(BleConstants.CHAR_ADMIN_PASSWORD))
        
        // Portal content upload characteristics
        portalDataChar = service.getCharacteristic(java.util.UUID.fromString(BleConstants.CHAR_PORTAL_DATA))
        portalCtrlChar = service.getCharacteristic(java.util.UUID.fromString(BleConstants.CHAR_PORTAL_CTRL))
        
        // Stats and session history characteristics
        statsChar = service.getCharacteristic(java.util.UUID.fromString(BleConstants.CHAR_STATS))
        sessionsChar = service.getCharacteristic(java.util.UUID.fromString(BleConstants.CHAR_SESSIONS))
        sessionCtrlChar = service.getCharacteristic(java.util.UUID.fromString(BleConstants.CHAR_SESSION_CTRL))

        // Find custom PromoBeacon Device Name
        deviceNameChar = service.getCharacteristic(java.util.UUID.fromString(BleConstants.CHAR_DEVICE_NAME))

        // Authentication characteristics
        findAuthCharacteristics(gatt)

        // Enable status notifications (serialized - one at a time)
        enableNotifications(statusChar)
        delay(50)
        enableNotifications(portalCtrlChar)
    }

    /**
     * Enable notifications
     */
    private suspend fun enableNotifications(characteristic: BluetoothGattCharacteristic?): Boolean {
        if (characteristic == null) return false

        return descriptorMutex.withLock {
            try {
                bluetoothGatt?.setCharacteristicNotification(characteristic, true)

                val descriptor = characteristic.getDescriptor(
                    java.util.UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")
                )
                if (descriptor != null) {
                    val deferred = CompletableDeferred<Boolean>()
                    pendingDescriptorWrite = deferred
                    descriptor.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
                    val initiated = bluetoothGatt?.writeDescriptor(descriptor) ?: false
                    if (!initiated) {
                        pendingDescriptorWrite = null
                        return@withLock false
                    }
                    val result = withTimeoutOrNull(2000L) { deferred.await() } ?: false
                    if (pendingDescriptorWrite == deferred) {
                        pendingDescriptorWrite = null
                    }
                    result
                } else {
                    false
                }
            } catch (e: SecurityException) {
                Log.e(tag, "Security exception during enableNotifications", e)
                false
            }
        }
    }

    /**
     * Write mode control
     */
    suspend fun writeMode(mode: DeviceMode): Boolean {
        val value = when (mode) {
            DeviceMode.MODE_G -> BleConstants.CMD_MODE_G
            DeviceMode.MODE_E -> BleConstants.CMD_MODE_E
            else -> return false
        }

        return writeCharacteristic(modeControlChar, byteArrayOf(value.toByte()))
    }

    /**
     * Write message
     */
    suspend fun writeMessage(message: String): Boolean {
        if (!ensureAuthenticatedForWrite()) return false
        val bytes = message.toByteArray(Charsets.UTF_8)
        val success = writeCharacteristic(messageChar, bytes)
        if (!success && _authenticationState.value != AuthenticationState.AUTHENTICATED) {
            _authenticationState.value = AuthStateReducer.reduce(_authenticationState.value, AuthEvent.WRITE_REJECTED_BY_AUTH)
        }
        return success
    }

    /**
     * Write promotion text
     */
    suspend fun writePromoText(text: String): Boolean {
        if (!ensureAuthenticatedForWrite()) return false
        val bytes = text.toByteArray(Charsets.UTF_8)
        val success = writeCharacteristic(promoTextChar, bytes)
        if (!success && _authenticationState.value != AuthenticationState.AUTHENTICATED) {
            _authenticationState.value = AuthStateReducer.reduce(_authenticationState.value, AuthEvent.WRITE_REJECTED_BY_AUTH)
        }
        return success
    }

    suspend fun readPromoText(): String? {
        return try {
            val char = promoTextChar ?: return null
            val gatt = bluetoothGatt ?: return null
            withTimeoutOrNull(3000L) {
                val deferred = CompletableDeferred<String?>()
                pendingReads[char.uuid.toString()] = deferred
                gatt.readCharacteristic(char)
                deferred.await()
            }
        } catch (e: Exception) {
            null
        }
    }

    suspend fun readDeviceName(): String? {
        return try {
            val char = deviceNameChar ?: return null
            val gatt = bluetoothGatt ?: return null
            withTimeoutOrNull(3000L) {
                val deferred = CompletableDeferred<String?>()
                pendingReads[char.uuid.toString()] = deferred
                gatt.readCharacteristic(char)
                deferred.await()
            }
        } catch (e: Exception) {
            null
        }
    }

    suspend fun writeDeviceName(name: String): Boolean {
        if (!ensureAuthenticatedForWrite()) return false
        val data = name.toByteArray(Charsets.UTF_8)
        val success = writeCharacteristic(deviceNameChar, data)
        if (!success && _authenticationState.value != AuthenticationState.AUTHENTICATED) {
            _authenticationState.value = AuthStateReducer.reduce(_authenticationState.value, AuthEvent.WRITE_REJECTED_BY_AUTH)
        }
        return success
    }

    /**
     * Write configuration command.
     *
     * Firmware protocol (v4.1.5+): the config characteristic treats a write of
     * exactly ONE byte as a command (CMD_REBOOT=0x02, CMD_RESET_DEFAULTS=0x03,
     * CONFIG_START_OTA=0x03). Any write longer than 1 byte is interpreted as a
     * raw WiFi password update. The app's old 6-byte frame (command + 3 params)
     * therefore never reached the command branch — reboot/factory-reset were
     * silently treated as a WiFi password write ("WiFi Password update received:
     * \x02"). Send only the single command byte.
     */
    suspend fun writeConfig(command: Byte, param1: Short = 0, param2: Short = 0, param3: Byte = 0): Boolean {
        if (!ensureAuthenticatedForWrite()) return false
        // Only single-byte commands are supported by the current firmware protocol.
        // (params are kept for API compatibility but not serialized.)
        val data = byteArrayOf(command)
        val success = writeCharacteristic(configChar, data)
        if (!success && _authenticationState.value != AuthenticationState.AUTHENTICATED) {
            _authenticationState.value = AuthStateReducer.reduce(_authenticationState.value, AuthEvent.WRITE_REJECTED_BY_AUTH)
        }
        return success
    }

    suspend fun writeSsid(ssid: String): Boolean {
        // No-op: SSID is driven by promo text on the firmware side.
        // Returning true to maintain API compatibility.
        return true
    }

    suspend fun writeWifiPassword(password: String): Boolean {
        if (!ensureAuthenticatedForWrite()) return false
        val data = password.toByteArray(Charsets.UTF_8)
        val success = writeCharacteristic(configChar, data)
        if (!success && _authenticationState.value != AuthenticationState.AUTHENTICATED) {
            _authenticationState.value = AuthStateReducer.reduce(_authenticationState.value, AuthEvent.WRITE_REJECTED_BY_AUTH)
        }
        return success
    }

    /**
     * Write characteristic value
     */
    suspend fun writeCharacteristic(characteristic: BluetoothGattCharacteristic?, data: ByteArray): Boolean {
        if (characteristic == null) { return false }
        if (data.isEmpty()) { return false }
        return writeMutex.withLock {
            try {
                val deferred = CompletableDeferred<Boolean>()
                pendingWrite = deferred
                characteristic.value = data
                characteristic.writeType = BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT
                val initiated = bluetoothGatt?.writeCharacteristic(characteristic) ?: false
                if (!initiated) {
                    pendingWrite = null
                    return@withLock false
                }
                withTimeoutOrNull(2000L) {
                    deferred.await()
                } ?: false
            } catch (e: SecurityException) { false }
        }
    }

    fun readCharacteristicAsString(characteristic: BluetoothGattCharacteristic?): String? {
        if (characteristic == null || bluetoothGatt == null) return null
        return try {
            // Note: This is a synchronous read in the sense that it triggers the request,
            // but the value won't be updated until onCharacteristicRead is called.
            // However, the provided prompt suggests this usage pattern.
            // For a more robust implementation, we might want a suspend version with a callback/continuation.
            bluetoothGatt?.readCharacteristic(characteristic)
            characteristic.getStringValue(0)
        } catch (e: SecurityException) { null }
    }

    /**
     * Read status
     */
    fun readStatus(): Boolean {
        return try {
            statusChar?.let {
                bluetoothGatt?.readCharacteristic(it)
                true
            } ?: false
        } catch (e: SecurityException) {
            Log.e(tag, "Security exception during readStatus", e)
            false
        }
    }

    /**
     * Scan callback
     */
    private val scanCallback = object : ScanCallback() {
        override fun onScanResult(callbackType: Int, result: ScanResult) {
            try {
                val device = result.device
                val name = device.name ?: "Unknown"
                val rssi = result.rssi

                // Filter logic:
                // - Normal mode: filter by UUID or PromoBeacon name
                // - Fallback/debug mode: show ALL devices so user can see if ESP32 is visible
                val isMatch = if (isScanFallbackActive) {
                    // Show everything in debug mode
                    true
                } else {
                    val scanRecord = result.scanRecord
                    val hasServiceUuid = scanRecord?.serviceUuids?.any {
                        it.toString().equals(PROMOBEACON_SERVICE_UUID, ignoreCase = true)
                    } == true
                    hasServiceUuid || name.contains("PROMO", ignoreCase = true) || 
                        name.contains("Beacon", ignoreCase = true) || name.contains("ESP", ignoreCase = true)
                }

                if (isMatch) {
                    val scannedDevice = ScannedDevice(
                        name = name,
                        address = device.address,
                        rssi = rssi,
                        isPromoBeacon = true
                    )

                    val currentList = _scanResults.value.toMutableList()
                    val existingIndex = currentList.indexOfFirst { it.address == device.address }

                    if (existingIndex >= 0) {
                        currentList[existingIndex] = scannedDevice
                    } else {
                        currentList.add(scannedDevice)
                    }

                    // Sort by signal strength
                    _scanResults.value = currentList.sortedByDescending { it.rssi }
                }
            } catch (e: SecurityException) {
                Log.e(tag, "Security exception in scan callback", e)
            }
        }

        override fun onScanFailed(errorCode: Int) {
            Log.e(tag, "Scan failed: $errorCode")
            _scanError.value = errorCode
            isScanning = false
        }
    }

    /**
     * ================================================================
     * PORTAL CONTENT UPLOAD METHODS
     * ================================================================
     */

    /**
     * Start portal content upload transfer
     *
     * @param totalSize Total size of HTML content in bytes
     * @param crc32 CRC32 checksum of content
     * @return true if start command was sent successfully
     */
    suspend fun portalStartUpload(totalSize: Int, crc32: Int): Boolean {
        if (portalCtrlChar == null) {
            Log.e(tag, "Portal ctrl characteristic not available")
            return false
        }

        // Command format: [CMD=0x10] [Total Size: 4 bytes] [CRC32: 4 bytes] (Little-Endian)
        val data = ByteArray(9)
        data[0] = BleConstants.PORTAL_CMD_START.toByte()
        data[1] = (totalSize and 0xFF).toByte()
        data[2] = ((totalSize shr 8) and 0xFF).toByte()
        data[3] = ((totalSize shr 16) and 0xFF).toByte()
        data[4] = ((totalSize shr 24) and 0xFF).toByte()
        data[5] = (crc32 and 0xFF).toByte()
        data[6] = ((crc32 shr 8) and 0xFF).toByte()
        data[7] = ((crc32 shr 16) and 0xFF).toByte()
        data[8] = ((crc32 shr 24) and 0xFF).toByte()

        portalUploadInProgress = true
        portalUploadProgress.value = 0f

        val result = writeCharacteristic(portalCtrlChar, data)
        if (result) {
            Log.i(tag, "Portal upload started: size=$totalSize, crc=0x${crc32.toString(16)}")
        }
        return result
    }

    /**
     * Send portal content data chunk
     *
     * @param sequenceNumber Sequence number (0-based)
     * @param data Chunk data (max CHUNK_SIZE bytes)
     * @return true if chunk was sent successfully
     */
    suspend fun portalSendChunk(sequenceNumber: Int, data: ByteArray): Boolean {
        if (portalDataChar == null) {
            Log.e(tag, "Portal data characteristic not available")
            return false
        }

        if (!portalUploadInProgress) {
            Log.w(tag, "No portal upload in progress")
            return false
        }

        // Data format: [Seq Num: 2 bytes] [Data: up to 128 bytes]
        val chunkData = ByteArray(2 + data.size)
        chunkData[0] = (sequenceNumber and 0xFF).toByte()
        chunkData[1] = ((sequenceNumber shr 8) and 0xFF).toByte()
        System.arraycopy(data, 0, chunkData, 2, data.size)

        // Use NO_RESPONSE for faster throughput on data chunks
        portalDataChar?.writeType = BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE
        val result = writeCharacteristic(portalDataChar, chunkData)
        if (result) {
            Log.d(tag, "Portal chunk $sequenceNumber sent: ${data.size} bytes")
        }
        return result
    }

    /**
     * Complete portal content upload
     *
     * @return true if end command was sent successfully
     */
    suspend fun portalCompleteUpload(): Boolean {
        if (portalCtrlChar == null) {
            return false
        }

        val data = byteArrayOf(BleConstants.PORTAL_CMD_END.toByte())
        val result = writeCharacteristic(portalCtrlChar, data)

        if (result) {
            Log.i(tag, "Portal upload completed")
        }
        portalUploadInProgress = false
        return result
    }

    /**
     * Abort portal content upload
     *
     * @return true if abort command was sent successfully
     */
    suspend fun portalAbortUpload(): Boolean {
        if (portalCtrlChar == null) {
            return false
        }

        val data = byteArrayOf(BleConstants.PORTAL_CMD_ABORT.toByte())
        val result = writeCharacteristic(portalCtrlChar, data)

        if (result) {
            Log.i(tag, "Portal upload aborted")
        }
        portalUploadInProgress = false
        portalUploadProgress.value = 0f
        return result
    }

    /**
     * Request portal status
     *
     * @return true if status command was sent successfully
     */
    suspend fun portalRequestStatus(): Boolean {
        if (portalCtrlChar == null) {
            return false
        }

        val data = byteArrayOf(BleConstants.PORTAL_CMD_STATUS.toByte())
        return writeCharacteristic(portalCtrlChar, data)
    }

    /**
     * Reset portal to default content
     *
     * @return true if reset command was sent successfully
     */
    suspend fun portalResetToDefault(): Boolean {
        if (portalCtrlChar == null) {
            return false
        }

        val data = byteArrayOf(BleConstants.PORTAL_CMD_RESET.toByte())
        val result = writeCharacteristic(portalCtrlChar, data)

        if (result) {
            Log.i(tag, "Portal reset to default command sent")
        }
        return result
    }

    /**
     * Check if portal upload is in progress
     */
    fun isPortalUploading(): Boolean = portalUploadInProgress

    /**
     * Set new admin password
     */
    suspend fun writeAdminPassword(newPassword: String): Boolean {
        if (!ensureAuthenticatedForWrite()) return false
        val characteristic = adminPasswordChar ?: return false
        val device = bluetoothGatt?.device ?: return false
        
        Log.i(tag, "Writing new admin password to ${device.address}")
        val success = writeCharacteristic(characteristic, newPassword.toByteArray(Charsets.UTF_8))
        if (!success && _authenticationState.value != AuthenticationState.AUTHENTICATED) {
            _authenticationState.value = AuthStateReducer.reduce(_authenticationState.value, AuthEvent.WRITE_REJECTED_BY_AUTH)
        }
        return success
    }

    /**
     * Get portal upload progress
     */
    fun getPortalUploadProgress(): StateFlow<Float> = portalUploadProgress.asStateFlow()

    /**
     * Calculate CRC32 of byte array
     */
    fun calculateCrc32(data: ByteArray): Int {
        var crc = 0xFFFFFFFF.toInt()
        for (byte in data) {
            crc = crc xor (byte.toInt() and 0xFF)
            for (i in 0 until 8) {
                crc = if (crc and 1 != 0) {
                    (crc ushr 1) xor 0xEDB88320.toInt()
                } else {
                    crc ushr 1
                }
            }
        }
        return crc xor 0xFFFFFFFF.toInt()
    }

    /**
     * ================================================================
     * AUTHENTICATION METHODS
     * ================================================================
     */

    /**
     * Find authentication characteristics
     */
    private suspend fun findAuthCharacteristics(gatt: BluetoothGatt) {
        val service = gatt.getService(java.util.UUID.fromString(BleConstants.PROMO_SERVICE_UUID))
        if (service == null) {
            Log.w(tag, "Service not found for auth characteristics")
            return
        }

        authChar = service.getCharacteristic(java.util.UUID.fromString(BleConstants.CHAR_AUTH))
        authStatusChar = service.getCharacteristic(java.util.UUID.fromString(BleConstants.CHAR_AUTH_STATUS))

        // Enable notifications for auth status
        enableNotifications(authStatusChar)
        Log.d(tag, "Authentication characteristics found")
    }

    /**
     * Authenticate with the device using password
     *
     * @param password Authentication password (e.g. 'admin123')
     * @return true if authentication command was sent successfully
     */
    suspend fun authenticate(password: String): Boolean {
        val characteristic = authChar ?: return false

        if (password.isEmpty()) {
            Log.w(tag, "Password cannot be empty")
            return false
        }

        // The firmware expects raw password bytes directly written to the auth characteristic
        val data = password.toByteArray(Charsets.UTF_8)

        _authenticationState.value = AuthenticationState.AUTHENTICATING

        val result = writeCharacteristic(characteristic, data)
        if (result) {
            Log.i(tag, "Authentication password sent")
            
            // Proactively try to read auth status after a short delay as fallback 
            // for cases where notifications might be missed
            scope.launch {
                delay(800)
                readAuthStatus()
            }
        }
        return result
    }

    /**
     * Proactively read authentication status
     */
    fun readAuthStatus(): Boolean {
        val characteristic = authStatusChar ?: return false
        
        return try {
            bluetoothGatt?.readCharacteristic(characteristic) ?: false
        } catch (e: SecurityException) {
            Log.e(tag, "Security exception during readAuthStatus", e)
            false
        }
    }

    /**
     * Logout - clear authentication state
     *
     * @return true if logout command was sent successfully
     */
    suspend fun logout(): Boolean {
        if (authChar == null) {
            return false
        }

        val data = byteArrayOf(BleConstants.AUTH_CMD_LOGOUT.toByte())
        _authenticationState.value = AuthenticationState.NOT_AUTHENTICATED
        return writeCharacteristic(authChar, data)
    }





    /**
     * Check if currently authenticated
     */
    fun isAuthenticated(): Boolean {
        return _authenticationState.value == AuthenticationState.AUTHENTICATED
    }

    private suspend fun ensureAuthenticatedForWrite(): Boolean {
        if (_authenticationState.value == AuthenticationState.AUTHENTICATED) {
            return true
        }
        val finalState = kotlinx.coroutines.withTimeoutOrNull(2000L) {
            _authenticationState.first { 
                it == AuthenticationState.AUTHENTICATED || 
                it == AuthenticationState.FAILED || 
                it == AuthenticationState.LOCKED 
            }
        }
        if (finalState != AuthenticationState.AUTHENTICATED) {
            if (_authenticationState.value != AuthenticationState.LOCKED && _authenticationState.value != AuthenticationState.FAILED) {
                _authenticationState.value = AuthStateReducer.reduce(_authenticationState.value, AuthEvent.WRITE_REJECTED_BY_AUTH)
            }
            return false
        }
        return true
    }

    /**
     * Update authentication state based on status characteristic
     */
    private fun updateAuthenticationState(status: Byte) {
        val event = AuthStateReducer.fromFirmwareStatus(status) ?: return
        val newState = AuthStateReducer.reduce(_authenticationState.value, event)
        if (_authenticationState.value != newState) {
            _authenticationState.value = newState
            when (newState) {
                AuthenticationState.AUTHENTICATED -> Log.i(tag, "Authentication successful")
                AuthenticationState.FAILED -> Log.w(tag, "Authentication failed")
                AuthenticationState.LOCKED -> Log.e(tag, "Device locked due to too many failed attempts")
                else -> {}
            }
        }
    }

}

/**
 * Connection state enumeration
 */
enum class ConnectionState {
    DISCONNECTED,
    CONNECTING,
    CONNECTED,
    DISCONNECTING
}

/**
 * Authentication state enumeration
 */
enum class AuthenticationState {
    NOT_AUTHENTICATED,
    REQUIRED,
    AUTHENTICATING,
    AUTHENTICATED,
    FAILED,
    LOCKED
}

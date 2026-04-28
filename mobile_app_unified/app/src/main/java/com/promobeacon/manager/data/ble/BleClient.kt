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

/**
 * BLE GATT服務UUID常量
 */
object BleConstants {
    // 統一服務UUID
    const val PROMO_SERVICE_UUID = "12345678-1234-1234-1234-123456789ABC"

    // 特徵UUID
    const val CHAR_MODE_CONTROL = "12345679-1234-1234-1234-123456789ABC"
    const val CHAR_MESSAGE = "1234567A-1234-1234-1234-123456789ABC"
    const val CHAR_CONFIG = "1234567B-1234-1234-1234-123456789ABC"
    const val CHAR_STATUS = "1234567C-1234-1234-1234-123456789ABC"
    const val CHAR_PROMO_TEXT = "1234567D-1234-1234-1234-123456789ABC"
    const val CHAR_PORTAL_DATA = "12345681-1234-1234-1234-123456789ABC"  // Portal data chunks
    const val CHAR_PORTAL_CTRL = "12345682-1234-1234-1234-123456789ABC"  // Portal control & status
    const val CHAR_AUTH = "12345683-1234-1234-1234-123456789ABC"  // Authentication
    const val CHAR_AUTH_STATUS = "12345685-1234-1234-1234-123456789ABC"  // Auth status
    const val CHAR_ADMIN_PASSWORD = "12345686-1234-1234-1234-123456789ABC"  // Admin password change
    const val CHAR_STATS = "1234567E-1234-1234-1234-123456789ABC"         // Aggregated stats
    const val CHAR_SESSIONS = "1234567F-1234-1234-1234-123456789ABC"      // Session history
    const val CHAR_SESSION_CTRL = "12345680-1234-1234-1234-123456789ABC"  // Session control commands

    // 命令常量
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
    const val PORTAL_CHUNK_SIZE = 200  // Max bytes per BLE write
    const val PORTAL_MAX_SIZE = 16384  // 16KB max HTML size
}

/**
 * BLE客戶端類
 * 封裝藍牙GATT操作
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

    // 狀態Flow
    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private val _deviceStatus = MutableStateFlow<ByteArray?>(null)
    val deviceStatus: StateFlow<ByteArray?> = _deviceStatus.asStateFlow()

    private val writeMutex = Mutex()
    private var lastWriteTime = 0L
    private val MIN_WRITE_INTERVAL = 50L

    internal var adminPasswordChar: BluetoothGattCharacteristic? = null
    internal var deviceNameChar: BluetoothGattCharacteristic? = null

    // 掃描結果
    private val _scanResults = MutableStateFlow<List<ScannedDevice>>(emptyList())
    val scanResults: StateFlow<List<ScannedDevice>> = _scanResults.asStateFlow()

    private var isScanning = false

    // 特徵引用
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

    // Authentication state
    private val _authenticationState = MutableStateFlow(AuthenticationState.NOT_AUTHENTICATED)
    val authenticationState: StateFlow<AuthenticationState> = _authenticationState.asStateFlow()

    // Portal upload state
    private var portalUploadInProgress = false
    private var portalUploadProgress = MutableStateFlow(0f)

    // GATT回調
    private val gattCallback = object : BluetoothGattCallback() {
        override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
            Log.d(tag, "onConnectionStateChange: status=$status, newState=$newState")

            if (status == BluetoothGatt.GATT_SUCCESS) {
                if (newState == BluetoothProfile.STATE_CONNECTED) {
                    _connectionState.value = ConnectionState.CONNECTED
                    Log.d(tag, "Connected to GATT server")
                    // 發現服務
                    discoverServices()
                    bluetoothGatt?.requestMtu(512)
                } else if (newState == BluetoothProfile.STATE_DISCONNECTED) {
                    _connectionState.value = ConnectionState.DISCONNECTED
                    Log.d(tag, "Disconnected from GATT server")
                    close()
                }
            } else {
                Log.e(tag, "Connection error: $status")
                _connectionState.value = ConnectionState.DISCONNECTED
                close()
            }
        }

        override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
            Log.d(tag, "onServicesDiscovered: status=$status")

            if (status == BluetoothGatt.GATT_SUCCESS) {
                Log.d(tag, "Services discovered")
                findCharacteristics(gatt)
            } else {
                Log.w(tag, "onServicesDiscovered received: $status")
            }
        }

        override fun onCharacteristicRead(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic, status: Int) {
            Log.d(tag, "onCharacteristicRead: ${characteristic.uuid}, status=$status")

            if (status == BluetoothGatt.GATT_SUCCESS) {
                when (characteristic.uuid.toString()) {
                    BleConstants.CHAR_STATUS -> {
                        _deviceStatus.value = characteristic.value
                    }
                    BleConstants.CHAR_AUTH_STATUS -> {
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

            if (characteristic.uuid.toString() == BleConstants.CHAR_STATUS) {
                _deviceStatus.value = characteristic.value
            } else if (characteristic.uuid.toString() == BleConstants.CHAR_AUTH_STATUS) {
                // Update authentication state from notification
                if (characteristic.value.isNotEmpty()) {
                    updateAuthenticationState(characteristic.value[0])
                }
            } else if (characteristic.uuid.toString() == BleConstants.CHAR_PORTAL_CTRL) {
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
        }
    }

    /**
     * 初始化BLE客戶端
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
     * 檢查BLE權限
     */
    fun hasRequiredPermissions(): Boolean {
        return ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.BLUETOOTH_CONNECT
        ) == PackageManager.PERMISSION_GRANTED
    }

    /**
     * 開始掃描設備
     */
    fun startScan() {
        if (!hasRequiredPermissions()) {
            Log.w(tag, "Missing BLUETOOTH_CONNECT permission")
            return
        }

        if (isScanning) {
            Log.d(tag, "Already scanning")
            return
        }

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
            Log.d(tag, "Starting scan with UUID filter: $PROMOBEACON_SERVICE_UUID")
            bluetoothScanner?.startScan(listOf(scanFilter), scanSettings, scanCallback)
            
            // Start fallback timer
            scanFallbackJob = scope.launch {
                delay(5000)
                if (_scanResults.value.isEmpty() && isScanning && !isScanFallbackActive) {
                    Log.w(tag, "No devices found with UUID filter, switching to fallback name-based scan")
                    stopScan()
                    delay(200) // Brief pause to ensure scanner resets
                    isScanning = true
                    isScanFallbackActive = true
                    bluetoothScanner?.startScan(null, scanSettings, scanCallback)
                }
            }
        } catch (e: SecurityException) {
            Log.e(tag, "Security exception during scan", e)
            isScanning = false
        }
    }

    /**
     * 停止掃描設備
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
     * 連接到設備
     */
    fun connect(device: ScannedDevice): Flow<ConnectionState> = flow {
        emit(ConnectionState.CONNECTING)

        try {
            // 停止掃描
            stopScan()

            // 斷開現有連接
            disconnect()

            val bluetoothDevice = bluetoothAdapter?.getRemoteDevice(device.address)
            if (bluetoothDevice == null) {
                emit(ConnectionState.DISCONNECTED)
                return@flow
            }

            // 連接
            _connectionState.value = ConnectionState.CONNECTING

            bluetoothGatt = bluetoothDevice.connectGatt(
                context,
                false,
                gattCallback,
                BluetoothDevice.TRANSPORT_LE
            )

            // 等待連接狀態變化
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
     * 斷開連接
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
     * 關閉GATT連接
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
        }
    }

    /**
     * 發現服務
     */
    private fun discoverServices() {
        try {
            bluetoothGatt?.discoverServices()
        } catch (e: SecurityException) {
            Log.e(tag, "Security exception during discoverServices", e)
        }
    }

    /**
     * 查找特徵
     */
    private fun findCharacteristics(gatt: BluetoothGatt) {
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

        // Find GAP Device Name
        val gapService = gatt.getService(java.util.UUID.fromString("00001800-0000-1000-8000-00805f9b34fb"))
        deviceNameChar = gapService?.getCharacteristic(java.util.UUID.fromString("00002a00-0000-1000-8000-00805f9b34fb"))

        // Authentication characteristics
        findAuthCharacteristics(gatt)

        // 啟用狀態通知
        enableNotifications(statusChar)
        // 啟用portal控制通知
        enableNotifications(portalCtrlChar)
    }

    /**
     * 啟用通知
     */
    private fun enableNotifications(characteristic: BluetoothGattCharacteristic?) {
        if (characteristic == null) return

        try {
            bluetoothGatt?.setCharacteristicNotification(characteristic, true)

            val descriptor = characteristic.getDescriptor(
                java.util.UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")
            )
            descriptor?.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
            bluetoothGatt?.writeDescriptor(descriptor)
        } catch (e: SecurityException) {
            Log.e(tag, "Security exception during enableNotifications", e)
        }
    }

    /**
     * 寫入模式控制
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
     * 寫入訊息
     */
    suspend fun writeMessage(message: String): Boolean {
        val bytes = message.toByteArray(Charsets.UTF_8)
        return writeCharacteristic(messageChar, bytes)
    }

    /**
     * 寫入宣傳文字
     */
    suspend fun writePromoText(text: String): Boolean {
        val bytes = text.toByteArray(Charsets.UTF_8)
        return writeCharacteristic(promoTextChar, bytes)
    }

    /**
     * 寫入配置命令
     */
    suspend fun writeConfig(command: Byte, param1: Short = 0, param2: Short = 0, param3: Byte = 0): Boolean {
        val data = byteArrayOf(command, (param1.toInt() and 0xFF).toByte(), (param1.toInt() shr 8 and 0xFF).toByte(),
            (param2.toInt() and 0xFF).toByte(), (param2.toInt() shr 8 and 0xFF).toByte(), param3)
        return writeCharacteristic(configChar, data)
    }

    suspend fun writeSsid(ssid: String): Boolean {
        val data = ssid.toByteArray(Charsets.UTF_8)
        return writeCharacteristic(configChar, data)
    }

    suspend fun writeWifiPassword(password: String): Boolean {
        val data = password.toByteArray(Charsets.UTF_8)
        return writeCharacteristic(configChar, data)
    }

    /**
     * 寫入特徵值
     */
    suspend fun writeCharacteristic(characteristic: BluetoothGattCharacteristic?, data: ByteArray): Boolean {
        if (characteristic == null) { return false }
        if (data.isEmpty()) { return false }
        return writeMutex.withLock {
            val now = System.currentTimeMillis()
            val elapsed = now - lastWriteTime
            if (elapsed < MIN_WRITE_INTERVAL) {
                kotlinx.coroutines.delay(MIN_WRITE_INTERVAL - elapsed)
            }
            try {
                characteristic.value = data
                characteristic.writeType = BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT
                val result = bluetoothGatt?.writeCharacteristic(characteristic) ?: false
                if (result) {
                    lastWriteTime = System.currentTimeMillis()
                    kotlinx.coroutines.delay(30)
                }
                result
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
     * 讀取狀態
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
     * 掃描回調
     */
    private val scanCallback = object : ScanCallback() {
        override fun onScanResult(callbackType: Int, result: ScanResult) {
            try {
                val device = result.device
                val name = device.name ?: "Unknown"
                val rssi = result.rssi

                // If in fallback mode, apply name filter. 
                // If in UUID mode, all results are already filtered by OS.
                val isMatch = if (isScanFallbackActive) {
                    name.contains("PROMO", ignoreCase = true) || name.contains("Beacon", ignoreCase = true)
                } else {
                    true
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

        // Data format: [Seq Num: 2 bytes] [Data: up to 200 bytes]
        val chunkData = ByteArray(2 + data.size)
        chunkData[0] = ((sequenceNumber shr 8) and 0xFF).toByte()
        chunkData[1] = (sequenceNumber and 0xFF).toByte()
        System.arraycopy(data, 0, chunkData, 2, data.size)

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
        val characteristic = adminPasswordChar ?: return false
        val device = bluetoothGatt?.device ?: return false
        
        Log.i(tag, "Writing new admin password to ${device.address}")
        return writeCharacteristic(characteristic, newPassword.toByteArray())
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
    private fun findAuthCharacteristics(gatt: BluetoothGatt) {
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

    /**
     * Update authentication state based on status characteristic
     */
    private fun updateAuthenticationState(status: Byte) {
        val statusInt = status.toInt() and 0xFF
        when (statusInt) {
            BleConstants.AUTH_STATUS_IDLE -> {
                // No change, keep current state
            }
            BleConstants.AUTH_STATUS_REQUIRED -> {
                _authenticationState.value = AuthenticationState.REQUIRED
            }
            BleConstants.AUTH_STATUS_SUCCESS -> {
                _authenticationState.value = AuthenticationState.AUTHENTICATED
                Log.i(tag, "Authentication successful")
            }
            BleConstants.AUTH_STATUS_FAILED -> {
                _authenticationState.value = AuthenticationState.FAILED
                Log.w(tag, "Authentication failed")
            }
            BleConstants.AUTH_STATUS_LOCKED -> {
                _authenticationState.value = AuthenticationState.LOCKED
                Log.e(tag, "Device locked due to too many failed attempts")
            }
        }
    }

}

/**
 * 連接狀態枚舉
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

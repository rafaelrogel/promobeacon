package com.promobeacon.manager

import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.content.Context
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.promobeacon.manager.data.ble.AuthEvent
import com.promobeacon.manager.data.ble.AuthStateReducer
import com.promobeacon.manager.data.ble.AuthenticationState
import com.promobeacon.manager.data.ble.BleClient
import com.promobeacon.manager.data.ble.BleConstants
import com.promobeacon.manager.domain.model.ConnectionState
import com.promobeacon.manager.domain.repository.DeviceRepository
import com.promobeacon.manager.domain.usecase.ConnectDeviceUseCase
import com.promobeacon.manager.domain.usecase.GetConnectionStateUseCase
import com.promobeacon.manager.domain.usecase.GetDeviceStatusUseCase
import com.promobeacon.manager.domain.usecase.ScanDevicesUseCase
import com.promobeacon.manager.ui.scan.ScanViewModel
import dagger.hilt.android.testing.HiltAndroidRule
import dagger.hilt.android.testing.HiltAndroidTest
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.rules.RuleChain
import org.junit.runner.RunWith
import javax.inject.Inject

/**
 * Instrumented BLE GATT E2E & Integration Test for PromoBeacon Android app.
 *
 * Verifies:
 * 1. ScanViewModel scanning & state flow observation
 * 2. ScanDevicesUseCase invocation & lifecycle without crash
 * 3. BleClient public API state & query on physical device
 * 4. AuthStateReducer state machine sanity (androidTest parity with BleClientAuthStateTest)
 * 5. Tolerance when Bluetooth radio is disabled (Assume.assumeTrue)
 * 6. Compose UI ScanScreen rendering & top bar verification
 */
@HiltAndroidTest
@RunWith(AndroidJUnit4::class)
class ScanFlowIntegrationTest {

    val hiltRule = HiltAndroidRule(this)
    val composeTestRule = createAndroidComposeRule<MainActivity>()

    @get:Rule
    val ruleChain: RuleChain = RuleChain.outerRule(hiltRule).around(composeTestRule)

    @Inject
    lateinit var bleClient: BleClient

    @Inject
    lateinit var deviceRepository: DeviceRepository

    @Inject
    lateinit var scanDevicesUseCase: ScanDevicesUseCase

    @Inject
    lateinit var connectDeviceUseCase: ConnectDeviceUseCase

    @Inject
    lateinit var getConnectionStateUseCase: GetConnectionStateUseCase

    @Inject
    lateinit var getDeviceStatusUseCase: GetDeviceStatusUseCase

    private lateinit var scanViewModel: ScanViewModel
    private var bluetoothAdapter: BluetoothAdapter? = null

    @Before
    fun setUp() {
        hiltRule.inject()
        val context = ApplicationProvider.getApplicationContext<Context>()
        val bluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager
        bluetoothAdapter = bluetoothManager?.adapter

        scanViewModel = ScanViewModel(
            scanDevicesUseCase = scanDevicesUseCase,
            connectDeviceUseCase = connectDeviceUseCase,
            getConnectionStateUseCase = getConnectionStateUseCase,
            getDeviceStatusUseCase = getDeviceStatusUseCase
        )
    }

    /**
     * 1. Verifies ScanViewModel starts scanning and observes the device list flow
     */
    @Test
    fun testScanViewModel_startsScanningAndObservesDeviceListFlow() = runTest {
        assumeTrue(bluetoothAdapter != null && bluetoothAdapter!!.isEnabled)

        // Initial state
        assertNotNull(scanViewModel.uiState.value)
        val initialScanningState = scanViewModel.uiState.value.isScanning

        // Start scanning
        scanViewModel.startScan()
        assertTrue("ScanViewModel should reflect scanning state", scanViewModel.uiState.value.isScanning)

        // Allow some time for scanning flow to emit
        delay(1500)
        assertNotNull("Devices list should not be null", scanViewModel.uiState.value.devices)

        // Stop scanning
        scanViewModel.stopScan()
        assertFalse("ScanViewModel should reflect stopped scanning state", scanViewModel.uiState.value.isScanning)
    }

    /**
     * 2. Verifies ScanDevicesUseCase can be invoked without crash
     */
    @Test
    fun testScanDevicesUseCase_invokedWithoutCrash() = runTest {
        assumeTrue(bluetoothAdapter != null && bluetoothAdapter!!.isEnabled)

        val scanFlow = scanDevicesUseCase(timeoutMs = 3000)
        assertNotNull("Scan flow should be non-null", scanFlow)

        val collectJob = launch {
            scanFlow.collect { devices ->
                assertNotNull("Collected device list should not be null", devices)
            }
        }

        delay(1000)
        scanDevicesUseCase.stop()
        collectJob.cancel()
    }

    /**
     * 3. Verifies BleClient public API can be queried on a real device
     */
    @Test
    fun testBleClient_publicApiCanBeQueriedOnRealDevice() {
        // Assert public StateFlows and methods are accessible
        assertNotNull("BleClient scanResults should be initialized", bleClient.scanResults.value)
        assertEquals("Initial connectionState should be DISCONNECTED", ConnectionState.DISCONNECTED, bleClient.connectionState.value)
        assertNull("Initial deviceStatus should be null", bleClient.deviceStatus.value)
        assertFalse("Initial isAuthenticated should be false", bleClient.isAuthenticated())
        assertFalse("Initial isPortalUploading should be false", bleClient.isPortalUploading())

        // Check CRC32 utility calculation
        val testPayload = "PromoBeaconTest".toByteArray(Charsets.UTF_8)
        val crc = bleClient.calculateCrc32(testPayload)
        assertTrue("CRC32 calculation should return non-zero for test string", crc != 0)

        // If Bluetooth radio is available, test start/stop scan API
        if (bluetoothAdapter?.isEnabled == true) {
            bleClient.startScan()
            assertNotNull(bleClient.scanResults.value)
            bleClient.stopScan()
        }
    }

    /**
     * 4. Tests the BleClientAuthStateTest scenario as androidTest sanity
     */
    @Test
    fun testBleClientAuthState_sanityReducerTransitions() {
        // Disconnect resets all states to NOT_AUTHENTICATED
        for (initialState in AuthenticationState.values()) {
            val nextState = AuthStateReducer.reduce(initialState, AuthEvent.ON_DISCONNECT)
            assertEquals(
                "Disconnect from state $initialState must reset to NOT_AUTHENTICATED",
                AuthenticationState.NOT_AUTHENTICATED,
                nextState
            )
        }

        // Connect start resets to NOT_AUTHENTICATED
        for (initialState in AuthenticationState.values()) {
            val nextState = AuthStateReducer.reduce(initialState, AuthEvent.ON_CONNECT_START)
            assertEquals(
                "Connect start from state $initialState must reset to NOT_AUTHENTICATED",
                AuthenticationState.NOT_AUTHENTICATED,
                nextState
            )
        }

        // Write rejected transitions to REQUIRED
        val statesToTest = listOf(
            AuthenticationState.AUTHENTICATED,
            AuthenticationState.NOT_AUTHENTICATED,
            AuthenticationState.AUTHENTICATING
        )
        for (state in statesToTest) {
            val nextState = AuthStateReducer.reduce(state, AuthEvent.WRITE_REJECTED_BY_AUTH)
            assertEquals(
                "Write rejected by auth from state $state should transition to REQUIRED",
                AuthenticationState.REQUIRED,
                nextState
            )
        }

        // Auth status transitions
        assertEquals(
            AuthenticationState.REQUIRED,
            AuthStateReducer.reduce(AuthenticationState.AUTHENTICATED, AuthEvent.AUTH_STATUS_REQUIRED)
        )
        assertEquals(
            AuthenticationState.AUTHENTICATED,
            AuthStateReducer.reduce(AuthenticationState.AUTHENTICATING, AuthEvent.AUTH_STATUS_SUCCESS)
        )
        assertEquals(
            AuthenticationState.FAILED,
            AuthStateReducer.reduce(AuthenticationState.AUTHENTICATING, AuthEvent.AUTH_STATUS_FAILED)
        )
        assertEquals(
            AuthenticationState.LOCKED,
            AuthStateReducer.reduce(AuthenticationState.AUTHENTICATING, AuthEvent.AUTH_STATUS_LOCKED)
        )

        // Firmware status byte mapping
        assertEquals(AuthEvent.AUTH_STATUS_IDLE, AuthStateReducer.fromFirmwareStatus(BleConstants.AUTH_STATUS_IDLE.toByte()))
        assertEquals(AuthEvent.AUTH_STATUS_REQUIRED, AuthStateReducer.fromFirmwareStatus(BleConstants.AUTH_STATUS_REQUIRED.toByte()))
        assertEquals(AuthEvent.AUTH_STATUS_SUCCESS, AuthStateReducer.fromFirmwareStatus(BleConstants.AUTH_STATUS_SUCCESS.toByte()))
        assertEquals(AuthEvent.AUTH_STATUS_FAILED, AuthStateReducer.fromFirmwareStatus(BleConstants.AUTH_STATUS_FAILED.toByte()))
        assertEquals(AuthEvent.AUTH_STATUS_LOCKED, AuthStateReducer.fromFirmwareStatus(BleConstants.AUTH_STATUS_LOCKED.toByte()))
        assertNull(AuthStateReducer.fromFirmwareStatus(0x99.toByte()))
    }

    /**
     * 5 & Compose UI: Verifies ScanScreen renders UI elements (TopBar title, etc.)
     */
    @Test
    fun testComposeUi_rendersScanScreenAndComponents() {
        // Verify Activity launched and top bar title "Scan Devices" is rendered
        assertNotNull(composeTestRule.activity)
        composeTestRule.onNodeWithText("Scan Devices").assertExists().assertIsDisplayed()
    }
}

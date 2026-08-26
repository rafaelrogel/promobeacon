package com.promobeacon.manager.ui.dashboard

import com.promobeacon.manager.data.ble.AuthenticationState
import com.promobeacon.manager.data.ble.BleClient
import com.promobeacon.manager.domain.model.ConnectionState
import com.promobeacon.manager.domain.model.DeviceStatus
import com.promobeacon.manager.domain.model.GModeConfig
import com.promobeacon.manager.domain.usecase.ExportStatsToCsvUseCase
import com.promobeacon.manager.domain.usecase.GetConnectionStateUseCase
import com.promobeacon.manager.domain.usecase.GetDeviceStatusUseCase
import com.promobeacon.manager.domain.usecase.ReadGModeConfigUseCase
import com.promobeacon.manager.domain.usecase.RebootDeviceUseCase
import com.promobeacon.manager.domain.usecase.ResetToDefaultsUseCase
import com.promobeacon.manager.domain.usecase.UpdateGModeConfigUseCase
import com.promobeacon.manager.domain.usecase.UploadPortalUseCase
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.every
import io.mockk.mockk
import io.mockk.verify
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class DashboardViewModelTest {

    private val testDispatcher = StandardTestDispatcher()

    private lateinit var bleClient: BleClient
    private lateinit var getConnectionState: GetConnectionStateUseCase
    private lateinit var getDeviceStatus: GetDeviceStatusUseCase
    private lateinit var readGModeConfig: ReadGModeConfigUseCase
    private lateinit var updateGModeConfig: UpdateGModeConfigUseCase
    private lateinit var rebootDevice: RebootDeviceUseCase
    private lateinit var resetToDefaults: ResetToDefaultsUseCase
    private lateinit var exportStats: ExportStatsToCsvUseCase
    private lateinit var uploadPortal: UploadPortalUseCase

    @Before
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        bleClient = mockk(relaxed = true)
        getConnectionState = mockk()
        getDeviceStatus = mockk()
        readGModeConfig = mockk()
        updateGModeConfig = mockk()
        rebootDevice = mockk()
        resetToDefaults = mockk()
        exportStats = mockk()
        uploadPortal = mockk()

        every { bleClient.authenticationState } returns MutableStateFlow(AuthenticationState.NOT_AUTHENTICATED)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    private fun newViewModel() = DashboardViewModel(
        bleClient = bleClient,
        getConnectionStateUseCase = getConnectionState,
        getDeviceStatusUseCase = getDeviceStatus,
        readGModeConfigUseCase = readGModeConfig,
        updateGModeConfigUseCase = updateGModeConfig,
        rebootDeviceUseCase = rebootDevice,
        resetToDefaultsUseCase = resetToDefaults,
        exportStatsToCsvUseCase = exportStats,
        uploadPortalUseCase = uploadPortal
    )

    @Test
    fun `fresh CONNECTED transition resets cached gModeConfig to defaults to avoid stale UI`() = runTest {
        val connectionFlow = MutableStateFlow(ConnectionState.DISCONNECTED)
        every { getConnectionState.invoke() } returns connectionFlow
        every { getDeviceStatus.invoke() } returns flowOf(DeviceStatus())
        coEvery { readGModeConfig.invoke() } returns Result.success(GModeConfig())

        val vm = newViewModel()
        testDispatcher.scheduler.advanceUntilIdle()

        // Emit CONNECTED for the first time → should reset config and trigger load
        connectionFlow.value = ConnectionState.CONNECTED
        testDispatcher.scheduler.advanceUntilIdle()

        // After fresh connect, gModeConfig is reset to defaults (default ssid = PromoBeacon)
        assertEquals("PromoBeacon", vm.uiState.value.gModeConfig.ssid)
        assertEquals(ConnectionState.CONNECTED, vm.uiState.value.connectionState)
        // Auth must be reset to NOT_AUTHENTICATED so user re-auths on new session
        assertEquals(AuthenticationState.NOT_AUTHENTICATED, vm.uiState.value.authenticationState)
        coVerify(exactly = 1) { readGModeConfig.invoke() }
    }

    @Test
    fun `repeated CONNECTED emissions do not reload config (only on transition)`() = runTest {
        val connectionFlow = MutableStateFlow(ConnectionState.DISCONNECTED)
        every { getConnectionState.invoke() } returns connectionFlow
        every { getDeviceStatus.invoke() } returns flowOf(DeviceStatus())
        coEvery { readGModeConfig.invoke() } returns Result.success(GModeConfig())

        val vm = newViewModel()
        testDispatcher.scheduler.advanceUntilIdle()

        connectionFlow.value = ConnectionState.CONNECTED
        testDispatcher.scheduler.advanceUntilIdle()
        // Same state again → should not re-fetch
        connectionFlow.value = ConnectionState.CONNECTED
        testDispatcher.scheduler.advanceUntilIdle()

        // readGModeConfig called exactly once (only on the transition)
        coVerify(exactly = 1) { readGModeConfig.invoke() }
    }

    @Test
    fun `DISCONNECTED transition clears gModeConfig auth and transient flags`() = runTest {
        val connectionFlow = MutableStateFlow(ConnectionState.DISCONNECTED)
        every { getConnectionState.invoke() } returns connectionFlow
        every { getDeviceStatus.invoke() } returns flowOf(DeviceStatus(isConnected = true))
        coEvery { readGModeConfig.invoke() } returns Result.success(
            GModeConfig(ssid = "OLD_SSID", deviceName = "OldName", promoText = "OldPromo")
        )

        val vm = newViewModel()
        testDispatcher.scheduler.advanceUntilIdle()

        // Connect → loads config
        connectionFlow.value = ConnectionState.CONNECTED
        testDispatcher.scheduler.advanceUntilIdle()
        assertEquals("OLD_SSID", vm.uiState.value.gModeConfig.ssid)

        // Disconnect
        connectionFlow.value = ConnectionState.DISCONNECTED
        testDispatcher.scheduler.advanceUntilIdle()

        assertEquals(ConnectionState.DISCONNECTED, vm.uiState.value.connectionState)
        assertEquals("PromoBeacon", vm.uiState.value.gModeConfig.ssid) // cleared to default
        assertEquals(AuthenticationState.NOT_AUTHENTICATED, vm.uiState.value.authenticationState)
        assertFalse(vm.uiState.value.isLoading)
        assertFalse(vm.uiState.value.isSaving)
        assertFalse(vm.uiState.value.isUploading)
    }

    @Test
    fun `reconnect after disconnect reloads config and resets auth`() = runTest {
        val connectionFlow = MutableStateFlow(ConnectionState.DISCONNECTED)
        every { getConnectionState.invoke() } returns connectionFlow
        every { getDeviceStatus.invoke() } returns flowOf(DeviceStatus())
        coEvery { readGModeConfig.invoke() } returns Result.success(
            GModeConfig(ssid = "FRESH_SSID")
        )

        val vm = newViewModel()
        testDispatcher.scheduler.advanceUntilIdle()

        // First session
        connectionFlow.value = ConnectionState.CONNECTED
        testDispatcher.scheduler.advanceUntilIdle()
        assertEquals("FRESH_SSID", vm.uiState.value.gModeConfig.ssid)

        // Disconnect
        connectionFlow.value = ConnectionState.DISCONNECTED
        testDispatcher.scheduler.advanceUntilIdle()
        assertEquals("PromoBeacon", vm.uiState.value.gModeConfig.ssid)

        // Reconnect — should fetch again and populate with new values
        coEvery { readGModeConfig.invoke() } returns Result.success(
            GModeConfig(ssid = "ANOTHER_SSID")
        )
        connectionFlow.value = ConnectionState.CONNECTED
        testDispatcher.scheduler.advanceUntilIdle()

        assertEquals("ANOTHER_SSID", vm.uiState.value.gModeConfig.ssid)
        assertEquals(AuthenticationState.NOT_AUTHENTICATED, vm.uiState.value.authenticationState)
        coVerify(exactly = 2) { readGModeConfig.invoke() }
    }

    @Test
    fun `initial state has empty gModeConfig and NOT_AUTHENTICATED`() = runTest {
        val connectionFlow = MutableStateFlow(ConnectionState.DISCONNECTED)
        every { getConnectionState.invoke() } returns connectionFlow
        every { getDeviceStatus.invoke() } returns flowOf(DeviceStatus())
        coEvery { readGModeConfig.invoke() } returns Result.success(GModeConfig())

        val vm = newViewModel()

        assertEquals("PromoBeacon", vm.uiState.value.gModeConfig.ssid)
        assertEquals(AuthenticationState.NOT_AUTHENTICATED, vm.uiState.value.authenticationState)
        assertEquals(ConnectionState.DISCONNECTED, vm.uiState.value.connectionState)
        assertFalse(vm.uiState.value.isLoading)
    }
}

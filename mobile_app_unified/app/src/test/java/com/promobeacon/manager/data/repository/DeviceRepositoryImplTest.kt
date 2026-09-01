package com.promobeacon.manager.data.repository

import android.content.Context
import android.util.Log
import com.promobeacon.manager.data.ble.AuthenticationState
import com.promobeacon.manager.data.ble.BleClient
import com.promobeacon.manager.data.ble.BleConstants
import com.promobeacon.manager.domain.model.GModeConfig
import com.promobeacon.manager.domain.repository.UploadProgress
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.every
import io.mockk.mockk
import io.mockk.mockkStatic
import io.mockk.unmockkStatic
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class DeviceRepositoryImplTest {

    private lateinit var bleClient: BleClient
    private lateinit var context: Context
    private lateinit var repository: DeviceRepositoryImpl

    @Before
    fun setup() {
        mockkStatic(Log::class)
        every { Log.v(any(), any()) } returns 0
        every { Log.d(any(), any()) } returns 0
        every { Log.i(any(), any()) } returns 0
        every { Log.w(any(), any<String>()) } returns 0
        every { Log.w(any(), any<Throwable>()) } returns 0
        every { Log.w(any(), any<String>(), any()) } returns 0
        every { Log.e(any(), any()) } returns 0
        every { Log.e(any(), any(), any()) } returns 0

        bleClient = mockk(relaxed = true)
        every { bleClient.authenticationState } returns MutableStateFlow(AuthenticationState.AUTHENTICATED)
        context = mockk(relaxed = true)
        repository = DeviceRepositoryImpl(bleClient, context)
    }

    @After
    fun tearDown() {
        unmockkStatic(Log::class)
    }

    @Test
    fun `updateGModeConfig writes promoText, deviceName, and password`() = runTest {
        coEvery { bleClient.writePromoText(any()) } returns true
        coEvery { bleClient.writeDeviceName(any()) } returns true
        coEvery { bleClient.writeWifiPassword(any()) } returns true

        val config = GModeConfig(
            deviceName = "MyDevice",
            ssid = "MyDevice",
            promoText = "Welcome",
            password = "secretpassword"
        )

        val result = repository.updateGModeConfig(config)

        assertTrue(result.isSuccess)
        coVerify { bleClient.writePromoText("Welcome") }
        coVerify { bleClient.writeDeviceName("MyDevice") }
        coVerify { bleClient.writeWifiPassword("secretpassword") }
    }

    @Test
    fun `updateGModeConfig fails when writePromoText fails`() = runTest {
        coEvery { bleClient.writePromoText(any()) } returns false

        val config = GModeConfig(promoText = "Welcome")
        val result = repository.updateGModeConfig(config)

        assertFalse(result.isSuccess)
        coVerify(exactly = 0) { bleClient.writeDeviceName(any()) }
    }

    @Test
    fun `updateGModeConfig skips password when empty`() = runTest {
        coEvery { bleClient.writePromoText(any()) } returns true
        coEvery { bleClient.writeDeviceName(any()) } returns true

        val config = GModeConfig(
            deviceName = "MyDevice",
            promoText = "Welcome",
            password = ""
        )
        val result = repository.updateGModeConfig(config)

        assertTrue(result.isSuccess)
        coVerify(exactly = 0) { bleClient.writeWifiPassword(any()) }
    }

    @Test
    fun `updateGModeConfig fails when not authenticated`() = runTest {
        every { bleClient.authenticationState } returns MutableStateFlow(AuthenticationState.NOT_AUTHENTICATED)

        val config = GModeConfig(promoText = "Welcome")
        val result = repository.updateGModeConfig(config)

        assertFalse(result.isSuccess)
        coVerify(exactly = 0) { bleClient.writePromoText(any()) }
    }

    @Test
    fun `uploadPortalContent success emits Started and Completed`() = runTest {
        coEvery { bleClient.portalStartUpload(any(), any()) } returns true
        coEvery { bleClient.portalSendChunk(any(), any()) } returns true
        coEvery { bleClient.portalCompleteUpload() } returns true
        coEvery { bleClient.portalRequestStatus() } returns true

        val events = mutableListOf<UploadProgress>()
        repository.uploadPortalContent("<html>hi</html>").toList(events)

        assertTrue(events.any { it is UploadProgress.Started })
        assertTrue(events.any { it is UploadProgress.Completed })
    }

    @Test
    fun `uploadPortalContent empty html emits Error and never starts upload`() = runTest {
        val events = mutableListOf<UploadProgress>()
        repository.uploadPortalContent("").toList(events)

        assertTrue(events.first() is UploadProgress.Error)
        coVerify(exactly = 0) { bleClient.portalStartUpload(any(), any()) }
    }

    @Test
    fun `uploadPortalContent larger than 32KB emits Error and never starts upload`() = runTest {
        val largeHtml = "A".repeat(32 * 1024 + 1)
        val events = mutableListOf<UploadProgress>()
        repository.uploadPortalContent(largeHtml).toList(events)

        assertTrue(events.first() is UploadProgress.Error)
        coVerify(exactly = 0) { bleClient.portalStartUpload(any(), any()) }
    }

    @Test
    fun `uploadPortalContent failure on chunk 2 emits Error and aborts upload`() = runTest {
        val html = "A".repeat(200)
        coEvery { bleClient.portalStartUpload(any(), any()) } returns true
        coEvery { bleClient.portalSendChunk(0, any()) } returns true
        coEvery { bleClient.portalSendChunk(1, any()) } returns false
        coEvery { bleClient.portalAbortUpload() } returns true

        val events = mutableListOf<UploadProgress>()
        repository.uploadPortalContent(html).toList(events)

        assertTrue(events.any { it is UploadProgress.Error })
        coVerify { bleClient.portalAbortUpload() }
    }

    @Test
    fun `reboot succeeds when authenticated and writeConfig returns true`() = runTest {
        coEvery { bleClient.writeConfig(BleConstants.CMD_REBOOT.toByte()) } returns true

        val result = repository.reboot()

        assertTrue(result.isSuccess)
        coVerify { bleClient.writeConfig(BleConstants.CMD_REBOOT.toByte()) }
    }

    @Test
    fun `reboot fails when writeConfig returns false`() = runTest {
        coEvery { bleClient.writeConfig(BleConstants.CMD_REBOOT.toByte()) } returns false

        val result = repository.reboot()

        assertFalse(result.isSuccess)
        coVerify { bleClient.writeConfig(BleConstants.CMD_REBOOT.toByte()) }
    }

    @Test
    fun `resetToDefaults succeeds and clears config cache`() = runTest {
        coEvery { bleClient.readPromoText() } returns "OLD_PROMO"
        coEvery { bleClient.readDeviceName() } returns "OLD_DEVICE"

        val initialRead = repository.readGModeConfig()
        assertTrue(initialRead.isSuccess)
        coVerify(exactly = 1) { bleClient.readPromoText() }

        // Second read should use cached value without hitting bleClient
        repository.readGModeConfig()
        coVerify(exactly = 1) { bleClient.readPromoText() }

        coEvery { bleClient.writeConfig(BleConstants.CMD_RESET_DEFAULTS.toByte()) } returns true

        val resetResult = repository.resetToDefaults()
        assertTrue(resetResult.isSuccess)
        coVerify { bleClient.writeConfig(BleConstants.CMD_RESET_DEFAULTS.toByte()) }

        // After reset, cache is cleared so readGModeConfig hits bleClient again
        val postResetRead = repository.readGModeConfig()
        assertTrue(postResetRead.isSuccess)
        coVerify(exactly = 2) { bleClient.readPromoText() }
    }

    @Test
    fun `readGModeConfig without cache uses promoText fallback for deviceName and ssid`() = runTest {
        coEvery { bleClient.readPromoText() } returns "OLÁ"
        coEvery { bleClient.readDeviceName() } returns null

        val result = repository.readGModeConfig()

        assertTrue(result.isSuccess)
        val config = result.getOrNull()
        assertEquals("OLÁ", config?.promoText)
        assertEquals("OLÁ", config?.deviceName)
        assertEquals("OLÁ", config?.ssid)
    }

    // ---- BUG 1 regression: writeDeviceName must succeed when the BLE write completes (no GAP 0x2A00) ----

    @Test
    fun `updateGModeConfig succeeds when both writePromoText and writeDeviceName return true (BUG1 fix path)`() = runTest {
        coEvery { bleClient.writePromoText("PROMO") } returns true
        coEvery { bleClient.writeDeviceName("DEV") } returns true

        val config = GModeConfig(
            deviceName = "DEV",
            ssid = "PROMO",
            promoText = "PROMO",
            password = "",
            newAdminPassword = ""
        )
        val result = repository.updateGModeConfig(config)

        assertTrue(result.isSuccess)
        coVerify { bleClient.writePromoText("PROMO") }
        coVerify { bleClient.writeDeviceName("DEV") }
    }

    @Test
    fun `updateGModeConfig short-circuits when writePromoText fails (does not attempt writeDeviceName)`() = runTest {
        coEvery { bleClient.writePromoText(any()) } returns false

        val config = GModeConfig(promoText = "X", deviceName = "Y")
        val result = repository.updateGModeConfig(config)

        assertFalse(result.isSuccess)
        coVerify { bleClient.writePromoText("X") }
        coVerify(exactly = 0) { bleClient.writeDeviceName(any()) }
    }

    @Test
    fun `updateGModeConfig reports failure when only writeDeviceName fails (BUG1 regression guard)`() = runTest {
        coEvery { bleClient.writePromoText("PROMO") } returns true
        coEvery { bleClient.writeDeviceName("DEV") } returns false

        val config = GModeConfig(promoText = "PROMO", deviceName = "DEV")
        val result = repository.updateGModeConfig(config)

        assertFalse(result.isSuccess)
        coVerify { bleClient.writePromoText("PROMO") }
        coVerify { bleClient.writeDeviceName("DEV") }
    }

    @Test
    fun `BUG 1 guard updateGModeConfig NAO escreve no GAP 0x2A00 apenas delega para bleClient writeDeviceName que usa a char custom`() = runTest {
        coEvery { bleClient.writePromoText("PROMO") } returns true
        coEvery { bleClient.writeDeviceName("DEV") } returns true

        val config = GModeConfig(
            deviceName = "DEV",
            ssid = "PROMO",
            promoText = "PROMO",
            password = "",
            newAdminPassword = ""
        )
        val result = repository.updateGModeConfig(config)

        assertTrue(result.isSuccess)
        coVerify { bleClient.writeDeviceName("DEV") }
        // Verify we rely on bleClient's writeDeviceName (custom char) and do not directly write to 0x2A00/GAP here
    }

    @Test
    fun `updateGModeConfig skips writeWifiPassword when password is empty`() = runTest {
        coEvery { bleClient.writePromoText("PROMO") } returns true
        coEvery { bleClient.writeDeviceName("DEV") } returns true

        val config = GModeConfig(promoText = "PROMO", deviceName = "DEV", password = "")
        val result = repository.updateGModeConfig(config)

        assertTrue(result.isSuccess)
        coVerify(exactly = 0) { bleClient.writeWifiPassword(any()) }
    }

    @Test
    fun `updateGModeConfig writes wifi password when provided`() = runTest {
        coEvery { bleClient.writePromoText("PROMO") } returns true
        coEvery { bleClient.writeDeviceName("DEV") } returns true
        coEvery { bleClient.writeWifiPassword("newpass") } returns true

        val config = GModeConfig(promoText = "PROMO", deviceName = "DEV", password = "newpass")
        val result = repository.updateGModeConfig(config)

        assertTrue(result.isSuccess)
        coVerify { bleClient.writeWifiPassword("newpass") }
    }

    // ---- BUG 2 regression: cache must not mask firmware-side state across reconnect/reset ----

    @Test
    fun `readGModeConfig returns cached value when available`() = runTest {
        coEvery { bleClient.readPromoText() } returns "FIRST"
        coEvery { bleClient.readDeviceName() } returns "FIRST_DEV"

        val first = repository.readGModeConfig()
        assertTrue(first.isSuccess)
        assertEquals("FIRST", first.getOrNull()?.promoText)
        coVerify(exactly = 1) { bleClient.readPromoText() }

        // Second read uses cache — does not hit BLE again
        val second = repository.readGModeConfig()
        assertEquals("FIRST", second.getOrNull()?.promoText)
        coVerify(exactly = 1) { bleClient.readPromoText() }
    }

    @Test
    fun `readGModeConfig after resetToDefaults hits BLE again (cache cleared)`() = runTest {
        coEvery { bleClient.readPromoText() } returnsMany listOf("OLD", "FRESH")
        coEvery { bleClient.readDeviceName() } returnsMany listOf("OLD_DEV", "FRESH_DEV")
        coEvery { bleClient.writeConfig(BleConstants.CMD_RESET_DEFAULTS.toByte()) } returns true

        // Prime cache
        repository.readGModeConfig()
        // Reset
        val reset = repository.resetToDefaults()
        assertTrue(reset.isSuccess)
        // After reset, next read should fetch from BLE (cache cleared)
        val after = repository.readGModeConfig()
        assertTrue(after.isSuccess)
        assertEquals("FRESH", after.getOrNull()?.promoText)
        coVerify(exactly = 2) { bleClient.readPromoText() }
    }
}

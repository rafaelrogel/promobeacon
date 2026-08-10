package com.promobeacon.manager.data.repository

import android.content.Context
import com.promobeacon.manager.data.ble.AuthenticationState
import com.promobeacon.manager.data.ble.BleClient
import com.promobeacon.manager.domain.model.GModeConfig
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertTrue
import org.junit.Assert.assertFalse
import org.junit.Before
import org.junit.Test

class DeviceRepositoryImplTest {

    private lateinit var bleClient: BleClient
    private lateinit var context: Context
    private lateinit var repository: DeviceRepositoryImpl

    @Before
    fun setup() {
        bleClient = mockk(relaxed = true)
        every { bleClient.authenticationState } returns MutableStateFlow(AuthenticationState.AUTHENTICATED)
        context = mockk(relaxed = true)
        repository = DeviceRepositoryImpl(bleClient, context)
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
}

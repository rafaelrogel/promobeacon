package com.promobeacon.manager.domain.usecase

import com.promobeacon.manager.domain.model.GModeConfig
import com.promobeacon.manager.domain.repository.DeviceRepository
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class UpdateGModeConfigUseCaseTest {

    private lateinit var repository: DeviceRepository
    private lateinit var useCase: UpdateGModeConfigUseCase

    @Before
    fun setup() {
        repository = mockk(relaxed = true)
        useCase = UpdateGModeConfigUseCase(repository)
    }

    @Test
    fun `invoke with blank ssid returns failure and never calls repository`() = runTest {
        val config = GModeConfig(
            ssid = "   ",
            deviceName = "Device",
            promoText = "Promo"
        )

        val result = useCase(config)

        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull() is IllegalArgumentException)
        assertEquals("SSID cannot be empty", result.exceptionOrNull()?.message)
        coVerify(exactly = 0) { repository.updateGModeConfig(any()) }
    }

    @Test
    fun `invoke with ssid longer than 32 chars returns failure and never calls repository`() = runTest {
        val config = GModeConfig(
            ssid = "A".repeat(33),
            deviceName = "Device",
            promoText = "Promo"
        )

        val result = useCase(config)

        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull() is IllegalArgumentException)
        assertEquals("SSID cannot exceed 32 characters", result.exceptionOrNull()?.message)
        coVerify(exactly = 0) { repository.updateGModeConfig(any()) }
    }

    @Test
    fun `invoke with promoText longer than 32 chars returns failure and never calls repository`() = runTest {
        val config = GModeConfig(
            ssid = "ValidSSID",
            deviceName = "Device",
            promoText = "A".repeat(33)
        )

        val result = useCase(config)

        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull() is IllegalArgumentException)
        assertEquals("Promotion text cannot exceed 32 characters", result.exceptionOrNull()?.message)
        coVerify(exactly = 0) { repository.updateGModeConfig(any()) }
    }

    @Test
    fun `invoke with valid config delegates to repository`() = runTest {
        val config = GModeConfig(
            ssid = "ValidSSID",
            deviceName = "ValidDevice",
            promoText = "ValidPromo",
            password = "password123"
        )
        coEvery { repository.updateGModeConfig(config) } returns Result.success(Unit)

        val result = useCase(config)

        assertTrue(result.isSuccess)
        coVerify(exactly = 1) { repository.updateGModeConfig(config) }
    }
}

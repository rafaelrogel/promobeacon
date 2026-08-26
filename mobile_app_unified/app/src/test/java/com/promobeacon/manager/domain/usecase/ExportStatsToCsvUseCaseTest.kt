package com.promobeacon.manager.domain.usecase

import com.promobeacon.manager.domain.repository.DeviceRepository
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class ExportStatsToCsvUseCaseTest {

    private lateinit var repository: DeviceRepository
    private lateinit var useCase: ExportStatsToCsvUseCase

    @Before
    fun setup() {
        repository = mockk(relaxed = true)
        useCase = ExportStatsToCsvUseCase(repository)
    }

    @Test
    fun `invoke with blank ip returns failure and never calls repository`() = runTest {
        val result = useCase("   ")

        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull() is IllegalArgumentException)
        assertEquals("Device IP address cannot be empty", result.exceptionOrNull()?.message)
        coVerify(exactly = 0) { repository.exportStatsToCsv(any()) }
    }

    @Test
    fun `invoke with invalid ip format returns failure and never calls repository`() = runTest {
        val result = useCase("abc")

        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull() is IllegalArgumentException)
        assertEquals("Invalid IP address format", result.exceptionOrNull()?.message)
        coVerify(exactly = 0) { repository.exportStatsToCsv(any()) }
    }

    @Test
    fun `invoke with ip 999_1_1_1 passes regex validation and delegates to repository`() = runTest {
        val ip = "999.1.1.1"
        coEvery { repository.exportStatsToCsv(ip) } returns Result.success("/tmp/stats_999.csv")

        val result = useCase(ip)

        assertTrue(result.isSuccess)
        assertEquals("/tmp/stats_999.csv", result.getOrNull())
        coVerify(exactly = 1) { repository.exportStatsToCsv(ip) }
    }

    @Test
    fun `invoke with valid ip delegates to repository and returns success`() = runTest {
        val ip = "192.168.4.1"
        coEvery { repository.exportStatsToCsv(ip) } returns Result.success("/tmp/stats.csv")

        val result = useCase(ip)

        assertTrue(result.isSuccess)
        assertEquals("/tmp/stats.csv", result.getOrNull())
        coVerify(exactly = 1) { repository.exportStatsToCsv(ip) }
    }
}

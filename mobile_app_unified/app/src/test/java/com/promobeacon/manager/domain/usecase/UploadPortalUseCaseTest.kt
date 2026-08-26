package com.promobeacon.manager.domain.usecase

import com.promobeacon.manager.domain.repository.DeviceRepository
import com.promobeacon.manager.domain.repository.UploadProgress
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class UploadPortalUseCaseTest {

    private lateinit var repository: DeviceRepository
    private lateinit var useCase: UploadPortalUseCase

    @Before
    fun setup() {
        repository = mockk(relaxed = true)
        useCase = UploadPortalUseCase(repository)
    }

    @Test
    fun `invoke with blank html returns Error and never calls repository`() = runTest {
        val result = useCase("   ").first()

        assertTrue(result is UploadProgress.Error)
        assertEquals("HTML content cannot be empty", (result as UploadProgress.Error).message)
        coVerify(exactly = 0) { repository.uploadPortalContent(any()) }
    }

    @Test
    fun `invoke with 33KB html returns Error and never calls repository`() = runTest {
        val largeHtml = "A".repeat(33 * 1024)

        val result = useCase(largeHtml).first()

        assertTrue(result is UploadProgress.Error)
        assertEquals("HTML content too large, max 32KB supported", (result as UploadProgress.Error).message)
        coVerify(exactly = 0) { repository.uploadPortalContent(any()) }
    }

    @Test
    fun `invoke with valid html delegates to repository`() = runTest {
        val validHtml = "<html>test</html>"
        coEvery { repository.uploadPortalContent(validHtml) } returns flowOf(UploadProgress.Completed(10))

        val result = useCase(validHtml).first()

        assertTrue(result is UploadProgress.Completed)
        assertEquals(10, (result as UploadProgress.Completed).totalBytes)
        coVerify(exactly = 1) { repository.uploadPortalContent(validHtml) }
    }
}

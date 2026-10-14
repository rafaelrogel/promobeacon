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

    @Test
    fun `invoke with external image returns Error and never calls repository`() = runTest {
        val htmlWithExtImg = """<html><body><img src="https://example.com/logo.png"></body></html>"""

        val result = useCase(htmlWithExtImg).first()

        assertTrue(result is UploadProgress.Error)
        val errorMsg = (result as UploadProgress.Error).message
        assertTrue(errorMsg.contains("external resource"))
        assertTrue(errorMsg.contains("https://example.com/logo.png"))
        coVerify(exactly = 0) { repository.uploadPortalContent(any()) }
    }

    @Test
    fun `invoke with external stylesheet link returns Error and never calls repository`() = runTest {
        val htmlWithExtCss = """<html><head><link rel="stylesheet" href="https://fonts.com/roboto.css"></head></html>"""

        val result = useCase(htmlWithExtCss).first()

        assertTrue(result is UploadProgress.Error)
        val errorMsg = (result as UploadProgress.Error).message
        assertTrue(errorMsg.contains("external resource"))
        assertTrue(errorMsg.contains("https://fonts.com/roboto.css"))
        coVerify(exactly = 0) { repository.uploadPortalContent(any()) }
    }

    @Test
    fun `invoke with external script returns Error and never calls repository`() = runTest {
        val htmlWithExtScript = """<html><head><script src="http://cdn.com/app.js"></script></head></html>"""

        val result = useCase(htmlWithExtScript).first()

        assertTrue(result is UploadProgress.Error)
        val errorMsg = (result as UploadProgress.Error).message
        assertTrue(errorMsg.contains("external resource"))
        assertTrue(errorMsg.contains("http://cdn.com/app.js"))
        coVerify(exactly = 0) { repository.uploadPortalContent(any()) }
    }

    @Test
    fun `invoke with external css import returns Error and never calls repository`() = runTest {
        val htmlWithImport = """<html><head><style>@import url("https://fonts.com/css");</style></head></html>"""

        val result = useCase(htmlWithImport).first()

        assertTrue(result is UploadProgress.Error)
        val errorMsg = (result as UploadProgress.Error).message
        assertTrue(errorMsg.contains("external resource"))
        coVerify(exactly = 0) { repository.uploadPortalContent(any()) }
    }

    @Test
    fun `invoke with valid offline base64 image and svg succeeds and delegates to repository`() = runTest {
        val offlineHtml = """
            <html>
                <body>
                    <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==">
                    <svg width="10" height="10"><circle cx="5" cy="5" r="5"/></svg>
                </body>
            </html>
        """.trimIndent()
        coEvery { repository.uploadPortalContent(offlineHtml) } returns flowOf(UploadProgress.Completed(offlineHtml.length))

        val result = useCase(offlineHtml).first()

        assertTrue(result is UploadProgress.Completed)
        assertEquals(offlineHtml.length, (result as UploadProgress.Completed).totalBytes)
        coVerify(exactly = 1) { repository.uploadPortalContent(offlineHtml) }
    }

    @Test
    fun `invoke with allowExternalResources true allows external url and delegates to repository`() = runTest {
        val htmlWithExtImg = """<html><body><img src="https://example.com/logo.png"></body></html>"""
        coEvery { repository.uploadPortalContent(htmlWithExtImg) } returns flowOf(UploadProgress.Completed(100))

        val result = useCase(htmlWithExtImg, allowExternalResources = true).first()

        assertTrue(result is UploadProgress.Completed)
        assertEquals(100, (result as UploadProgress.Completed).totalBytes)
        coVerify(exactly = 1) { repository.uploadPortalContent(htmlWithExtImg) }
    }
}

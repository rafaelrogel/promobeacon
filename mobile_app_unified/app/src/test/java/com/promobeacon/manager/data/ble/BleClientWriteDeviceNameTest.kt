package com.promobeacon.manager.data.ble

import android.bluetooth.BluetoothGattCharacteristic
import android.content.Context
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import io.mockk.spyk
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class BleClientWriteDeviceNameTest {

    private lateinit var mockContext: Context
    private lateinit var bleClient: BleClient
    private lateinit var authStateFlow: MutableStateFlow<AuthenticationState>

    @Before
    fun setup() {
        mockContext = mockk(relaxed = true)
        // Use spyk to partially mock BleClient so we can override writeCharacteristic
        bleClient = spyk(BleClient(mockContext))

        // Access the private _authenticationState via reflection
        val stateField = BleClient::class.java.getDeclaredField("_authenticationState")
        stateField.isAccessible = true
        @Suppress("UNCHECKED_CAST")
        authStateFlow = stateField.get(bleClient) as MutableStateFlow<AuthenticationState>
    }

    @Test
    fun testWriteDeviceNameFailsWhenNotAuthenticated() = runTest {
        // Arrange: Start with an unauthenticated state
        authStateFlow.value = AuthenticationState.NOT_AUTHENTICATED

        // Act
        val result = bleClient.writeDeviceName("New Name")

        // Assert: Should return false immediately
        assertFalse("writeDeviceName should fail when not authenticated", result)
        // ensureAuthenticatedForWrite will also transition NOT_AUTHENTICATED to REQUIRED
        assertEquals(
            "Should transition to REQUIRED due to write attempt while unauthenticated",
            AuthenticationState.REQUIRED, 
            bleClient.authenticationState.value
        )
    }

    @Test
    fun testWriteDeviceNameSuccessWhenAuthenticated() = runTest {
        // Arrange: Start authenticated
        authStateFlow.value = AuthenticationState.AUTHENTICATED
        val mockChar = mockk<BluetoothGattCharacteristic>(relaxed = true)
        bleClient.deviceNameChar = mockChar
        
        // Mock writeCharacteristic to return true
        coEvery { bleClient.writeCharacteristic(mockChar, any()) } returns true

        // Act
        val result = bleClient.writeDeviceName("New Name")

        // Assert
        assertTrue("writeDeviceName should succeed when authenticated and write succeeds", result)
        assertEquals(
            "State should remain AUTHENTICATED",
            AuthenticationState.AUTHENTICATED,
            bleClient.authenticationState.value
        )
        // Verify characteristic was written with the correct bytes
        coVerify { bleClient.writeCharacteristic(mockChar, "New Name".toByteArray(Charsets.UTF_8)) }
    }

    @Test
    fun testWriteDeviceNameFailsWhenWriteCharacteristicFails() = runTest {
        // Arrange: Start authenticated
        authStateFlow.value = AuthenticationState.AUTHENTICATED
        val mockChar = mockk<BluetoothGattCharacteristic>(relaxed = true)
        bleClient.deviceNameChar = mockChar
        
        // Mock writeCharacteristic to return false but state stays AUTHENTICATED
        coEvery { bleClient.writeCharacteristic(mockChar, any()) } returns false

        // Act
        val result = bleClient.writeDeviceName("New Name")

        // Assert
        assertFalse("writeDeviceName should fail when underlying write fails", result)
        assertEquals(
            "State should remain AUTHENTICATED if failure was not auth related",
            AuthenticationState.AUTHENTICATED,
            bleClient.authenticationState.value
        )
    }

    @Test
    fun testWriteDeviceNameHandlesAuthRejectionDuringWrite() = runTest {
        // Arrange: Start authenticated
        authStateFlow.value = AuthenticationState.AUTHENTICATED
        val mockChar = mockk<BluetoothGattCharacteristic>(relaxed = true)
        bleClient.deviceNameChar = mockChar
        
        // Mock writeCharacteristic to return false AND simulate state change from GATT callback
        coEvery { 
            bleClient.writeCharacteristic(mockChar, any()) 
        } answers {
            // Simulate GATT callback receiving insufficient authentication
            authStateFlow.value = AuthenticationState.NOT_AUTHENTICATED
            false
        }

        // Act
        val result = bleClient.writeDeviceName("New Name")

        // Assert
        assertFalse("writeDeviceName should fail when underlying write fails", result)
        assertEquals(
            "State should transition to REQUIRED after auth rejection during write",
            AuthenticationState.REQUIRED,
            bleClient.authenticationState.value
        )
    }
}

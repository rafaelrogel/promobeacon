package com.promobeacon.manager.data.ble

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

class BleConstantsTest {

    @Test
    fun testBleConstants() {
        assertEquals("12345684-1234-1234-1234-123456789ABC", BleConstants.CHAR_DEVICE_NAME)
        assertEquals("1234567D-1234-1234-1234-123456789ABC", BleConstants.CHAR_PROMO_TEXT)
        assertEquals("12345678-1234-1234-1234-123456789ABC", BleConstants.PROMO_SERVICE_UUID)
    }

    @Test
    fun testRegressionGuardGapUuid() {
        // The app must NOT write device name to the read-only GAP char
        assertNotEquals("00002a00-0000-1000-8000-00805f9b34fb", BleConstants.CHAR_DEVICE_NAME)
    }

    @Test
    fun testUuidConsistency() {
        val deviceNamePrefix = BleConstants.CHAR_DEVICE_NAME.substring(0, 8)
        val promoServicePrefix = BleConstants.PROMO_SERVICE_UUID.substring(0, 8)
        
        assertEquals("12345684", deviceNamePrefix)
        assertEquals("12345678", promoServicePrefix)
    }
}

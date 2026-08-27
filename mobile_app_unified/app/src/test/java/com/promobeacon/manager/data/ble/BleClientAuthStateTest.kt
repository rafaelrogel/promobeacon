package com.promobeacon.manager.data.ble

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class BleClientAuthStateTest {

    @Test
    fun testOnDisconnectResetsAllStatesToNotAuthenticated() {
        for (initialState in AuthenticationState.values()) {
            val nextState = AuthStateReducer.reduce(initialState, AuthEvent.ON_DISCONNECT)
            assertEquals(
                "Disconnect from state $initialState must reset to NOT_AUTHENTICATED",
                AuthenticationState.NOT_AUTHENTICATED,
                nextState
            )
        }
    }

    @Test
    fun testOnConnectStartResetsToNotAuthenticated() {
        for (initialState in AuthenticationState.values()) {
            val nextState = AuthStateReducer.reduce(initialState, AuthEvent.ON_CONNECT_START)
            assertEquals(
                "Connect start from state $initialState must reset to NOT_AUTHENTICATED",
                AuthenticationState.NOT_AUTHENTICATED,
                nextState
            )
        }
    }

    @Test
    fun testWriteRejectedByAuthTransitionsToRequired() {
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
    }

    @Test
    fun testAuthStatusIdleKeepsCurrentState() {
        for (state in AuthenticationState.values()) {
            val nextState = AuthStateReducer.reduce(state, AuthEvent.AUTH_STATUS_IDLE)
            assertEquals(
                "AUTH_STATUS_IDLE should maintain current state $state",
                state,
                nextState
            )
        }
    }

    @Test
    fun testAuthStatusRequiredTransitionsToRequired() {
        val nextState = AuthStateReducer.reduce(AuthenticationState.AUTHENTICATED, AuthEvent.AUTH_STATUS_REQUIRED)
        assertEquals(AuthenticationState.REQUIRED, nextState)
    }

    @Test
    fun testAuthStatusSuccessTransitionsToAuthenticated() {
        val nextState = AuthStateReducer.reduce(AuthenticationState.AUTHENTICATING, AuthEvent.AUTH_STATUS_SUCCESS)
        assertEquals(AuthenticationState.AUTHENTICATED, nextState)
    }

    @Test
    fun testAuthStatusFailedTransitionsToFailed() {
        val nextState = AuthStateReducer.reduce(AuthenticationState.AUTHENTICATING, AuthEvent.AUTH_STATUS_FAILED)
        assertEquals(AuthenticationState.FAILED, nextState)
    }

    @Test
    fun testAuthStatusLockedTransitionsToLocked() {
        val nextState = AuthStateReducer.reduce(AuthenticationState.AUTHENTICATING, AuthEvent.AUTH_STATUS_LOCKED)
        assertEquals(AuthenticationState.LOCKED, nextState)
    }

    @Test
    fun testFromFirmwareStatusByteMapping() {
        assertEquals(AuthEvent.AUTH_STATUS_IDLE, AuthStateReducer.fromFirmwareStatus(BleConstants.AUTH_STATUS_IDLE.toByte()))
        assertEquals(AuthEvent.AUTH_STATUS_REQUIRED, AuthStateReducer.fromFirmwareStatus(BleConstants.AUTH_STATUS_REQUIRED.toByte()))
        assertEquals(AuthEvent.AUTH_STATUS_SUCCESS, AuthStateReducer.fromFirmwareStatus(BleConstants.AUTH_STATUS_SUCCESS.toByte()))
        assertEquals(AuthEvent.AUTH_STATUS_FAILED, AuthStateReducer.fromFirmwareStatus(BleConstants.AUTH_STATUS_FAILED.toByte()))
        assertEquals(AuthEvent.AUTH_STATUS_LOCKED, AuthStateReducer.fromFirmwareStatus(BleConstants.AUTH_STATUS_LOCKED.toByte()))
        assertNull(AuthStateReducer.fromFirmwareStatus(0x99.toByte()))
    }
}

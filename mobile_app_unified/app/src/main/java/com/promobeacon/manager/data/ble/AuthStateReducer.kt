package com.promobeacon.manager.data.ble

/**
 * Events that trigger authentication state changes.
 */
enum class AuthEvent {
    ON_DISCONNECT,
    ON_CONNECT_START,
    AUTH_STATUS_IDLE,
    AUTH_STATUS_REQUIRED,
    AUTH_STATUS_SUCCESS,
    AUTH_STATUS_FAILED,
    AUTH_STATUS_LOCKED,
    WRITE_REJECTED_BY_AUTH
}

/**
 * Pure state reducer to manage AuthenticationState transitions deterministically.
 */
object AuthStateReducer {
    fun reduce(currentState: AuthenticationState, event: AuthEvent): AuthenticationState {
        return when (event) {
            AuthEvent.ON_DISCONNECT -> AuthenticationState.NOT_AUTHENTICATED
            AuthEvent.ON_CONNECT_START -> AuthenticationState.NOT_AUTHENTICATED
            AuthEvent.WRITE_REJECTED_BY_AUTH -> AuthenticationState.REQUIRED
            AuthEvent.AUTH_STATUS_IDLE -> currentState
            AuthEvent.AUTH_STATUS_REQUIRED -> AuthenticationState.REQUIRED
            AuthEvent.AUTH_STATUS_SUCCESS -> AuthenticationState.AUTHENTICATED
            AuthEvent.AUTH_STATUS_FAILED -> AuthenticationState.FAILED
            AuthEvent.AUTH_STATUS_LOCKED -> AuthenticationState.LOCKED
        }
    }

    fun fromFirmwareStatus(statusByte: Byte): AuthEvent? {
        val statusInt = statusByte.toInt() and 0xFF
        return when (statusInt) {
            BleConstants.AUTH_STATUS_IDLE -> AuthEvent.AUTH_STATUS_IDLE
            BleConstants.AUTH_STATUS_REQUIRED -> AuthEvent.AUTH_STATUS_REQUIRED
            BleConstants.AUTH_STATUS_SUCCESS -> AuthEvent.AUTH_STATUS_SUCCESS
            BleConstants.AUTH_STATUS_FAILED -> AuthEvent.AUTH_STATUS_FAILED
            BleConstants.AUTH_STATUS_LOCKED -> AuthEvent.AUTH_STATUS_LOCKED
            else -> null
        }
    }
}

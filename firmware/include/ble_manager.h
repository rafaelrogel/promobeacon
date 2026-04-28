/**
 * BLE Manager Header - Unified GATT Service
 * 
 * Provides unified BLE GATT service for both G and E modes.
 * Supports mode switching, configuration, and status monitoring.
 * 
 * Author: MiniMax Agent
 * Version: 3.0.0
 */

#ifndef BLE_MANAGER_H
#define BLE_MANAGER_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * GATT SERVICE UUIDS
 * ============================================================================ */

/* 128-bit Service UUID for PromoBeacon Unified Service */
#define PROMO_SERVICE_UUID         "12345678-1234-1234-1234-123456789ABC"

/* 128-bit Characteristic UUIDs */
#define CHAR_MODE_CONTROL          "12345679-1234-1234-1234-123456789ABC"  /* R/W */
#define CHAR_MESSAGE               "1234567A-1234-1234-1234-123456789ABC"  /* R/W */
#define CHAR_CONFIG                "1234567B-1234-1234-1234-123456789ABC"  /* W */
#define CHAR_STATUS                "1234567C-1234-1234-1234-123456789ABC"  /* R/N */
#define CHAR_PROMO_TEXT            "1234567D-1234-1234-1234-123456789ABC"  /* R/W */
#define CHAR_STATS                 "1234567E-1234-1234-1234-123456789ABC"  /* R/N - Aggregated stats */
#define CHAR_SESSIONS              "1234567F-1234-1234-1234-123456789ABC"  /* R - Session history */
#define CHAR_SESSION_CTRL          "12345680-1234-1234-1234-123456789ABC"  /* W - Session control commands */

/* Client Characteristic Configuration Descriptor UUID */
#define CLIENT_CONFIG_DESC_UUID    "00002902-0000-1000-8000-00805f9b34fb"

/* ============================================================================
 * COMMAND VALUES
 * ============================================================================ */

#define CMD_MODE_G                 0x00    /* Switch to G Mode */
#define CMD_REBOOT                 0x02    /* Reboot device */
#define CMD_RESET_DEFAULTS         0x03    /* Reset to defaults */

/* Config command subtypes */
#define CONFIG_SET_BEACON_PARAMS   0x01
#define CONFIG_START_OTA           0x03    /* Start OTA update mode */
#define CONFIG_GET_OTA_STATUS      0x04    /* Get OTA status */

/* Session control command subtypes */
#define SESSION_CMD_CLEAR_ALL      0x01    /* Clear all session history */
#define SESSION_CMD_GET_COUNT      0x02    /* Get session count */
#define SESSION_CMD_GET_STATS      0x03    /* Get aggregated stats */
#define SESSION_CMD_GET_LATEST     0x04    /* Get latest N sessions */

/* Portal content upload commands (via session control characteristic) */
#define BLE_PORTAL_CMD_START       0x10    /* Start portal upload */
#define BLE_PORTAL_CMD_DATA        0x11    /* Portal data chunk */
#define BLE_PORTAL_CMD_END         0x12    /* End portal upload */
#define BLE_PORTAL_CMD_ABORT       0x13    /* Abort portal upload */
#define BLE_PORTAL_CMD_STATUS      0x14    /* Request portal status */
#define BLE_PORTAL_CMD_RESET       0x15    /* Reset to default content */

/* Portal content characteristics */
#define CHAR_PORTAL_DATA           "12345681-1234-1234-1234-123456789ABC"  /* W - Portal data chunks */
#define CHAR_PORTAL_CTRL           "12345682-1234-1234-1234-123456789ABC"  /* R/W/N - Portal control & status */

/* Authentication characteristic */
#define CHAR_AUTH                   "12345683-1234-1234-1234-123456789ABC"  /* W - Password authentication */

/* Authentication response characteristic */
#define CHAR_AUTH_STATUS            "12345685-1234-1234-1234-123456789ABC"  /* R/N - Authentication status */

/* Device name characteristic */
#define CHAR_DEVICE_NAME            "12345684-1234-1234-1234-123456789ABC"  /* R/W - Device name */

/* Authentication status values */
#define AUTH_STATUS_IDLE            0x00
#define AUTH_STATUS_REQUIRED        0x01
#define AUTH_STATUS_SUCCESS         0x02
#define AUTH_STATUS_FAILED          0x03
#define AUTH_STATUS_LOCKED          0x04

/* Authentication commands */
#define AUTH_CMD_LOGIN              0x01    /* Submit authentication token */
#define AUTH_CMD_LOGOUT             0x02    /* Clear authentication */
#define AUTH_CMD_SET_TOKEN          0x03    /* Set new auth token (requires auth) */
#define AUTH_CMD_GET_TOKEN_HINT     0x04    /* Get token hint (first 4 chars) */

/* ============================================================================
 * SIZE CONSTANTS
 * ============================================================================ */

#define MAX_MESSAGE_LENGTH         20
#define MAX_PROMO_TEXT_LENGTH      32
#define MAX_SSID_LENGTH            32
#define MAX_PASSWORD_LENGTH        64
#define MAX_DEVICE_NAME_LENGTH     32
#define MIN_ADMIN_PASSWORD_LENGTH  4
#define MAX_STATUS_LENGTH          32
#define MAX_DEVICE_ID_LENGTH       16

/* ============================================================================
 * MODE ENUMERATION
 * ============================================================================ */

/**
 * @brief Device mode enumeration
 */
typedef enum {
    MODE_G = 0,    /* WiFi AP + Captive Portal */
    MODE_UNKNOWN = 255
} DeviceMode;

/**
 * @brief Connection state enumeration
 */
typedef enum {
    CONN_STATE_DISCONNECTED = 0,
    CONN_STATE_CONNECTING = 1,
    CONN_STATE_CONNECTED = 2,
    CONN_STATE_DISCONNECTING = 3
} ConnectionState;

/* ============================================================================
 * STATUS STRUCTURE
 * ============================================================================ */

/**
 * @brief Device status structure
 */
typedef struct {
    DeviceMode mode;              /* Current mode (G or E) */
    bool is_advertising;          /* Advertising status */
    bool is_connected;            /* BLE connection status */
    uint32_t uptime_ms;           /* Uptime in milliseconds */
    int8_t rssi;                  /* Last RSSI in dBm */
    uint8_t client_count;         /* Number of connected clients */
    uint8_t wifi_clients;         /* WiFi clients (G mode only) */
    char message[MAX_MESSAGE_LENGTH + 1];      /* Current message */
    char promo_text[MAX_PROMO_TEXT_LENGTH + 1]; /* Promo/SSID text */
    uint8_t ota_progress;         /* OTA update progress (0-100) */
    char firmware_version[16];    /* Firmware version string */
    char device_id[MAX_DEVICE_ID_LENGTH];      /* Unique device identifier */
} DeviceStatus;

/**
 * @brief Configuration command structure
 */
typedef struct {
    uint8_t command;              /* Command byte */
    uint16_t param1;              /* First parameter (major/beacon ID) */
    uint16_t param2;              /* Second parameter (minor) */
    int8_t param3;                /* Third parameter (TX power) */
    uint8_t flags;                /* Feature flags */
} ConfigCommand;
/**
 * @brief BLE GATT Configuration structure
 */
typedef struct {
    uint8_t dummy; /* Placeholder for future config */
} BleManGattConfig;

/**
 * @brief Mode change callback type
 */
typedef void (*mode_change_callback_t)(DeviceMode new_mode, DeviceMode old_mode);

/**
 * @brief Status update callback type
 */
typedef void (*status_update_callback_t)(const DeviceStatus* status);

/* ============================================================================
 * FUNCTION PROTOTYPES - CORE API
 * ============================================================================ */

/**
 * @brief Initialize BLE manager with unified GATT service
 * 
 * Initializes BLE stack, registers GATT service with all characteristics,
 * and starts advertising. Must be called before any other BLE operations.
 * 
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t init_ble_manager(void);

/**
 * @brief Deinitialize BLE manager
 * 
 * Stops advertising, disconnects clients, and releases BLE resources.
 */
void deinit_ble_manager(void);

/**
 * @brief Get current device mode
 * 
 * @return Current device mode (MODE_G only)
 */
DeviceMode get_device_mode(void);

/**
 * @brief Check if BLE is connected
 * 
 * @return true if at least one BLE client is connected
 */
bool is_ble_connected(void);

/**
 * @brief Get connection state
 * 
 * @return Current connection state
 */
ConnectionState get_connection_state(void);

/**
 * @brief Get connected client count
 * 
 * @return Number of connected BLE clients
 */
uint8_t get_ble_client_count(void);

/* ============================================================================
 * FUNCTION PROTOTYPES - CONFIGURATION
 * ============================================================================ */

/**
 * @brief Set broadcast message
 * 
 * Sets the message for the current mode.
 * G Mode: Landing page promo text
 * E Mode: Broadcast message
 * 
 * @param message Message string (max MAX_MESSAGE_LENGTH chars)
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_set_message(const char* message);

/**
 * @brief Get current message
 * 
 * @param buffer Buffer to store message
 * @param buffer_size Size of buffer
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_get_message(char* buffer, size_t buffer_size);

/**
 * @brief Set promo text / SSID
 * 
 * G Mode: WiFi SSID
 * E Mode: Device advertising name
 * 
 * @param text Text string (max MAX_PROMO_TEXT_LENGTH chars)
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_set_promo_text(const char* text);

/**
 * @brief Get promo text / SSID
 * 
 * @param buffer Buffer to store text
 * @param buffer_size Size of buffer
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_get_promo_text(char* buffer, size_t buffer_size);

/**
 * @brief Configure beacon parameters (E Mode)
 * 
 * @param major Major version number (1-65535)
 * @param minor Minor version number (1-65535)
 * @param tx_power TX power in dBm (-40 to +3)
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_set_beacon_params(uint16_t major, uint16_t minor, int8_t tx_power);

/**
 * @brief Start OTA update mode
 *
 * Prepares the device to receive firmware updates via the web interface.
 * After calling this, the device will be ready to receive firmware binary
 * via POST to /update endpoint.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_start_ota_update(void);

/**
 * @brief Get OTA status
 *
 * Gets the current OTA update status including progress percentage.
 *
 * @param progress Pointer to store OTA progress (0-100)
 * @param status_text Pointer to store status string
 * @param text_size Size of status_text buffer
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_get_ota_status(uint8_t* progress, char* status_text, size_t text_size);

/* ============================================================================
 * FUNCTION PROTOTYPES - STATUS & CALLBACKS
 * ============================================================================ */

/**
 * @brief Update status characteristic
 * 
 * Updates the status characteristic with current device state
 * and sends notifications to subscribed clients.
 * 
 * @param status Pointer to status structure
 */
void ble_update_status(const DeviceStatus* status);

/**
 * @brief Register mode change callback
 * 
 * Registers a callback to be called when device mode changes.
 * 
 * @param callback Callback function pointer
 */
void ble_register_mode_change_callback(mode_change_callback_t callback);

/**
 * @brief Register status update callback
 * 
 * Registers a callback to be called when status should be updated.
 * 
 * @param callback Callback function pointer
 */
void ble_register_status_callback(status_update_callback_t callback);

/**
 * @brief Get current device status
 * 
 * Fills the status structure with current device state.
 * 
 * @param status Pointer to status structure to fill
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_get_status(DeviceStatus* status);

/**
 * @brief Notify connected clients
 * 
 * Sends status notification to all subscribed clients.
 */
void ble_notify_clients(void);

/* ============================================================================
 * FUNCTION PROTOTYPES - UTILITY
 * ============================================================================ */

/**
 * @brief Update BLE advertising name
 * 
 * Updates the device name used in BLE advertisements.
 * 
 * @param name New advertising name (max 29 characters)
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t update_ble_advertising_name(const char* name);

/**
 * @brief Check if device is in G mode
 * 
 * @return true if device is in G mode
 */
bool is_g_mode_active(void);

/**
 * @brief Reset to default configuration
 * 
 * Resets all configuration to factory defaults.
 * 
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_reset_defaults(void);

/**
 * @brief Get RSSI of connected client
 * 
 * @param rssi Pointer to store RSSI value
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_get_rssi(int8_t* rssi);

/**
 * @brief Get client session statistics
 *
 * Returns aggregated statistics about client connections and sessions.
 *
 * @param stats_buffer Buffer to store statistics string
 * @param buffer_size Size of buffer
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_get_session_stats(char* stats_buffer, size_t buffer_size);

/**
 * @brief Get session data for BLE transfer
 *
 * Serializes session history data for BLE GATT transfer.
 *
 * @param buffer Output buffer for serialized data
 * @param buffer_size Size of output buffer
 * @param start_index Starting session index
 * @param max_entries Maximum entries to include
 * @return Number of bytes written
 */
uint16_t ble_get_session_data(uint8_t* buffer, size_t buffer_size, uint16_t start_index, uint8_t max_entries);

/**
 * @brief Get total session history size
 *
 * Returns the total size of all session history data.
 *
 * @return Total data size in bytes
 */
uint32_t ble_get_session_history_size(void);

/**
 * @brief Clear all session history
 *
 * Erases all stored session data and resets statistics.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_clear_session_history(void);

/* ============================================================================
 * FUNCTION PROTOTYPES - MAC CONNECTION COUNTS
 * ============================================================================ */

/**
 * @brief Get MAC connection counts
 *
 * Returns connection count data for all tracked MAC addresses.
 * Data is serialized as: MAC(6 bytes)|count(4 bytes)|MAC(6 bytes)|count(4 bytes)...
 *
 * @param buffer Output buffer for serialized data
 * @param buffer_size Size of output buffer
 * @param start_index Starting MAC index
 * @param max_entries Maximum entries to include
 * @return Number of bytes written
 */
uint16_t ble_get_mac_connection_counts(uint8_t* buffer, size_t buffer_size, uint16_t start_index, uint8_t max_entries);

/**
 * @brief Get total MAC count table size
 *
 * Returns the total size of MAC connection count data.
 *
 * @return Total data size in bytes
 */
uint32_t ble_get_mac_count_data_size(void);

/**
 * @brief Get connection count for a specific MAC
 *
 * Returns the connection count for a given MAC address.
 *
 * @param mac Client MAC address (6 bytes)
 * @return Connection count (0 if MAC not found)
 */
uint32_t ble_get_mac_count(const uint8_t* mac);

/**
 * @brief Get total connected time for a specific MAC
 *
 * Returns the total seconds this MAC has been connected across all sessions.
 *
 * @param mac Client MAC address (6 bytes)
 * @return Total connected seconds (0 if MAC not found)
 */
uint32_t ble_get_mac_total_time(const uint8_t* mac);

/**
 * @brief Get MAC count table summary
 *
 * Returns a summary string of the MAC count table.
 * Format: "TotalMACs:XXX,TotalConn:YYY"
 *
 * @param buffer Output buffer
 * @param buffer_size Size of buffer
 * @return ESP_OK on success
 */
esp_err_t ble_get_mac_count_summary(char* buffer, size_t buffer_size);

/* ============================================================================
 * FUNCTION PROTOTYPES - PORTAL CONTENT MANAGEMENT
 * ============================================================================ */

/**
 * @brief Set device name for BLE advertising
 *
 * Sets the custom device name shown in BLE advertisements.
 *
 * @param name New device name (max MAX_DEVICE_NAME_LENGTH chars)
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_set_device_name(const char* name);

/**
 * @brief Get current device name
 *
 * @param buffer Buffer to store device name
 * @param buffer_size Size of buffer
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_get_device_name(char* buffer, size_t buffer_size);

/**
 * @brief Set admin password for authentication
 *
 * Sets the password required for protected write operations.
 * Password must be at least MIN_ADMIN_PASSWORD_LENGTH characters.
 *
 * @param password New password (NULL or empty to disable password protection)
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_set_admin_password(const char* password);

/**
 * @brief Check if authentication is required
 *
 * @return true if password protection is enabled
 */
bool ble_is_authentication_required(void);

/**
 * @brief Check if current session is authenticated
 *
 * @return true if the current BLE connection is authenticated
 */
bool ble_is_authenticated(void);

/**
 * @brief Submit password for authentication
 *
 * Attempts to authenticate the current session with the given password.
 *
 * @param password Password to verify
 * @return ESP_OK if authentication successful, ESP_ERR_INVALID_PASSWORD otherwise
 */
esp_err_t ble_authenticate(const char* password);

/**
 * @brief Clear authentication state
 *
 * Resets authentication state for current connection.
 */
void ble_clear_authentication(void);

/**
 * @brief Start portal content transfer
 *
 * Called when app sends CMD_START to begin uploading custom HTML.
 *
 * @param total_size Expected total content size
 * @param crc32 Expected CRC32 of complete content
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_portal_start_transfer(uint32_t total_size, uint32_t crc32);

/**
 * @brief Process portal data chunk
 *
 * Called when app sends data chunks via PORTAL_DATA characteristic.
 *
 * @param seq_num Sequence number (big-endian, 2 bytes)
 * @param data Pointer to chunk data
 * @param data_len Length of chunk data
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_portal_process_chunk(uint16_t seq_num, const uint8_t* data, uint16_t data_len);

/**
 * @brief Complete portal content transfer
 *
 * Called when app sends CMD_END to finalize transfer.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_portal_complete_transfer(void);

/**
 * @brief Abort portal content transfer
 *
 * Cancels current transfer and frees resources.
 */
void ble_portal_abort_transfer(void);

/**
 * @brief Get portal transfer status
 *
 * Returns current transfer status for app polling.
 *
 * @param status Pointer to store status byte
 * @param progress Pointer to store progress (0-100)
 * @return ESP_OK on success
 */
esp_err_t ble_portal_get_status(uint8_t* status, uint8_t* progress);

/**
 * @brief Reset portal to default content
 *
 * Removes custom content and reverts to built-in default.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_portal_reset_to_default(void);

/**
 * @brief Notify portal status to connected clients
 *
 * Sends current portal status notification to subscribed clients.
 */
void ble_portal_notify_status(void);

/* ============================================================================
 * FUNCTION PROTOTYPES - BLE SECURITY
 * ============================================================================ */

/**
 * @brief Enable BLE security (passkey pairing)
 *
 * Configures BLE stack to require authentication for connections.
 * Uses passkey entry method for pairing.
 *
 * @param passkey Pointer to 6-digit passkey string (NULL for random generation)
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_enable_security(const char* passkey);

/**
 * @brief Disable BLE security
 *
 * Removes security requirements for BLE connections.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_disable_security(void);

/**
 * @brief Check if BLE security is enabled
 *
 * @return true if security is enabled
 */
bool ble_is_security_enabled(void);

/**
 * @brief Get current passkey for pairing
 *
 * Returns the active passkey for BLE pairing.
 *
 * @param buffer Buffer to store passkey (6 characters + null)
 * @param buffer_size Size of buffer
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_get_passkey(char* buffer, size_t buffer_size);

/**
 * @brief Generate a new random passkey
 *
 * Creates a new 6-digit random passkey for BLE pairing.
 *
 * @param buffer Buffer to store passkey (6 characters + null)
 * @param buffer_size Size of buffer
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_generate_passkey(char* buffer, size_t buffer_size);

/**
 * @brief Set a specific passkey for pairing
 *
 * Configures BLE to use a specific passkey for pairing.
 *
 * @param passkey 6-digit numeric passkey string
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_set_passkey(const char* passkey);

/**
 * @brief Check if device is bonded with a peer
 *
 * @return true if at least one bonded device exists
 */
bool ble_is_bonded(void);

/**
 * @brief Remove all bonded devices
 *
 * Clears all bonding information from secure storage.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_remove_bonding(void);

/**
 * @brief Authenticate using the auth token
 *
 * Submits the authentication token for verification.
 *
 * @param token 32-character hex auth token
 * @return ESP_OK if authentication successful, ESP_ERR_INVALID_ARG or ESP_ERR_INVALID_PASSWORD otherwise
 */
esp_err_t ble_authenticate_with_token(const char* token);

/**
 * @brief Get authentication status
 *
 * Returns current authentication state.
 *
 * @param status Pointer to store authentication status byte
 * @return ESP_OK on success
 */
esp_err_t ble_get_auth_status(uint8_t* status);

/**
 * @brief Get auth token hint (first 4 characters)
 *
 * Returns a hint to help user identify which token to use.
 *
 * @param buffer Buffer to store hint (4 characters + null)
 * @param buffer_size Size of buffer
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ble_get_token_hint(char* buffer, size_t buffer_size);

/**
 * @brief Check if client is authenticated
 *
 * @return true if the current BLE client has successfully authenticated
 */
bool ble_is_client_authenticated(void);

#ifdef __cplusplus
}
#endif

#endif /* BLE_MANAGER_H */

/**
 * Configuration Manager Header
 * 
 * Defines the interface for persistent configuration storage.
 * Manages NVS storage for promotion text, portal HTML,
 * WiFi password, and other settings.
 */

#ifndef CONFIG_MANAGER_H
#define CONFIG_MANAGER_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/* NVS namespace and keys */
#define CONFIG_NAMESPACE          "promobeacon"
#define KEY_PROMO_TEXT            "promo_text"
#define KEY_SSID                  "ssid"
#define KEY_PORTAL_HTML           "portal_html"
#define KEY_WIFI_PASSWORD         "wifi_pass"
#define KEY_BATTERY_CAL           "batt_cal"
#define KEY_DEVICE_NAME           "device_name"
#define KEY_ADMIN_PASSWORD        "admin_pass"
#define KEY_IS_CONFIGURED         "is_configured"
#define KEY_AUTH_TOKEN            "auth_token"

/* Configuration limits */
#define MAX_PROMO_TEXT_LENGTH     32
#define MAX_SSID_LENGTH           32
#define MAX_PORTAL_HTML_SIZE      8192
#define MAX_PASSWORD_LENGTH       64
#define MAX_DEVICE_NAME_LENGTH    32
#define MIN_ADMIN_PASSWORD_LENGTH 4
#define MAX_DEVICE_ID_LENGTH      16
#define AUTH_TOKEN_LENGTH         16  /* 16 bytes = 32 hex characters */

/* Default values */
#define DEFAULT_PROMO_TEXT        "PROMOBEACON"
#define DEFAULT_DEVICE_NAME       "PROMO-BEACON"
#define DEFAULT_HTML_SIZE         0  /* Use built-in default */

/**
 * @brief Configuration structure
 */
typedef struct {
    char promo_text[MAX_PROMO_TEXT_LENGTH + 1];
    bool wifi_encrypted;
    char wifi_password[MAX_PASSWORD_LENGTH + 1];
    char device_name[MAX_DEVICE_NAME_LENGTH + 1];
    char admin_password[MAX_PASSWORD_LENGTH + 1];
} DeviceConfig;

/**
 * @brief Initialize configuration manager
 * 
 * Loads configuration from NVS or creates defaults if not present.
 * 
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t init_config_manager(void);

/**
 * @brief Deinitialize configuration manager
 * 
 * Flushes any pending writes and releases resources.
 */
void deinit_config_manager(void);

/**
 * @brief Get current configuration
 * 
 * @return Pointer to current configuration structure
 */
const DeviceConfig* get_config(void);

/**
 * @brief Save promotion text
 * 
 * Stores the promotion text in persistent storage.
 * 
 * @param promo_text New promotion text
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t save_promo_text(const char* promo_text);

/**
 * @brief Load promotion text
 * 
 * @param buffer Buffer to receive promotion text
 * @param buffer_size Buffer size
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t load_promo_text(char* buffer, size_t buffer_size);

/**
 * @brief Save SSID
 * 
 * Stores the SSID in persistent storage.
 * 
 * @param ssid New SSID
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t save_ssid(const char* ssid);

/**
 * @brief Load SSID
 * 
 * @param buffer Buffer to receive SSID
 * @param buffer_size Buffer size
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t load_ssid(char* buffer, size_t buffer_size);

/**
 * @brief Save portal HTML content
 * 
 * Stores the portal HTML in persistent storage.
 * 
 * @param html_content HTML content
 * @param length Content length
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t save_portal_html(const char* html_content, size_t length);

/**
 * @brief Load portal HTML content
 * 
 * @param buffer Buffer to receive HTML content
 * @param buffer_size Buffer size
 * @return Actual content length or error code
 */
ssize_t load_portal_html(char* buffer, size_t buffer_size);

/**
 * @brief Save WiFi password
 * 
 * Stores the WiFi password for AP mode.
 * 
 * @param password New password (NULL to disable encryption)
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t save_wifi_password(const char* password);

/**
 * @brief Load WiFi password
 * 
 * @param buffer Buffer to receive password
 * @param buffer_size Buffer size
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t load_wifi_password(char* buffer, size_t buffer_size);

/**
 * @brief Reset configuration to defaults
 * 
 * Clears all stored configuration and restores defaults.
 * 
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t reset_to_defaults(void);

/**
 * @brief Check if configuration is initialized
 *
 * @return true if configuration has been loaded
 */
bool is_config_initialized(void);

/**
 * @brief Check if device has been configured
 *
 * Returns true after initial configuration is complete.
 * Once configured, the web portal shows promotional content only.
 *
 * @return true if device is configured, false for initial setup mode
 */
bool is_device_configured(void);

/**
 * @brief Mark device as configured
 *
 * Called after initial setup is complete.
 * Locks out web portal admin interface.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t set_device_configured(void);

/**
 * @brief Reset configuration state
 *
 * Marks device as unconfigured, allowing web portal setup again.
 * Called during factory reset or when reflash detected.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t reset_configuration_state(void);

/**
 * @brief Save device name
 *
 * Stores the custom device name used for BLE advertising.
 *
 * @param name New device name (NULL to use default)
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t save_device_name(const char* name);

/**
 * @brief Load device name
 *
 * @param buffer Buffer to receive device name
 * @param buffer_size Buffer size
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t load_device_name(char* buffer, size_t buffer_size);

/**
 * @brief Save admin password
 *
 * Stores the admin password for BLE authentication.
 *
 * @param password New admin password (NULL or empty to disable)
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t save_admin_password(const char* password);

/**
 * @brief Load admin password
 *
 * @param buffer Buffer to receive admin password
 * @param buffer_size Buffer size
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t load_admin_password(char* buffer, size_t buffer_size);

/**
 * @brief Check if admin password is set
 *
 * @return true if password protection is enabled
 */
bool is_admin_password_set(void);

/**
 * @brief Verify admin password
 *
 * @param password Password to verify
 * @return true if password matches
 */
bool verify_admin_password(const char* password);

/**
 * @brief Generate a new authentication token
 *
 * Creates a random authentication token for app-to-device authentication.
 * This token is generated during initial setup and must be entered in the app.
 *
 * @param buffer Buffer to receive token (32 hex characters + null terminator)
 * @param buffer_size Buffer size (must be at least AUTH_TOKEN_LENGTH * 2 + 1)
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t generate_auth_token(char* buffer, size_t buffer_size);

/**
 * @brief Save authentication token
 *
 * Stores the authentication token in persistent storage.
 *
 * @param token Token string (32 hex characters)
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t save_auth_token(const char* token);

/**
 * @brief Load authentication token
 *
 * @param buffer Buffer to receive token (32 hex characters + null terminator)
 * @param buffer_size Buffer size
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t load_auth_token(char* buffer, size_t buffer_size);

/**
 * @brief Verify authentication token
 *
 * @param token Token to verify (32 hex characters)
 * @return true if token matches stored token
 */
bool verify_auth_token(const char* token);

/**
 * @brief Check if authentication token is set
 *
 * @return true if token has been generated and stored
 */
bool is_auth_token_set(void);

/**
 * @brief Get unique device identifier
 *
 * Generates a unique device ID based on the ESP32's MAC address.
 * Format: "PB-XXXXXX" where XXXXXX is the last 6 hex digits of MAC.
 * Example: MAC AA:BB:CC:DD:EE:FF -> Device ID "PB-AABBCCDDEEFF"
 *
 * @param buffer Buffer to receive device ID
 * @param buffer_size Buffer size (should be at least MAX_DEVICE_ID_LENGTH)
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t get_device_id(char* buffer, size_t buffer_size);

#ifdef __cplusplus
}
#endif

#endif /* CONFIG_MANAGER_H */

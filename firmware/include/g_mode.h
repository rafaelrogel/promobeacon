/**
 * G Mode (Active Promotion Mode) Header
 *
 * Defines the interface for G mode functionality including:
 * - WiFi Access Point with captive portal
 * - DNS wildcard server
 * - HTTP web server
 * - BLE advertising for device name
 *
 * Designed for unified architecture controlled by ble_manager.
 */

#ifndef G_MODE_H
#define G_MODE_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include "esp_wifi_types.h"
#include "ble_manager.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Initialize G mode
 *
 * Initializes internal G mode resources.
 * Does not start services - call g_mode_start() for that.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t g_mode_init(void);

/**
 * @brief Deinitialize G mode
 *
 * Releases G mode resources.
 * Should be called before g_mode_start() is never needed again.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t g_mode_deinit(void);

/**
 * @brief Start G mode services
 *
 * Starts WiFi AP, DNS server, and HTTP server.
 * BLE advertising is handled by ble_manager.
 *
 * @param config Pointer to BLE manager GATT configuration
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t g_mode_start(const BleManGattConfig* config);

/**
 * @brief Stop G mode services
 *
 * Stops all G mode services (WiFi, DNS, HTTP).
 * BLE continues running for control connectivity.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t g_mode_stop(void);

/**
 * @brief Check if G mode is active
 *
 * @return true if G mode is currently active, false otherwise
 */
bool g_mode_is_active(void);

/**
 * @brief Check if G mode services are running
 *
 * @return true if G mode services are currently running
 */
bool g_mode_is_running(void);

/**
 * @brief Update promotion text (SSID and BLE name)
 *
 * @param promotion_text New promotion text (max 29 characters)
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t g_mode_update_promotion_text(const char* promotion_text);

/**
 * @brief Update WiFi AP SSID
 *
 * Updates the WiFi network name (SSID) without changing the promotion text.
 * The new SSID takes effect immediately.
 *
 * @param new_ssid New SSID (1-32 characters)
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t g_mode_update_ssid(const char* new_ssid);

/**
 * @brief Update portal HTML content
 *
 * @param html_content New HTML content
 * @param length Content length
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t g_mode_update_portal_html(const char* html_content, size_t length);

/**
 * @brief Get current connected client count
 *
 * @return Number of connected WiFi clients (0-6)
 */
uint8_t g_mode_get_client_count(void);

/**
 * @brief Get portal engagement time
 *
 * @return Average time clients spend on portal (seconds)
 */
uint8_t g_mode_get_portal_engagement_time(void);

/**
 * @brief Initialize G mode (legacy wrapper)
 *
 * For backward compatibility. Calls g_mode_init() and g_mode_start().
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t init_g_mode(void);

/**
 * @brief Cleanup G mode (legacy wrapper)
 *
 * For backward compatibility. Calls g_mode_stop() and g_mode_deinit().
 */
void cleanup_g_mode(void);

/**
 * @brief Check if G mode is active (legacy wrapper)
 *
 * For backward compatibility.
 *
 * @return true if G mode is currently active, false otherwise
 */
bool is_g_mode_active(void);

/**
 * @brief Update promotion text (legacy wrapper)
 *
 * For backward compatibility.
 */
esp_err_t update_promotion_text(const char* promotion_text);

/**
 * @brief Update portal HTML content (legacy wrapper)
 *
 * For backward compatibility.
 */
esp_err_t update_portal_html(const char* html_content, size_t length);

/**
 * @brief Get client count (legacy wrapper)
 *
 * For backward compatibility.
 */
uint8_t get_client_count(void);

/**
 * @brief Get engagement time (legacy wrapper)
 *
 * For backward compatibility.
 */
uint8_t get_portal_engagement_time(void);

#ifdef __cplusplus
}
#endif

#endif /* G_MODE_H */

/**
 * Web Server Header
 * 
 * Defines the interface for HTTP server functionality.
 * Serves the captive portal HTML content and handles
 * form submissions from connected clients.
 */

#ifndef WEB_SERVER_H
#define WEB_SERVER_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/* HTTP server configuration */
#define HTTP_SERVER_PORT          80
#define HTTP_BUFFER_SIZE          1024
#define HTTP_MAX_CONNECTIONS      6
#define HTTP_TIMEOUT_MS           30000
#define HTTP_MAX_URI_LENGTH       128
#define HTTP_MAX_HEADER_LENGTH    256

/* HTTP response codes */
#define HTTP_STATUS_OK            200
#define HTTP_STATUS_FOUND         302
#define HTTP_STATUS_BAD_REQUEST   400
#define HTTP_STATUS_NOT_FOUND     404
#define HTTP_STATUS_INTERNAL_ERROR 500

/* MIME types */
#define MIME_TYPE_HTML            "text/html"
#define MIME_TYPE_CSS             "text/css"
#define MIME_TYPE_JS              "application/javascript"
#define MIME_TYPE_JSON            "application/json"
#define MIME_TYPE_TEXT            "text/plain"

/**
 * @brief Form submission callback type
 */
typedef void (*form_submit_callback_t)(const char* form_data, size_t length);

/**
 * @brief Initialize HTTP server
 * 
 * Starts HTTP server on port 80 to serve captive portal.
 * 
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t init_http_server(void);

/**
 * @brief Stop HTTP server
 * 
 * Stops all HTTP server connections and releases resources.
 */
void stop_http_server(void);

/**
 * @brief Handle HTTP requests
 * 
 * Called from main loop to process pending HTTP requests.
 * Non-blocking, processes all available requests.
 */
void handle_http_requests(void);

/**
 * @brief Set portal HTML content
 * 
 * Updates the HTML content served by the web server.
 * 
 * @param html_content New HTML content
 * @param length Content length
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t set_portal_content(const char* html_content, size_t length);

/**
 * @brief Update portal content with simple text
 *
 * Generates a simple HTML page with the given text and updates the portal.
 *
 * @param text Text to display on the portal page
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t update_portal_content_with_text(const char* text);

/**
 * @brief Get portal content pointer
 * 
 * @return Pointer to current portal HTML content
 */
const char* get_portal_content(void);

/**
 * @brief Get portal content length
 * 
 * @return Current portal HTML content length
 */
size_t get_portal_content_length(void);

/**
 * @brief Register form submission callback
 * 
 * Registers a callback to be called when form data is submitted.
 * 
 * @param callback Callback function pointer
 */
void register_form_callback(form_submit_callback_t callback);

/**
 * @brief Check if HTTP server is active
 * 
 * @return true if server is running
 */
bool is_http_server_active(void);

/**
 * @brief Get active connection count
 * 
 * @return Number of currently active HTTP connections
 */
uint8_t get_http_connection_count(void);

/**
 * @brief Complete OTA firmware update
 *
 * Finalizes the OTA update process after all firmware data has been received.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t complete_ota_update(void);

/**
 * @brief Abort ongoing OTA update
 *
 * Cancels any in-progress OTA firmware update.
 */
void abort_ota_update(void);

/**
 * @brief Check if OTA update is in progress
 *
 * @return true if OTA upload is currently active
 */
bool is_ota_update_active(void);

/**
 * @brief Check if device is in setup mode
 *
 * Returns true when device has not been configured yet.
 * In setup mode, the web portal shows admin configuration page.
 *
 * @return true if device needs initial configuration
 */
bool is_in_setup_mode(void);

/**
 * @brief Mark setup as complete
 *
 * Called when initial configuration is submitted.
 * Locks the device and switches to operational mode.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t complete_setup(void);

#ifdef __cplusplus
}
#endif

#endif /* WEB_SERVER_H */

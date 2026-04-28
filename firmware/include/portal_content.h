/**
 * Portal Content Manager Header
 *
 * Manages custom HTML content storage and retrieval for the captive portal.
 * Supports receiving content via BLE chunked transfer and storing in NVS flash.
 *
 * Features:
 * - BLE chunked transfer protocol for large HTML files
 * - NVS persistent storage (max 16KB recommended)
 * - CRC32 validation for data integrity
 * - Fallback to default content if custom content invalid
 *
 * Author: MiniMax Agent
 * Version: 2.0.0
 */

#ifndef PORTAL_CONTENT_H
#define PORTAL_CONTENT_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * CONFIGURATION CONSTANTS
 * ============================================================================ */

/* NVS namespace and keys */
#define PORTAL_NVS_NAMESPACE         "portal"
#define PORTAL_NVS_CONTENT_KEY       "html_content"
#define PORTAL_NVS_SIZE_KEY          "content_size"
#define PORTAL_NVS_CRC_KEY           "content_crc"

/* Size limits */
#define PORTAL_MAX_SIZE              16384       /* 16KB max HTML size */
#define PORTAL_DEFAULT_SIZE          1024        /* Default buffer size */
#define PORTAL_CHUNK_SIZE            200         /* Max bytes per BLE chunk */

/* Transfer protocol commands */
#define PORTAL_CMD_START             0x01        /* Start transfer */
#define PORTAL_CMD_DATA              0x02        /* Data chunk */
#define PORTAL_CMD_END               0x03        /* End transfer */
#define PORTAL_CMD_ABORT             0x04        /* Abort transfer */
#define PORTAL_CMD_STATUS            0x05        /* Request status */
#define PORTAL_CMD_RESET             0x06        /* Reset to default */

/* Transfer status codes */
#define PORTAL_STATUS_IDLE           0x00
#define PORTAL_STATUS_RECEIVING      0x01
#define PORTAL_STATUS_COMPLETE       0x02
#define PORTAL_STATUS_ERROR          0x03
#define PORTAL_STATUS_VALID          0x04
#define PORTAL_STATUS_INVALID        0x05

/* ============================================================================
 * TRANSFER STATE STRUCTURE
 * ============================================================================ */

/**
 * @brief Portal transfer state
 */
typedef struct {
    uint8_t status;                 /* Current transfer status */
    uint32_t total_size;            /* Expected total size */
    uint32_t bytes_received;        /* Bytes received so far */
    uint16_t expected_seq;          /* Expected sequence number */
    uint32_t crc32;                 /* Expected CRC32 */
    uint8_t* buffer;                /* Transfer buffer (heap allocated) */
    uint32_t buffer_size;           /* Allocated buffer size */
} portal_transfer_state_t;

/**
 * @brief Portal content info
 */
typedef struct {
    uint32_t size;                  /* Content size in bytes */
    uint32_t crc32;                 /* Content CRC32 */
    bool valid;                     /* Is content valid */
    bool exists;                    /* Does custom content exist */
} portal_content_info_t;

/* ============================================================================
 * FUNCTION PROTOTYPES - CORE API
 * ============================================================================ */

/**
 * @brief Initialize portal content manager
 *
 * Loads custom content from NVS if available.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t portal_content_init(void);

/**
 * @brief Deinitialize portal content manager
 *
 * Frees any allocated resources.
 */
void portal_content_deinit(void);

/**
 * @brief Get portal content for serving
 *
 * Returns pointer to current portal HTML content.
 *
 * @return Pointer to HTML content string
 */
const char* portal_content_get(void);

/**
 * @brief Set portal content directly
 *
 * Updates the current portal HTML content and saves to NVS.
 *
 * @param content Pointer to new HTML content
 * @param length Length of content in bytes
 * @return ESP_OK on success
 */
esp_err_t portal_content_set(const char* content, size_t length);

/**
 * @brief Get portal content size
 *
 * Returns the size of current portal content.
 *
 * @return Content size in bytes
 */
size_t portal_content_get_size(void);

/**
 * @brief Check if custom content is loaded
 *
 * @return true if custom content is in use
 */
bool portal_content_is_custom(void);

/* ============================================================================
 * FUNCTION PROTOTYPES - TRANSFER API
 * ============================================================================ */

/**
 * @brief Start portal content transfer
 *
 * Called when app sends CMD_START. Allocates buffer and prepares for reception.
 *
 * @param total_size Expected total content size
 * @param crc32 Expected CRC32 of complete content
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t portal_transfer_start(uint32_t total_size, uint32_t crc32);

/**
 * @brief Process received data chunk
 *
 * Called when app sends data chunks. Validates sequence and stores data.
 *
 * @param seq_num Sequence number (big-endian, 2 bytes)
 * @param data Pointer to chunk data
 * @param data_len Length of chunk data
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t portal_transfer_process_chunk(uint16_t seq_num, const uint8_t* data, uint16_t data_len);

/**
 * @brief Complete portal content transfer
 *
 * Called when app sends CMD_END. Validates CRC and commits to NVS.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t portal_transfer_complete(void);

/**
 * @brief Abort portal content transfer
 *
 * Cancels current transfer and frees allocated resources.
 */
void portal_transfer_abort(void);

/**
 * @brief Get current transfer status
 *
 * Returns current transfer state for reporting to app.
 *
 * @param status Pointer to store status byte
 * @param progress Pointer to store progress (0-100)
 * @return ESP_OK on success
 */
esp_err_t portal_transfer_get_status(uint8_t* status, uint8_t* progress);

/* ============================================================================
 * FUNCTION PROTOTYPES - MANAGEMENT API
 * ============================================================================ */

/**
 * @brief Get portal content information
 *
 * Returns info about current content (size, validity, etc).
 *
 * @param info Pointer to info structure to fill
 * @return ESP_OK on success
 */
esp_err_t portal_get_info(portal_content_info_t* info);

/**
 * @brief Reset to default content
 *
 * Removes custom content from NVS and reverts to built-in default.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t portal_reset_to_default(void);

/**
 * @brief Delete custom content
 *
 * Removes custom content from NVS without reverting to default.
 * After this call, no portal content will be served (caller should handle).
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t portal_delete_custom_content(void);

/**
 * @brief Save content to NVS
 *
 * Commits current content buffer to NVS persistent storage.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t portal_save_to_nvs(void);

/**
 * @brief Load content from NVS
 *
 * Loads custom content from NVS into working buffer.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t portal_load_from_nvs(void);

/**
 * @brief Validate content CRC32
 *
 * Verifies that content in buffer matches expected CRC.
 *
 * @param expected_crc Expected CRC32 value
 * @return true if CRC matches
 */
bool portal_validate_crc(uint32_t expected_crc);

/**
 * @brief Calculate CRC32 of content
 *
 * Computes CRC32 of current content buffer.
 *
 * @return CRC32 value
 */
uint32_t portal_calculate_crc(void);

/* ============================================================================
 * FUNCTION PROTOTYPES - BLE NOTIFICATIONS
 * ============================================================================ */

/**
 * @brief Send transfer status notification
 *
 * Sends current transfer status to connected BLE client.
 *
 * @param status Status byte
 * @param progress Progress percentage (0-100)
 */
void portal_notify_status(uint8_t status, uint8_t progress);

/**
 * @brief Get default HTML with promo text substituted
 *
 * Returns a default HTML page with the given promo text.
 *
 * @param promo_text Promo text to display
 * @return Pointer to default HTML string (static buffer)
 */
const char* portal_get_default_html(const char* promo_text);

/**
 * @brief Get default HTML with promo text and device ID
 *
 * Returns a default HTML page with the given promo text and
 * unique device identifier shown in the corner.
 *
 * @param promo_text Promo text to display
 * @param device_id Unique device identifier (e.g., "PB-AABBCCDDEEFF")
 * @return Pointer to default HTML string (static buffer)
 */
const char* portal_get_default_html_with_id(const char* promo_text, const char* device_id);

#ifdef __cplusplus
}
#endif

#endif /* PORTAL_CONTENT_H */

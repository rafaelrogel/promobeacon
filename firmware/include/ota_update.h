/**
 * OTA Update Header
 *
 * Provides Over-The-Air firmware update functionality
 * with automatic data preservation.
 *
 * Features:
 * - Web-based firmware update portal
 * - BLE-triggered updates
 * - Automatic rollback on failure
 * - Version management
 * - All NVS data preserved automatically
 *
 * Author: MiniMax Agent
 * Version: 2.0.0
 */

#ifndef OTA_UPDATE_H
#define OTA_UPDATE_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Firmware Version - Update this when releasing new versions */
#define FIRMWARE_VERSION             "2.0.0"
#define FIRMWARE_VERSION_MAJOR       2
#define FIRMWARE_VERSION_MINOR       0
#define FIRMWARE_VERSION_PATCH       0

/* OTA Status Codes */
typedef enum {
    OTA_STATUS_IDLE = 0,
    OTA_STATUS_IN_PROGRESS,
    OTA_STATUS_SUCCESS,
    OTA_STATUS_FAILED,
    OTA_STATUS_ROLLBACK,
    OTA_STATUS_CHECKING,
    OTA_STATUS_DOWNLOADING
} ota_status_t;

/* OTA Progress Structure */
typedef struct {
    ota_status_t status;
    uint32_t total_bytes;
    uint32_t written_bytes;
    uint8_t progress_percent;
    char error_message[128];
} ota_progress_t;

/* OTA Configuration */
typedef struct {
    bool auto_check_updates;      /* Check for updates periodically */
    uint32_t check_interval_hours; /* Hours between update checks */
    char update_url[256];          /* URL for automatic updates */
    bool auto_rollback;           /* Automatically rollback on failure */
} ota_config_t;

/**
 * @brief Initialize OTA subsystem
 *
 * Initializes OTA data structures and loads configuration.
 * Must be called early in startup.
 */
void ota_init(void);

/**
 * @brief Get firmware version string
 *
 * @return Pointer to version string (e.g., "1.1.0")
 */
const char* get_firmware_version(void);

/**
 * @brief Get firmware version as integer
 *
 * @return Version encoded as (major << 16 | minor << 8 | patch)
 */
uint32_t get_firmware_version_int(void);

/**
 * @brief Mark current firmware as valid
 *
 * Called after successful boot to prevent automatic rollback.
 * Should be called in main.c after all subsystems are initialized.
 */
void ota_mark_valid(void);

/**
 * @brief Get current OTA progress
 *
 * @param progress Pointer to progress structure to fill
 */
void ota_get_progress(ota_progress_t* progress);

/**
 * @brief Get OTA configuration
 *
 * @return Pointer to current OTA configuration
 */
ota_config_t* ota_get_config(void);

/**
 * @brief Set OTA configuration
 *
 * @param config Pointer to configuration structure
 */
void ota_set_config(ota_config_t* config);

/**
 * @brief Check if OTA update is in progress
 *
 * @return true if OTA is currently running
 */
bool ota_is_in_progress(void);

/**
 * @brief Get last OTA error message
 *
 * @return Pointer to error message string
 */
const char* ota_get_last_error(void);

/**
 * @brief Reset to factory defaults
 *
 * Erases all OTA-related data and marks current firmware as valid.
 * Does NOT affect user configuration (SSID, portal, etc.).
 */
void ota_reset(void);

/**
 * @brief Begin OTA update process
 *
 * Prepares the next OTA partition for writing.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ota_begin(void);

/**
 * @brief Write data to OTA partition
 *
 * @param data Pointer to data buffer
 * @param length Length of data in bytes
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ota_write(const void* data, size_t length);

/**
 * @brief Set total OTA size (optional)
 *
 * Call this before ota_write if total size is known.
 *
 * @param total_bytes Total bytes to be written
 */
void ota_set_total_size(uint32_t total_bytes);

/**
 * @brief End OTA update process
 *
 * Validates the written firmware and sets it as bootable.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t ota_end(void);

/**
 * @brief Abort OTA update
 *
 * Cancels the current OTA update and rolls back if needed.
 */
void ota_abort(void);

/**
 * @brief Get partition info string
 *
 * @param buffer Buffer to store info string
 * @param buffer_size Size of buffer
 */
void ota_get_partition_info(char* buffer, size_t buffer_size);

/**
 * @brief Check if new firmware is available
 *
 * @return true if update is available
 */
bool ota_check_for_updates(void);

/**
 * @brief Get human-readable OTA status for display
 *
 * @param buffer Buffer to store status string
 * @param buffer_size Size of buffer
 */
void ota_get_status_string(char* buffer, size_t buffer_size);

#ifdef __cplusplus
}
#endif

#endif /* OTA_UPDATE_H */

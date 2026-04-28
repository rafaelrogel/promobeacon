#include "ota_update.h"
#include "esp_log.h"
#include "esp_err.h"
#include "esp_ota_ops.h"
#include "esp_partition.h"
#include "esp_image_format.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "string.h"
#include "stdio.h"
#include <inttypes.h>

static const char* TAG = "OTA_UPDATE";

/* NVS Keys for OTA data */
#define OTA_NVS_NAMESPACE           "ota_data"

/* Local static variables */
static ota_progress_t g_progress = {0};
static ota_config_t g_config = {0};
static bool g_ota_initialized = false;
static esp_ota_handle_t g_update_handle = 0;

/* Forward declarations */
static void ota_rollback(void);

/**
 * @brief Initialize OTA subsystem
 */
void ota_init(void)
{
    if (g_ota_initialized) {
        ESP_LOGW(TAG, "OTA already initialized");
        return;
    }

    ESP_LOGI(TAG, "Initializing OTA subsystem");
    ESP_LOGI(TAG, "Firmware Version: %s", FIRMWARE_VERSION);

    /* Load OTA configuration */
    g_config.auto_check_updates = false;
    g_config.check_interval_hours = 24;
    g_config.auto_rollback = true;
    g_config.update_url[0] = '\0';

    /* Reset progress */
    memset(&g_progress, 0, sizeof(g_progress));
    g_progress.status = OTA_STATUS_IDLE;

    g_ota_initialized = true;
    ESP_LOGI(TAG, "OTA subsystem initialized");
}

/**
 * @brief Mark current firmware as valid
 */
void ota_mark_valid(void)
{
    esp_ota_mark_app_valid_cancel_rollback();
}

/**
 * @brief Get current OTA progress
 */
void ota_get_progress(ota_progress_t* progress)
{
    if (progress) {
        *progress = g_progress;
    }
}

/**
 * @brief Get OTA configuration
 */
ota_config_t* ota_get_config(void)
{
    return &g_config;
}

/**
 * @brief Set OTA configuration
 */
void ota_set_config(ota_config_t* config)
{
    if (config) {
        g_config = *config;
        
        nvs_handle_t nvs_handle;
        if (nvs_open(OTA_NVS_NAMESPACE, NVS_READWRITE, &nvs_handle) == ESP_OK) {
            nvs_set_u8(nvs_handle, "auto_check", (uint8_t)g_config.auto_check_updates);
            nvs_set_u32(nvs_handle, "check_interval", g_config.check_interval_hours);
            nvs_commit(nvs_handle);
            nvs_close(nvs_handle);
        }
    }
}

/**
 * @brief Check if OTA update is in progress
 */
bool ota_is_in_progress(void)
{
    return (g_progress.status == OTA_STATUS_IN_PROGRESS || 
            g_progress.status == OTA_STATUS_DOWNLOADING ||
            g_progress.status == OTA_STATUS_CHECKING);
}

/**
 * @brief Get last OTA error message
 */
const char* ota_get_last_error(void)
{
    return g_progress.error_message[0] ? g_progress.error_message : "No error";
}

/**
 * @brief Get partition info string
 */
void ota_get_partition_info(char* buffer, size_t buffer_size)
{
    const esp_partition_t* running = esp_ota_get_running_partition();
    const esp_partition_t* boot = esp_ota_get_boot_partition();
    const esp_partition_t* next = esp_ota_get_next_update_partition(NULL);

    snprintf(buffer, buffer_size,
             "Running: %s (0x%" PRIx32 ")\n"
             "Boot: %s (0x%" PRIx32 ")\n"
             "Next OTA: %s (0x%" PRIx32 ")\n"
             "Version: %s",
             running ? running->label : "N/A",
             (uint32_t)(running ? running->address : 0),
             boot ? boot->label : "N/A",
             (uint32_t)(boot ? boot->address : 0),
             next ? next->label : "N/A",
             (uint32_t)(next ? next->address : 0),
             FIRMWARE_VERSION);
}

/**
 * @brief Reset OTA data
 */
void ota_reset(void)
{
    nvs_handle_t nvs_handle;
    if (nvs_open(OTA_NVS_NAMESPACE, NVS_READWRITE, &nvs_handle) == ESP_OK) {
        nvs_erase_all(nvs_handle);
        nvs_commit(nvs_handle);
        nvs_close(nvs_handle);
    }
    ota_mark_valid();
}

/**
 * @brief Begin OTA update process
 */
esp_err_t ota_begin(void)
{
    const esp_partition_t* update_partition = esp_ota_get_next_update_partition(NULL);
    if (update_partition == NULL) {
        ESP_LOGE(TAG, "No OTA partition found");
        return ESP_ERR_NOT_FOUND;
    }

    ESP_LOGI(TAG, "Starting OTA on partition: %s", update_partition->label);

    esp_err_t err = esp_ota_begin(update_partition, OTA_SIZE_UNKNOWN, &g_update_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_ota_begin failed: %s", esp_err_to_name(err));
        return err;
    }

    g_progress.status = OTA_STATUS_IN_PROGRESS;
    g_progress.written_bytes = 0;
    g_progress.progress_percent = 0;
    
    return ESP_OK;
}

/**
 * @brief Write data to OTA partition
 */
esp_err_t ota_write(const void* data, size_t length)
{
    if (g_update_handle == 0) {
        return ESP_ERR_INVALID_STATE;
    }

    esp_err_t err = esp_ota_write(g_update_handle, data, length);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_ota_write failed: %s", esp_err_to_name(err));
        return err;
    }
    
    g_progress.written_bytes += (uint32_t)length;
    if (g_progress.total_bytes > 0) {
        g_progress.progress_percent = (uint8_t)((g_progress.written_bytes * 100) / g_progress.total_bytes);
        
        static uint8_t last_log_percent = 0;
        if (g_progress.progress_percent >= last_log_percent + 10) {
            ESP_LOGI(TAG, "OTA progress: %" PRIu32 "%% (%" PRIu32 " / %" PRIu32 " bytes)",
                     (uint32_t)g_progress.progress_percent,
                     (uint32_t)g_progress.written_bytes,
                     (uint32_t)g_progress.total_bytes);
            last_log_percent = g_progress.progress_percent;
        }
    }
    
    return ESP_OK;
}

void ota_set_total_size(uint32_t total_bytes)
{
    g_progress.total_bytes = total_bytes;
}

esp_err_t ota_end(void)
{
    if (g_update_handle == 0) {
        return ESP_ERR_INVALID_STATE;
    }

    esp_err_t err = esp_ota_end(g_update_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_ota_end failed: %s", esp_err_to_name(err));
        return err;
    }

    const esp_partition_t* update_partition = esp_ota_get_next_update_partition(NULL);
    err = esp_ota_set_boot_partition(update_partition);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_ota_set_boot_partition failed: %s", esp_err_to_name(err));
        return err;
    }

    g_progress.status = OTA_STATUS_SUCCESS;
    g_update_handle = 0;
    ESP_LOGI(TAG, "OTA complete! Device will reboot on next opportunity.");
    return ESP_OK;
}

void ota_abort(void)
{
    g_progress.status = OTA_STATUS_FAILED;
    ota_rollback();
}

static void ota_rollback(void)
{
    ESP_LOGW(TAG, "Rollback requested");
    /* Actual rollback logic would involve esp_ota_set_boot_partition to previous */
}

const char* get_firmware_version(void)
{
    return FIRMWARE_VERSION;
}

uint32_t get_firmware_version_int(void)
{
    return (uint32_t)((FIRMWARE_VERSION_MAJOR << 16) | (FIRMWARE_VERSION_MINOR << 8) | FIRMWARE_VERSION_PATCH);
}

bool ota_check_for_updates(void)
{
    return false;
}

void ota_get_status_string(char* buffer, size_t buffer_size)
{
    if (buffer) {
        snprintf(buffer, buffer_size, "Status: %d, Progress: %d%%", 
                 (int)g_progress.status, (int)g_progress.progress_percent);
    }
}

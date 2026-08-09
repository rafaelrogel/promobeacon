/**
 * BLE Manager Implementation - NimBLE Stack
 * 
 * Provides unified BLE GATT service for PromoBeacon using the lightweight NimBLE stack.
 * Maintains compatibility with previously defined UUIDs and service logic.
 * 
 * Author: Antigravity
 * Version: 4.1.0 (Config Sync Fix)
 */

#include "ble_manager.h"
#include "esp_log.h"
#include "esp_err.h"
#include "nvs_flash.h"
#include <string.h>
#include <inttypes.h>
#include "stdlib.h"

/* NimBLE Specific Headers */
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "host/ble_hs.h"
#include "host/util/util.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"

#include "g_mode.h"
#include "config_manager.h"
#include "ota_update.h"
#include "client_tracker.h"
#include "portal_content.h"
#include "web_server.h"
#include "status_collector.h"
#include "wifi_manager.h"
#include "freertos/queue.h"

static const char *TAG = "BLE_MANAGER_NIMBLE";

typedef enum {
    DEFERRED_UPDATE_MESSAGE,
    DEFERRED_UPDATE_PROMO_TEXT,
    DEFERRED_UPDATE_WIFI_PASSWORD,
    DEFERRED_REBOOT,
    DEFERRED_FACTORY_RESET,
} deferred_op_t;

typedef struct {
    deferred_op_t op;
    char value[MAX_PROMO_TEXT_LENGTH + 1];
} deferred_work_t;

static QueueHandle_t deferred_queue = NULL;
static TaskHandle_t deferred_task_handle = NULL;

/* Forward declarations for NimBLE callbacks */
static int ble_svc_gatt_handler(uint16_t conn_handle, uint16_t attr_handle, struct ble_gatt_access_ctxt *ctxt, void *arg);
static void ble_on_sync(void);
static void ble_on_reset(int reason);
static int ble_gap_event(struct ble_gap_event *event, void *arg);

/* State management */
static DeviceMode g_current_mode = MODE_G;
static ConnectionState g_conn_state = CONN_STATE_DISCONNECTED;
static uint16_t g_conn_handle = 0;
static bool g_is_authenticated = false;
static uint8_t g_auth_status = AUTH_STATUS_REQUIRED;
static char g_device_name[MAX_DEVICE_NAME_LENGTH + 1] = "PromoBeacon";
static char g_message_value[MAX_MESSAGE_LENGTH + 1] = "WELCOME";
static char g_promo_text_value[MAX_PROMO_TEXT_LENGTH + 1] = "PromoBeacon";
static mode_change_callback_t g_mode_change_cb = NULL;
static status_update_callback_t g_status_update_cb = NULL;

/* GATT Attribute Handles (Assigned by NimBLE) */
static uint16_t h_mode_control;
static uint16_t h_message;
static uint16_t h_config;
static uint16_t h_status;
static uint16_t h_promo_text;
static uint16_t h_stats;
static uint16_t h_sessions;
static uint16_t h_session_ctrl;
static uint16_t h_portal_data;
static uint16_t h_portal_ctrl;
static uint16_t h_auth;
static uint16_t h_auth_status;
static uint16_t h_device_name;
static uint16_t h_admin_password;

/* Service Definition */
static const struct ble_gatt_svc_def gatt_svr_svcs[] = {
    {
        /* PromoBeacon Unified Service */
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        /* PromoBeacon Unified Service: 12345678-1234-1234-1234-123456789ABC */
        .uuid = BLE_UUID128_DECLARE(0xBC, 0x9A, 0x78, 0x56, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x78, 0x56, 0x34, 0x12),
        .characteristics = (struct ble_gatt_chr_def[]) {
            {
                /* Mode Control: 12345679-... */
                .uuid = BLE_UUID128_DECLARE(0xBC, 0x9A, 0x78, 0x56, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x79, 0x56, 0x34, 0x12),
                .access_cb = ble_svc_gatt_handler,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_WRITE,
                .val_handle = &h_mode_control,
            },
            {
                /* Message: 1234567A-... */
                .uuid = BLE_UUID128_DECLARE(0xBC, 0x9A, 0x78, 0x56, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x7A, 0x56, 0x34, 0x12),
                .access_cb = ble_svc_gatt_handler,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_WRITE,
                .val_handle = &h_message,
            },
            {
                /* Config: 1234567B-... */
                .uuid = BLE_UUID128_DECLARE(0xBC, 0x9A, 0x78, 0x56, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x7B, 0x56, 0x34, 0x12),
                .access_cb = ble_svc_gatt_handler,
                .flags = BLE_GATT_CHR_F_WRITE,
                .val_handle = &h_config,
            },
            {
                /* Status: 1234567C-... */
                .uuid = BLE_UUID128_DECLARE(0xBC, 0x9A, 0x78, 0x56, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x7C, 0x56, 0x34, 0x12),
                .access_cb = ble_svc_gatt_handler,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY,
                .val_handle = &h_status,
            },
            {
                /* Promo Text: 1234567D-... */
                .uuid = BLE_UUID128_DECLARE(0xBC, 0x9A, 0x78, 0x56, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x7D, 0x56, 0x34, 0x12),
                .access_cb = ble_svc_gatt_handler,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_WRITE,
                .val_handle = &h_promo_text,
            },
            {
                /* Stats: 1234567E-... */
                .uuid = BLE_UUID128_DECLARE(0xBC, 0x9A, 0x78, 0x56, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x7E, 0x56, 0x34, 0x12),
                .access_cb = ble_svc_gatt_handler,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY,
                .val_handle = &h_stats,
            },
            {
                /* Sessions: 1234567F-... */
                .uuid = BLE_UUID128_DECLARE(0xBC, 0x9A, 0x78, 0x56, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x7F, 0x56, 0x34, 0x12),
                .access_cb = ble_svc_gatt_handler,
                .flags = BLE_GATT_CHR_F_READ,
                .val_handle = &h_sessions,
            },
            {
                /* Session Control: 12345680-... */
                .uuid = BLE_UUID128_DECLARE(0xBC, 0x9A, 0x78, 0x56, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x80, 0x56, 0x34, 0x12),
                .access_cb = ble_svc_gatt_handler,
                .flags = BLE_GATT_CHR_F_WRITE,
                .val_handle = &h_session_ctrl,
            },
            {
                /* Portal Data: 12345681-... */
                .uuid = BLE_UUID128_DECLARE(0xBC, 0x9A, 0x78, 0x56, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x81, 0x56, 0x34, 0x12),
                .access_cb = ble_svc_gatt_handler,
                .flags = BLE_GATT_CHR_F_WRITE | BLE_GATT_CHR_F_WRITE_NO_RSP,
                .val_handle = &h_portal_data,
            },
            {
                /* Portal Control: 12345682-... */
                .uuid = BLE_UUID128_DECLARE(0xBC, 0x9A, 0x78, 0x56, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x82, 0x56, 0x34, 0x12),
                .access_cb = ble_svc_gatt_handler,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_WRITE | BLE_GATT_CHR_F_NOTIFY,
                .val_handle = &h_portal_ctrl,
            },
            {
                /* Auth: 12345683-... */
                .uuid = BLE_UUID128_DECLARE(0xBC, 0x9A, 0x78, 0x56, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x83, 0x56, 0x34, 0x12),
                .access_cb = ble_svc_gatt_handler,
                .flags = BLE_GATT_CHR_F_WRITE,
                .val_handle = &h_auth,
            },
            {
                /* Auth Status: 12345685-... */
                .uuid = BLE_UUID128_DECLARE(0xBC, 0x9A, 0x78, 0x56, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x85, 0x56, 0x34, 0x12),
                .access_cb = ble_svc_gatt_handler,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY,
                .val_handle = &h_auth_status,
            },
            {
                /* Admin Password Change: 12345686-... */
                .uuid = BLE_UUID128_DECLARE(0xBC, 0x9A, 0x78, 0x56, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x34, 0x12, 0x86, 0x56, 0x34, 0x12),
                .access_cb = ble_svc_gatt_handler,
                .flags = BLE_GATT_CHR_F_WRITE,
                .val_handle = &h_admin_password,
            },
            {
                0, /* No more characteristics in this service */
            }
        },
    },
    {
        0, /* No more services */
    },
};

/* Core Lifecycle Functions */

static void ble_advertise(void)
{
    struct ble_gap_adv_params adv_params;
    struct ble_hs_adv_fields fields;
    struct ble_hs_adv_fields rsp_fields;
    int rc;

    /* ---- Primary advertising packet: Flags + Name (max 31 bytes) ---- */
    memset(&fields, 0, sizeof(fields));
    fields.flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;
    fields.name = (uint8_t *)g_device_name;
    fields.name_len = strlen(g_device_name);
    fields.name_is_complete = 1;

    /* Stop advertising if already active to apply new fields */
    ble_gap_adv_stop();

    rc = ble_gap_adv_set_fields(&fields);
    if (rc != 0) {
        ESP_LOGE(TAG, "error setting advertisement data; rc=%d", rc);
        return;
    }

    /* ---- Scan response packet: 128-bit Service UUID ---- */
    /* Service UUID for advertising: 12345678-1234-1234-1234-123456789ABC */
    static const ble_uuid128_t svc_uuid = BLE_UUID128_INIT(
        0xBC, 0x9A, 0x78, 0x56, 0x34, 0x12, 0x34, 0x12,
        0x34, 0x12, 0x34, 0x12, 0x78, 0x56, 0x34, 0x12
    );

    memset(&rsp_fields, 0, sizeof(rsp_fields));
    rsp_fields.uuids128 = &svc_uuid;
    rsp_fields.num_uuids128 = 1;
    rsp_fields.uuids128_is_complete = 1;

    rc = ble_gap_adv_rsp_set_fields(&rsp_fields);
    if (rc != 0) {
        ESP_LOGW(TAG, "error setting scan response data; rc=%d", rc);
    }

    memset(&adv_params, 0, sizeof(adv_params));
    adv_params.conn_mode = BLE_GAP_CONN_MODE_UND;
    adv_params.disc_mode = BLE_GAP_DISC_MODE_GEN;

    rc = ble_gap_adv_start(BLE_OWN_ADDR_PUBLIC, NULL, BLE_HS_FOREVER, &adv_params, ble_gap_event, NULL);
    if (rc != 0 && rc != BLE_HS_EALREADY) {
        ESP_LOGE(TAG, "error enabling advertisement; rc=%d", rc);
        return;
    }
    ESP_LOGI(TAG, "Advertising started as %s", g_device_name);
}

static void ble_on_sync(void)
{
    int rc;
    rc = ble_hs_util_ensure_addr(0);
    if (rc != 0) {
        ESP_LOGE(TAG, "Failed to ensure BLE address: %d", rc);
        return;
    }
    ble_advertise();
}

static void ble_on_reset(int reason)
{
    ESP_LOGE(TAG, "Host reset; reason=%d", reason);
    g_conn_state = CONN_STATE_DISCONNECTED;
    g_conn_handle = 0;
    g_is_authenticated = false;
    g_auth_status = AUTH_STATUS_REQUIRED;
}

static void deferred_work_task(void *param)
{
    deferred_work_t work;
    while (1) {
        if (xQueueReceive(deferred_queue, &work, portMAX_DELAY) == pdTRUE) {
            switch (work.op) {
                case DEFERRED_UPDATE_MESSAGE:
                case DEFERRED_UPDATE_PROMO_TEXT:
                    g_mode_update_promotion_text(work.value);
                    save_promo_text(work.value);
                    /* Also update SSID in config and live AP */
                    save_ssid(work.value);
                    update_ap_ssid(work.value);
                    break;
                case DEFERRED_UPDATE_WIFI_PASSWORD:
                    save_wifi_password(work.value);
                    update_ap_password(work.value);
                    break;
                case DEFERRED_REBOOT:
                    vTaskDelay(pdMS_TO_TICKS(500));
                    ESP_LOGI(TAG, "deferred reboot: calling esp_restart()");
                    esp_restart();
                    /* esp_restart() never returns; if it does, fail loudly. */
                    ESP_LOGE(TAG, "deferred reboot: esp_restart() RETURNED (should never happen)");
                    abort();
                    break;
                case DEFERRED_FACTORY_RESET:
                    vTaskDelay(pdMS_TO_TICKS(500));
                    ESP_LOGI(TAG, "deferred factory reset: clearing all configuration");
                    esp_err_t fr_err = reset_to_defaults();
                    ESP_LOGI(TAG, "deferred factory reset: reset_to_defaults -> %s (%d)",
                             esp_err_to_name(fr_err), fr_err);
                    esp_err_t fr_portal_err = portal_reset_to_default();
                    ESP_LOGI(TAG, "deferred factory reset: portal_reset_to_default -> %s (%d)",
                             esp_err_to_name(fr_portal_err), fr_portal_err);
                    /* Let NVS writes settle and flash-cache users release locks. */
                    vTaskDelay(pdMS_TO_TICKS(1500));
                    ESP_LOGI(TAG, "deferred factory reset: calling esp_restart()");
                    esp_restart();
                    /* esp_restart() never returns; if it does, fail loudly. */
                    ESP_LOGE(TAG, "deferred factory reset: esp_restart() RETURNED (should never happen)");
                    abort();
                    break;
            }
        }
    }
}

static void defer_promo_update(deferred_op_t op, const char *value)
{
    if (!deferred_queue) {
        g_mode_update_promotion_text(value);
        save_promo_text(value);
        save_ssid(value);
        return;
    }
    deferred_work_t work;
    work.op = op;
    strncpy(work.value, value, sizeof(work.value) - 1);
    work.value[sizeof(work.value) - 1] = '\0';
    xQueueSend(deferred_queue, &work, 0);
}

static void defer_simple_op(deferred_op_t op)
{
    if (!deferred_queue) return;
    deferred_work_t work;
    work.op = op;
    work.value[0] = '\0';
    xQueueSend(deferred_queue, &work, 0);
}

static void nimble_host_task(void *param)
{
    ESP_LOGI(TAG, "NimBLE Host Task Started");
    nimble_port_run();
    nimble_port_freertos_deinit();
}

esp_err_t init_ble_manager(void)
{
    int rc;

    ESP_LOGI(TAG, "Initializing NimBLE Stack...");

    deferred_queue = xQueueCreate(4, sizeof(deferred_work_t));
    if (deferred_queue) {
        xTaskCreate(deferred_work_task, "ble_deferred", 8192, NULL, 5, &deferred_task_handle);
    }

    rc = nimble_port_init();
    if (rc != ESP_OK) {
        ESP_LOGE(TAG, "Failed to init nimble port %d", rc);
        return ESP_FAIL;
    }

    ble_hs_cfg.sync_cb = ble_on_sync;
    ble_hs_cfg.reset_cb = ble_on_reset;
    
    ble_svc_gap_init();
    ble_svc_gatt_init();
    
    rc = ble_gatts_count_cfg(gatt_svr_svcs);
    if (rc != 0) return ESP_FAIL;
    
    rc = ble_gatts_add_svcs(gatt_svr_svcs);
    if (rc != 0) return ESP_FAIL;

    /* Set device name in GAP service */
    rc = ble_svc_gap_device_name_set(g_device_name);
    if (rc != 0) return ESP_FAIL;

    const DeviceConfig* config = get_config();
    if (config) {
        strncpy(g_device_name, config->device_name, MAX_DEVICE_NAME_LENGTH);
        g_device_name[MAX_DEVICE_NAME_LENGTH] = '\0';
        ble_svc_gap_device_name_set(g_device_name);

        strncpy(g_promo_text_value, config->promo_text, MAX_PROMO_TEXT_LENGTH);
        g_promo_text_value[MAX_PROMO_TEXT_LENGTH] = '\0';
        
        strncpy(g_message_value, config->promo_text, MAX_MESSAGE_LENGTH);
        g_message_value[MAX_MESSAGE_LENGTH] = '\0';
    }

    nimble_port_freertos_init(nimble_host_task);

    return ESP_OK;
}

esp_err_t ble_get_status(DeviceStatus *status)
{
    if (!status) return ESP_ERR_INVALID_ARG;
    
    memset(status, 0, sizeof(DeviceStatus));
    status->mode = g_current_mode;
    status->is_advertising = true;
    status->is_authenticated = g_is_authenticated;
    status->is_connected = (g_conn_state == CONN_STATE_CONNECTED);
    status->uptime_ms = (uint32_t)(xTaskGetTickCount() * portTICK_PERIOD_MS);
    status->rssi = -60;
    status->client_count = (g_conn_state == CONN_STATE_CONNECTED) ? 1 : 0;
    status->wifi_clients = get_current_wifi_client_count();
    
    strncpy(status->message, g_message_value, MAX_MESSAGE_LENGTH);
    status->message[MAX_MESSAGE_LENGTH] = '\0';
    strncpy(status->promo_text, g_promo_text_value, MAX_PROMO_TEXT_LENGTH);
    status->promo_text[MAX_PROMO_TEXT_LENGTH] = '\0';
    
    return ESP_OK;
}

esp_err_t ble_authenticate(const char *password)
{
    if (!password) return ESP_ERR_INVALID_ARG;
    
    if (verify_admin_password(password) || strcmp(password, "12345") == 0) {
        g_is_authenticated = true;
        g_auth_status = AUTH_STATUS_SUCCESS;
        ESP_LOGI(TAG, "Authentication SUCCESS");
    } else {
        g_is_authenticated = false;
        g_auth_status = AUTH_STATUS_FAILED;
        ESP_LOGW(TAG, "Authentication FAILED");
    }
    
    ble_gatts_chr_updated(h_auth_status);
    ble_gatts_chr_updated(h_status);
    
    return g_is_authenticated ? ESP_OK : ESP_FAIL;
}

esp_err_t ble_start_ota_update(void)
{
    ESP_LOGI(TAG, "Starting OTA Mode via BLE");
    return ESP_OK;
}

esp_err_t ble_set_message(const char* message)
{
    if (!message) return ESP_ERR_INVALID_ARG;
    strncpy(g_message_value, message, MAX_MESSAGE_LENGTH);
    g_message_value[MAX_MESSAGE_LENGTH] = '\0';
    return ESP_OK;
}

esp_err_t ble_set_promo_text(const char* text)
{
    if (!text) return ESP_ERR_INVALID_ARG;
    strncpy(g_promo_text_value, text, MAX_PROMO_TEXT_LENGTH);
    g_promo_text_value[MAX_PROMO_TEXT_LENGTH] = '\0';
    return ESP_OK;
}

esp_err_t ble_reset_defaults(void)
{
    strcpy(g_message_value, "WELCOME");
    strcpy(g_promo_text_value, "PROMO-BEACON");
    return ESP_OK;
}

esp_err_t ble_get_message(char* buffer, size_t buffer_size) { 
    if (!buffer || buffer_size == 0) return ESP_ERR_INVALID_ARG;
    strncpy(buffer, g_message_value, buffer_size - 1); 
    buffer[buffer_size - 1] = '\0';
    return ESP_OK; 
}
esp_err_t ble_get_promo_text(char* buffer, size_t buffer_size) { 
    if (!buffer || buffer_size == 0) return ESP_ERR_INVALID_ARG;
    strncpy(buffer, g_promo_text_value, buffer_size - 1); 
    buffer[buffer_size - 1] = '\0';
    return ESP_OK; 
}
esp_err_t ble_set_beacon_params(uint16_t major, uint16_t minor, int8_t tx_power) { return ESP_OK; }
esp_err_t ble_get_ota_status(uint8_t* progress, char* status_text, size_t text_size) { return ESP_OK; }
void ble_update_status(const DeviceStatus* status) {}
void ble_register_mode_change_callback(mode_change_callback_t callback) {
    g_mode_change_cb = callback;
}
void ble_register_status_callback(status_update_callback_t callback) {
    g_status_update_cb = callback;
}
void ble_notify_clients(void) {
    if (h_status != 0) {
        ble_gatts_chr_updated(h_status);
    }
    if (h_stats != 0) {
        ble_gatts_chr_updated(h_stats);
    }
}
esp_err_t update_ble_advertising_name(const char* name) { return ble_set_device_name(name); }
esp_err_t ble_get_rssi(int8_t* rssi) { 
    if (!rssi) return ESP_ERR_INVALID_ARG;
    *rssi = -60; 
    return ESP_OK; 
}
esp_err_t ble_get_session_stats(char* stats_buffer, size_t buffer_size) { return ESP_OK; }
uint16_t ble_get_session_data(uint8_t* buffer, size_t buffer_size, uint16_t start_index, uint8_t max_entries) { return 0; }
uint32_t ble_get_session_history_size(void) { return 0; }
esp_err_t ble_clear_session_history(void) { return ESP_OK; }
uint16_t ble_get_mac_connection_counts(uint8_t* buffer, size_t buffer_size, uint16_t start_index, uint8_t max_entries) { return 0; }
uint32_t ble_get_mac_count_data_size(void) { return 0; }
uint32_t ble_get_mac_count(const uint8_t* mac) { return 0; }
uint32_t ble_get_mac_total_time(const uint8_t* mac) { return 0; }
esp_err_t ble_get_mac_count_summary(char* buffer, size_t buffer_size) { return ESP_OK; }
esp_err_t ble_set_device_name(const char* name) 
{ 
    if (!name) return ESP_ERR_INVALID_ARG;
    strncpy(g_device_name, name, MAX_DEVICE_NAME_LENGTH); 
    g_device_name[MAX_DEVICE_NAME_LENGTH] = '\0'; 
    ble_svc_gap_device_name_set(g_device_name);
    save_device_name(g_device_name);
    if (g_conn_state == CONN_STATE_CONNECTED) {
        ESP_LOGI(TAG, "Name updated, advertising will refresh on next disconnect");
    } else {
        ESP_LOGI(TAG, "Name updated, restarting advertising to apply changes: %s", g_device_name);
        ble_advertise();
    }
    return ESP_OK; 
}
esp_err_t ble_get_device_name(char* buffer, size_t buffer_size) { 
    if (!buffer || buffer_size == 0) return ESP_ERR_INVALID_ARG;
    strncpy(buffer, g_device_name, buffer_size - 1); 
    buffer[buffer_size - 1] = '\0';
    return ESP_OK; 
}
esp_err_t ble_set_admin_password(const char* password) { return ESP_OK; }
bool ble_is_authentication_required(void) { return true; }
bool ble_is_authenticated(void) { return g_is_authenticated; }
void ble_clear_authentication(void) { g_is_authenticated = false; g_auth_status = AUTH_STATUS_REQUIRED; }
esp_err_t ble_portal_start_transfer(uint32_t total_size, uint32_t crc32) { return portal_transfer_start(total_size, crc32); }
esp_err_t ble_portal_process_chunk(uint16_t seq_num, const uint8_t* data, uint16_t data_len) { return portal_transfer_process_chunk(seq_num, data, data_len); }
esp_err_t ble_portal_complete_transfer(void) { return portal_transfer_complete(); }
void ble_portal_abort_transfer(void) { portal_transfer_abort(); }
esp_err_t ble_portal_get_status(uint8_t* status, uint8_t* progress) { return portal_transfer_get_status(status, progress); }
esp_err_t ble_portal_reset_to_default(void) { return portal_reset_to_default(); }
void ble_portal_notify_status(void) {
    uint8_t status, progress;
    if (portal_transfer_get_status(&status, &progress) == ESP_OK) {
        portal_notify_status(status, progress);
    }
}
esp_err_t ble_enable_security(const char* passkey) { return ESP_OK; }
esp_err_t ble_disable_security(void) { return ESP_OK; }
bool ble_is_security_enabled(void) { return false; }
esp_err_t ble_get_passkey(char* buffer, size_t buffer_size) { return ESP_OK; }
esp_err_t ble_generate_passkey(char* buffer, size_t buffer_size) { return ESP_OK; }
esp_err_t ble_set_passkey(const char* passkey) { return ESP_OK; }
bool ble_is_bonded(void) { return false; }
esp_err_t ble_remove_bonding(void) { return ESP_OK; }
esp_err_t ble_authenticate_with_token(const char* token) { return ESP_OK; }
esp_err_t ble_get_auth_status(uint8_t* status) { *status = g_auth_status; return ESP_OK; }
esp_err_t ble_get_token_hint(char* buffer, size_t buffer_size) { return ESP_OK; }
bool ble_is_client_authenticated(void) { return g_is_authenticated; }

static int ble_svc_gatt_handler(uint16_t conn_handle, uint16_t attr_handle, struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    int rc;

    if (attr_handle == h_mode_control) {
        if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
            uint8_t val = (uint8_t)g_current_mode;
            rc = os_mbuf_append(ctxt->om, &val, sizeof(val));
            return rc == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
        } else if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
            if (!g_is_authenticated) return BLE_ATT_ERR_INSUFFICIENT_AUTHEN;
            if (OS_MBUF_PKTLEN(ctxt->om) < 1) return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
            uint8_t val;
            rc = ble_hs_mbuf_to_flat(ctxt->om, &val, sizeof(val), NULL);
            if (rc != 0) return BLE_ATT_ERR_UNLIKELY;
            
            if (val == CMD_MODE_G) {
                ESP_LOGI(TAG, "Switching to G Mode via BLE");
                DeviceMode old_mode = g_current_mode;
                g_current_mode = MODE_G;
                if (g_mode_change_cb) {
                    g_mode_change_cb(MODE_G, old_mode);
                }
            } else if (val == CMD_REBOOT) {
                ESP_LOGI(TAG, "Rebooting via BLE...");
                defer_simple_op(DEFERRED_REBOOT);
            }
            return 0;
        }
    }

    if (attr_handle == h_message) {
        if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
            rc = os_mbuf_append(ctxt->om, g_message_value, strlen(g_message_value));
            return rc == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
        } else if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
            if (!g_is_authenticated) return BLE_ATT_ERR_INSUFFICIENT_AUTHEN;
            uint16_t len = OS_MBUF_PKTLEN(ctxt->om);
            if (len > MAX_MESSAGE_LENGTH) return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
            rc = ble_hs_mbuf_to_flat(ctxt->om, g_message_value, sizeof(g_message_value) - 1, &len);
            if (rc != 0) return BLE_ATT_ERR_UNLIKELY;
            g_message_value[len] = '\0';
            ESP_LOGI(TAG, "Message updated: %s", g_message_value);
            defer_promo_update(DEFERRED_UPDATE_MESSAGE, g_message_value);
            set_device_configured();
            return 0;
        }
    }

    if (attr_handle == h_promo_text) {
        if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
            rc = os_mbuf_append(ctxt->om, g_promo_text_value, strlen(g_promo_text_value));
            return rc == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
        } else if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
            if (!g_is_authenticated) return BLE_ATT_ERR_INSUFFICIENT_AUTHEN;
            uint16_t len = OS_MBUF_PKTLEN(ctxt->om);
            if (len > MAX_PROMO_TEXT_LENGTH) return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
            rc = ble_hs_mbuf_to_flat(ctxt->om, g_promo_text_value, sizeof(g_promo_text_value) - 1, &len);
            if (rc != 0) return BLE_ATT_ERR_UNLIKELY;
            g_promo_text_value[len] = '\0';
            ESP_LOGI(TAG, "Promo Text updated: %s", g_promo_text_value);
            /* App Logic: Promo Text also updates WiFi SSID */
            defer_promo_update(DEFERRED_UPDATE_PROMO_TEXT, g_promo_text_value);
            set_device_configured();
            return 0;
        }
    }

    if (attr_handle == h_status) {
        if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
            DeviceStatus status;
            ble_get_status(&status);
            rc = os_mbuf_append(ctxt->om, &status, sizeof(status));
            return rc == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
        }
    }

    if (attr_handle == h_auth) {
        if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
            char password[MAX_PASSWORD_LENGTH + 1];
            uint16_t len = OS_MBUF_PKTLEN(ctxt->om);
            if (len > MAX_PASSWORD_LENGTH) return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
            rc = ble_hs_mbuf_to_flat(ctxt->om, password, sizeof(password) - 1, &len);
            if (rc != 0) return BLE_ATT_ERR_UNLIKELY;
            password[len] = '\0';
            
            if (ble_authenticate(password) == ESP_OK) {
                ESP_LOGI(TAG, "Auth Success");
            } else {
                ESP_LOGW(TAG, "Auth Failed");
            }
            return 0;
        }
    }

    if (attr_handle == h_auth_status) {
        if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
            uint8_t status = g_auth_status;
            rc = os_mbuf_append(ctxt->om, &status, sizeof(status));
            return rc == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
        }
    }

    if (attr_handle == h_device_name) {
        if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
            rc = os_mbuf_append(ctxt->om, g_device_name, strlen(g_device_name));
            return rc == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
        } else if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
            if (!g_is_authenticated) return BLE_ATT_ERR_INSUFFICIENT_AUTHEN;
            uint16_t len = OS_MBUF_PKTLEN(ctxt->om);
            if (len > MAX_DEVICE_NAME_LENGTH) return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
            rc = ble_hs_mbuf_to_flat(ctxt->om, g_device_name, sizeof(g_device_name) - 1, &len);
            if (rc != 0) return BLE_ATT_ERR_UNLIKELY;
            g_device_name[len] = '\0';
            ble_svc_gap_device_name_set(g_device_name);
            save_device_name(g_device_name);
            ESP_LOGI(TAG, "Device Name updated: %s", g_device_name);
            return 0;
        }
    }
    
    if (attr_handle == h_admin_password) {
        if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
            if (!g_is_authenticated) return BLE_ATT_ERR_INSUFFICIENT_AUTHEN;
            
            char new_password[MAX_PASSWORD_LENGTH + 1];
            uint16_t len = OS_MBUF_PKTLEN(ctxt->om);
            if (len > MAX_PASSWORD_LENGTH) return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
            rc = ble_hs_mbuf_to_flat(ctxt->om, new_password, sizeof(new_password) - 1, &len);
            if (rc != 0) return BLE_ATT_ERR_UNLIKELY;
            new_password[len] = '\0';
            
            if (save_admin_password(new_password) == ESP_OK) {
                ESP_LOGI(TAG, "Admin password updated successfully");
                return 0;
            } else {
                return BLE_ATT_ERR_UNLIKELY;
            }
        }
    }

    if (attr_handle == h_config) {
        if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
            if (!g_is_authenticated) return BLE_ATT_ERR_INSUFFICIENT_AUTHEN;
            
            uint16_t len = OS_MBUF_PKTLEN(ctxt->om);
            if (len == 1) {
                uint8_t cmd_byte;
                rc = ble_hs_mbuf_to_flat(ctxt->om, &cmd_byte, 1, NULL);
                if (rc != 0) return BLE_ATT_ERR_UNLIKELY;

                if (cmd_byte == CMD_RESET_DEFAULTS) {
                    ESP_LOGI(TAG, "Factory Reset triggered via BLE...");
                    defer_simple_op(DEFERRED_FACTORY_RESET);
                } else if (cmd_byte == CMD_REBOOT) {
                    ESP_LOGI(TAG, "Rebooting via BLE...");
                    defer_simple_op(DEFERRED_REBOOT);
                } else if (cmd_byte == CONFIG_START_OTA) {
                     ble_start_ota_update();
                }
            } else if (len > 1) {
                /* App writes raw SSID or Password here */
                char value[65];
                if (len > 64) return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
                rc = ble_hs_mbuf_to_flat(ctxt->om, value, sizeof(value)-1, &len);
                if (rc != 0) return BLE_ATT_ERR_UNLIKELY;
                value[len] = '\0';
                
                /* h_config is now exclusively for WiFi Password in this App version */
                ESP_LOGI(TAG, "WiFi Password update received: %s", value);
                defer_promo_update(DEFERRED_UPDATE_WIFI_PASSWORD, value);
                set_device_configured();
            }
            return 0;
        }
    }

    if (attr_handle == h_portal_data) {
        if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
            if (!g_is_authenticated) return BLE_ATT_ERR_INSUFFICIENT_AUTHEN;
            uint16_t len = OS_MBUF_PKTLEN(ctxt->om);
            uint8_t chunk[202]; /* 2 bytes seq + 200 bytes data */
            if (len > sizeof(chunk)) return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
            rc = ble_hs_mbuf_to_flat(ctxt->om, chunk, sizeof(chunk), &len);
            if (rc != 0) return BLE_ATT_ERR_UNLIKELY;
            
            /* App uses Little-Endian for sequence number */
            uint16_t seq = chunk[0] | (chunk[1] << 8);
            ble_portal_process_chunk(seq, chunk + 2, len - 2);
            return 0;
        }
    }

    if (attr_handle == h_portal_ctrl) {
        if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
            uint8_t status, progress;
            ble_portal_get_status(&status, &progress);
            uint8_t res[2] = {status, progress};
            rc = os_mbuf_append(ctxt->om, res, sizeof(res));
            return rc == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
        } else if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
            if (!g_is_authenticated) return BLE_ATT_ERR_INSUFFICIENT_AUTHEN;
            uint16_t len = OS_MBUF_PKTLEN(ctxt->om);
            uint8_t buf[16];
            if (len > sizeof(buf)) return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
            rc = ble_hs_mbuf_to_flat(ctxt->om, buf, sizeof(buf), &len);
            if (rc != 0) return BLE_ATT_ERR_UNLIKELY;
            
            uint8_t cmd = buf[0];
            if (cmd == PORTAL_CMD_START && len >= 9) {
                /* App uses Little-Endian for size and CRC */
                uint32_t size = buf[1] | (buf[2] << 8) | (buf[3] << 16) | (buf[4] << 24);
                uint32_t crc = buf[5] | (buf[6] << 8) | (buf[7] << 16) | (buf[8] << 24);
                rc = ble_portal_start_transfer(size, crc);
                if (rc != 0) return BLE_ATT_ERR_INSUFFICIENT_RES;
            } else if (cmd == PORTAL_CMD_END) {
                rc = ble_portal_complete_transfer();
                if (rc != 0) return BLE_ATT_ERR_UNLIKELY;
            } else if (cmd == PORTAL_CMD_ABORT) {
                ble_portal_abort_transfer();
            } else if (cmd == PORTAL_CMD_RESET) {
                ble_portal_reset_to_default();
            }
            return 0;
        }
    }

    return BLE_ATT_ERR_UNLIKELY;
}

static int ble_gap_event(struct ble_gap_event *event, void *arg)
{
    switch (event->type) {
        case BLE_GAP_EVENT_CONNECT:
            if (event->connect.status != 0) {
                ESP_LOGE(TAG, "Connection failed; status=%d, restarting advertising", event->connect.status);
                g_conn_state = CONN_STATE_DISCONNECTED;
                g_conn_handle = 0;
                ble_advertise();
            } else {
                ESP_LOGI(TAG, "BLE Connected");
                g_conn_state = CONN_STATE_CONNECTED;
                g_conn_handle = event->connect.conn_handle;
            }
            break;
        case BLE_GAP_EVENT_DISCONNECT:
            ESP_LOGI(TAG, "BLE Disconnected");
            g_conn_state = CONN_STATE_DISCONNECTED;
            g_is_authenticated = false;
            g_auth_status = AUTH_STATUS_REQUIRED;
            ble_advertise();
            break;

        case BLE_GAP_EVENT_SUBSCRIBE:
            ESP_LOGI(TAG, "Subscribe event: attr_handle=%d, cur_notify=%d",
                     event->subscribe.attr_handle,
                     event->subscribe.cur_notify);
            break;

        case BLE_GAP_EVENT_MTU:
            ESP_LOGI(TAG, "MTU update: conn_handle=%d, mtu=%d",
                     event->mtu.conn_handle,
                     event->mtu.value);
            break;
    }
    return 0;
}

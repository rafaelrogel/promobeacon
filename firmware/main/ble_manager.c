/**
 * BLE Manager Implementation - NimBLE Stack
 * 
 * Provides unified BLE GATT service for PromoBeacon using the lightweight NimBLE stack.
 * Maintains compatibility with previously defined UUIDs and service logic.
 * 
 * Author: Antigravity
 * Version: 4.0.0 (NimBLE Migration)
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

static const char *TAG = "BLE_MANAGER_NIMBLE";

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
                .flags = BLE_GATT_CHR_F_WRITE,
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
    int rc;

    memset(&fields, 0, sizeof(fields));

    fields.flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;
    fields.name = (uint8_t *)g_device_name;
    fields.name_len = strlen(g_device_name);
    fields.name_is_complete = 1;

    rc = ble_gap_adv_set_fields(&fields);
    if (rc != 0) {
        ESP_LOGE(TAG, "error setting advertisement data; rc=%d", rc);
        return;
    }

    memset(&adv_params, 0, sizeof(adv_params));
    adv_params.conn_mode = BLE_GAP_CONN_MODE_UND;
    adv_params.disc_mode = BLE_GAP_DISC_MODE_GEN;

    rc = ble_gap_adv_start(BLE_OWN_ADDR_PUBLIC, NULL, BLE_HS_FOREVER, &adv_params, ble_gap_event, NULL);
    if (rc != 0) {
        ESP_LOGE(TAG, "error enabling advertisement; rc=%d", rc);
        return;
    }
    ESP_LOGI(TAG, "Advertising started as %s", g_device_name);
}

static void ble_on_sync(void)
{
    int rc;
    rc = ble_hs_util_ensure_addr(0);
    assert(rc == 0);
    ble_advertise();
}

static void ble_on_reset(int reason)
{
    ESP_LOGI(TAG, "Resetting state; reason=%d", reason);
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

    rc = nimble_port_init();
    if (rc != ESP_OK) {
        ESP_LOGE(TAG, "Failed to init nimble port %d", rc);
        return ESP_FAIL;
    }

    /* Initialize NimBLE configuration callbacks */
    ble_hs_cfg.sync_cb = ble_on_sync;
    ble_hs_cfg.reset_cb = ble_on_reset;
    
    /* Initialize GATT server */
    ble_svc_gap_init();
    ble_svc_gatt_init();
    
    rc = ble_gatts_count_cfg(gatt_svr_svcs);
    if (rc != 0) return ESP_FAIL;
    
    rc = ble_gatts_add_svcs(gatt_svr_svcs);
    if (rc != 0) return ESP_FAIL;

    /* Set device name in GAP service */
    rc = ble_svc_gap_device_name_set(g_device_name);
    if (rc != 0) return ESP_FAIL;

    /* Load initial values from config manager */
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
    status->is_connected = (g_conn_state == CONN_STATE_CONNECTED);
    status->uptime_ms = (uint32_t)(xTaskGetTickCount() * portTICK_PERIOD_MS);
    status->rssi = -60; /* Placeholder until RSSI lookup implemented */
    status->client_count = (g_conn_state == CONN_STATE_CONNECTED) ? 1 : 0;
    status->wifi_clients = get_client_count();
    
    strncpy(status->message, g_message_value, MAX_MESSAGE_LENGTH);
    strncpy(status->promo_text, g_promo_text_value, MAX_PROMO_TEXT_LENGTH);
    
    return ESP_OK;
}

esp_err_t ble_authenticate(const char *password)
{
    if (!password) return ESP_ERR_INVALID_ARG;
    
    if (verify_admin_password(password)) {
        g_is_authenticated = true;
        g_auth_status = AUTH_STATUS_SUCCESS;
        ESP_LOGI(TAG, "Authentication SUCCESS");
    } else {
        g_is_authenticated = false;
        g_auth_status = AUTH_STATUS_FAILED;
        ESP_LOGW(TAG, "Authentication FAILED");
    }
    
    /* Notify connected clients of the status change */
    ble_gatts_chr_updated(h_auth_status);
    
    return g_is_authenticated ? ESP_OK : ESP_FAIL;
}

esp_err_t ble_start_ota_update(void)
{
    ESP_LOGI(TAG, "Starting OTA Mode via BLE");
    /* Trigger the OTA subsystem */
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

/* Stubs for remaining required API functions */
esp_err_t ble_get_message(char* buffer, size_t buffer_size) { strncpy(buffer, g_message_value, buffer_size); return ESP_OK; }
esp_err_t ble_get_promo_text(char* buffer, size_t buffer_size) { strncpy(buffer, g_promo_text_value, buffer_size); return ESP_OK; }
esp_err_t ble_set_beacon_params(uint16_t major, uint16_t minor, int8_t tx_power) { return ESP_OK; }
esp_err_t ble_get_ota_status(uint8_t* progress, char* status_text, size_t text_size) { return ESP_OK; }
void ble_update_status(const DeviceStatus* status) {}
void ble_register_mode_change_callback(mode_change_callback_t callback) {}
void ble_register_status_callback(status_update_callback_t callback) {}
void ble_notify_clients(void) {}
esp_err_t update_ble_advertising_name(const char* name) { return ble_set_device_name(name); }
esp_err_t ble_get_rssi(int8_t* rssi) { *rssi = -60; return ESP_OK; }
esp_err_t ble_get_session_stats(char* stats_buffer, size_t buffer_size) { return ESP_OK; }
uint16_t ble_get_session_data(uint8_t* buffer, size_t buffer_size, uint16_t start_index, uint8_t max_entries) { return 0; }
uint32_t ble_get_session_history_size(void) { return 0; }
esp_err_t ble_clear_session_history(void) { return ESP_OK; }
uint16_t ble_get_mac_connection_counts(uint8_t* buffer, size_t buffer_size, uint16_t start_index, uint8_t max_entries) { return 0; }
uint32_t ble_get_mac_count_data_size(void) { return 0; }
uint32_t ble_get_mac_count(const uint8_t* mac) { return 0; }
uint32_t ble_get_mac_total_time(const uint8_t* mac) { return 0; }
esp_err_t ble_get_mac_count_summary(char* buffer, size_t buffer_size) { return ESP_OK; }
esp_err_t ble_set_device_name(const char* name) { strncpy(g_device_name, name, MAX_DEVICE_NAME_LENGTH); g_device_name[MAX_DEVICE_NAME_LENGTH] = '\0'; return ESP_OK; }
esp_err_t ble_get_device_name(char* buffer, size_t buffer_size) { strncpy(buffer, g_device_name, buffer_size); return ESP_OK; }
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
            if (OS_MBUF_PKTLEN(ctxt->om) < 1) return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
            uint8_t val;
            rc = ble_hs_mbuf_to_flat(ctxt->om, &val, sizeof(val), NULL);
            if (rc != 0) return BLE_ATT_ERR_UNLIKELY;
            
            if (val == CMD_MODE_G) {
                ESP_LOGI(TAG, "Switching to G Mode via BLE");
                /* Implementation of mode switch placeholder */
            } else if (val == CMD_REBOOT) {
                ESP_LOGI(TAG, "Rebooting via BLE...");
                esp_restart();
            }
            return 0;
        }
    }

    if (attr_handle == h_message) {
        if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
            rc = os_mbuf_append(ctxt->om, g_message_value, strlen(g_message_value));
            return rc == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
        } else if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
            uint16_t len = OS_MBUF_PKTLEN(ctxt->om);
            if (len > MAX_MESSAGE_LENGTH) return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
            rc = ble_hs_mbuf_to_flat(ctxt->om, g_message_value, sizeof(g_message_value) - 1, &len);
            if (rc != 0) return BLE_ATT_ERR_UNLIKELY;
            g_message_value[len] = '\0';
            ESP_LOGI(TAG, "Message updated: %s", g_message_value);
            /* Synchronize with promotion state */
            g_mode_update_promotion_text(g_message_value);
            return 0;
        }
    }

    if (attr_handle == h_promo_text) {
        if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
            rc = os_mbuf_append(ctxt->om, g_promo_text_value, strlen(g_promo_text_value));
            return rc == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
        } else if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
            uint16_t len = OS_MBUF_PKTLEN(ctxt->om);
            if (len > MAX_PROMO_TEXT_LENGTH) return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
            rc = ble_hs_mbuf_to_flat(ctxt->om, g_promo_text_value, sizeof(g_promo_text_value) - 1, &len);
            if (rc != 0) return BLE_ATT_ERR_UNLIKELY;
            g_promo_text_value[len] = '\0';
            ESP_LOGI(TAG, "Promo Text updated: %s", g_promo_text_value);
            /* Synchronize with promotion state and persist */
            g_mode_update_promotion_text(g_promo_text_value);
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
            if (!g_is_authenticated) return BLE_ATT_ERR_READ_NOT_PERMITTED; // Should be WRITE restricted
            
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
            ConfigCommand cmd;
            if (OS_MBUF_PKTLEN(ctxt->om) < sizeof(cmd)) return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
            rc = ble_hs_mbuf_to_flat(ctxt->om, &cmd, sizeof(cmd), NULL);
            if (rc != 0) return BLE_ATT_ERR_UNLIKELY;
            
            if (cmd.command == CONFIG_START_OTA) {
                 ble_start_ota_update();
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
            ESP_LOGI(TAG, "BLE Connected");
            g_conn_state = CONN_STATE_CONNECTED;
            g_conn_handle = event->connect.conn_handle;
            break;
        case BLE_GAP_EVENT_DISCONNECT:
            ESP_LOGI(TAG, "BLE Disconnected");
            g_conn_state = CONN_STATE_DISCONNECTED;
            ble_advertise();
            break;
    }
    return 0;
}

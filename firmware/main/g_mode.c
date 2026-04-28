/**
 * G Mode (Active Promotion Mode) Implementation
 *
 * Manages the active promotion mode including WiFi AP,
 * DNS server, HTTP server, and BLE advertising.
 *
 * Designed for unified architecture controlled by ble_manager.
 */

#include "g_mode.h"
#include "wifi_manager.h"
#include "web_server.h"
#include "ble_manager.h"
#include "status_collector.h"
#include "config_manager.h"
#include "esp_log.h"
#include "esp_err.h"
#include "nvs_flash.h"
#include <string.h>
#include <inttypes.h>

static const char* TAG = "G_MODE";

static bool g_initialized = false;
static bool g_running = false;
static char current_promo_text[MAX_PROMO_TEXT_LENGTH + 1] = {0};

/**
 * Form submission handler for portal forms
 */
static void portal_form_callback(const char* form_data, size_t length)
{
    ESP_LOGI(TAG, "Form submission received: %.*s", (int)length, form_data);
    /* Form data handling would go here (email capture, etc.) */
}

esp_err_t g_mode_init(void)
{
    if (g_initialized) {
        ESP_LOGW(TAG, "G mode already initialized");
        return ESP_OK;
    }

    ESP_LOGI(TAG, "Initializing G mode");

    /* Load configuration */
    DeviceConfig config;
    memcpy(&config, get_config(), sizeof(DeviceConfig));

    /* Store promotion text */
    strncpy(current_promo_text, config.promo_text, MAX_PROMO_TEXT_LENGTH);
    current_promo_text[MAX_PROMO_TEXT_LENGTH] = '\0';

    g_initialized = true;

    ESP_LOGI(TAG, "G mode initialized successfully");

    return ESP_OK;
}

esp_err_t g_mode_deinit(void)
{
    if (!g_initialized) {
        return ESP_OK;
    }

    /* Stop if currently running */
    if (g_running) {
        g_mode_stop();
    }

    g_initialized = false;

    ESP_LOGI(TAG, "G mode deinitialized");

    return ESP_OK;
}

esp_err_t g_mode_start(const BleManGattConfig* config)
{
    esp_err_t ret;

    if (!g_initialized) {
        ESP_LOGE(TAG, "G mode not initialized");
        return ESP_ERR_INVALID_STATE;
    }

    if (g_running) {
        ESP_LOGW(TAG, "G mode already running");
        return ESP_OK;
    }

    ESP_LOGI(TAG, "Starting G mode services");

    /* Load configuration */
    DeviceConfig dev_config;
    memcpy(&dev_config, get_config(), sizeof(DeviceConfig));

    /* Initialize WiFi Access Point */
    ret = init_wifi_ap(dev_config.promo_text,
                       dev_config.wifi_encrypted ? dev_config.wifi_password : NULL);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "WiFi AP init failed: %s", esp_err_to_name(ret));
        return ret;
    }

    /* Initialize DNS server */
    ret = init_dns_server();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "DNS server init failed: %s", esp_err_to_name(ret));
        stop_wifi_ap();
        return ret;
    }

    /* Initialize HTTP server */
    ret = init_http_server();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "HTTP server init failed: %s", esp_err_to_name(ret));
        stop_dns_server();
        stop_wifi_ap();
        return ret;
    }

    /* Register form callback */
    register_form_callback(portal_form_callback);

    /* Update BLE advertising name via ble_manager */
    ret = update_ble_advertising_name(dev_config.promo_text);
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "BLE advertising update failed: %s", esp_err_to_name(ret));
        /* Non-fatal, continue without BLE update */
    }
    /* NOTE: init_status_collector() is called once in main.c — not repeated here */

    g_running = true;

    ESP_LOGI(TAG, "G mode started successfully");
    ESP_LOGI(TAG, "AP SSID: %s", dev_config.promo_text);

    return ESP_OK;
}

esp_err_t g_mode_stop(void)
{
    if (!g_running) {
        return ESP_OK;
    }

    ESP_LOGI(TAG, "Stopping G mode services");

    /* Stop HTTP server */
    stop_http_server();

    /* Stop DNS server */
    stop_dns_server();

    /* Stop WiFi AP */
    stop_wifi_ap();

    g_running = false;

    ESP_LOGI(TAG, "G mode stopped");

    return ESP_OK;
}

bool g_mode_is_active(void)
{
    return g_initialized && g_running;
}

bool g_mode_is_running(void)
{
    return g_running;
}

esp_err_t g_mode_update_promotion_text(const char* promotion_text)
{
    if (!promotion_text) {
        return ESP_ERR_INVALID_ARG;
    }

    /* Enforce length limit */
    size_t len = strlen(promotion_text);
    if (len > MAX_PROMO_TEXT_LENGTH) {
        len = MAX_PROMO_TEXT_LENGTH;
    }

    /* Update local copy */
    strncpy(current_promo_text, promotion_text, len);
    current_promo_text[len] = '\0';

    /* Save to persistent storage */
    esp_err_t ret = save_promo_text(current_promo_text);
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "Failed to save promo text: %s", esp_err_to_name(ret));
    }

    ESP_LOGI(TAG, "Promotion text updated: %s", current_promo_text);

    return ESP_OK;
}

esp_err_t g_mode_update_ssid(const char* new_ssid)
{
    if (!new_ssid) {
        return ESP_ERR_INVALID_ARG;
    }

    /* Enforce SSID length limit */
    size_t len = strlen(new_ssid);
    if (len == 0 || len > 32) {
        ESP_LOGE(TAG, "SSID must be 1-32 characters");
        return ESP_ERR_INVALID_ARG;
    }

    ESP_LOGI(TAG, "Updating SSID to: %s", new_ssid);

    /* Update WiFi AP SSID */
    esp_err_t ret = update_ap_ssid(new_ssid);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to update AP SSID: %s", esp_err_to_name(ret));
        return ret;
    }

    /* Save to persistent storage */
    ret = save_ssid(new_ssid);
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "Failed to save SSID: %s", esp_err_to_name(ret));
    }

    /* Update BLE advertising name to match new SSID */
    ret = update_ble_advertising_name(new_ssid);
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "Failed to update BLE name: %s", esp_err_to_name(ret));
        /* Non-fatal, continue */
    }

    ESP_LOGI(TAG, "SSID updated successfully: %s", new_ssid);

    return ESP_OK;
}

esp_err_t g_mode_update_portal_html(const char* html_content, size_t length)
{
    if (!html_content || length == 0) {
        return ESP_ERR_INVALID_ARG;
    }

    if (length > MAX_PORTAL_HTML_SIZE) {
        ESP_LOGE(TAG, "HTML content too large: %zu (max %d)",
                 length, MAX_PORTAL_HTML_SIZE);
        return ESP_ERR_INVALID_SIZE;
    }

    /* Update HTTP server content */
    esp_err_t ret = set_portal_content(html_content, length);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to set portal content: %s", esp_err_to_name(ret));
        return ret;
    }

    /* Save to persistent storage */
    ret = save_portal_html(html_content, length);
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "Failed to save portal HTML: %s", esp_err_to_name(ret));
    }

    ESP_LOGI(TAG, "Portal HTML updated: %zu bytes", length);

    return ESP_OK;
}

uint8_t g_mode_get_client_count(void)
{
    return get_connected_client_count();
}

uint8_t g_mode_get_portal_engagement_time(void)
{
    return get_portal_engagement_time();
}

/* ============================================================================
 * LEGACY COMPATIBILITY WRAPPERS
 * ============================================================================ */

esp_err_t init_g_mode(void)
{
    esp_err_t ret = g_mode_init();
    if (ret != ESP_OK) {
        return ret;
    }

    return g_mode_start(NULL);
}

void cleanup_g_mode(void)
{
    g_mode_stop();
    g_mode_deinit();
}

bool is_g_mode_active(void)
{
    return g_mode_is_active();
}

esp_err_t update_promotion_text(const char* promotion_text)
{
    return g_mode_update_promotion_text(promotion_text);
}

esp_err_t update_portal_html(const char* html_content, size_t length)
{
    return g_mode_update_portal_html(html_content, length);
}

uint8_t get_client_count(void)
{
    return g_mode_get_client_count();
}


/**
 * Integration Example: GDPR-Compliant Captive Portal
 * 
 * This file demonstrates how to integrate the GDPR-compliant captive portal
 * into the main PromoBeacon application.
 * 
 * Features demonstrated:
 * - Portal initialization with store configuration
 * - HTTP server setup for captive portal
 * - Form submission handling
 * - Unsubscribe endpoint integration
 * - Compliance metrics monitoring
 * 
 * Author: MiniMax Agent
 * Version: 2.0.0
 */

/* ============================================================================
 * EXAMPLE 1: Basic Setup in main.c
 * ============================================================================ */

/*
#include "captive_portal.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "nvs_flash.h"

#define STORE_NAME "MainStreetShop"
#define PROMO_TEXT "10% OFF on your first purchase!"
#define DATA_CONTROLLER_EMAIL "privacy@mainstreetshop.com"

void setup() {
    Serial.begin(115200);
    
    // Initialize NVS (required for WiFi)
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        ret = nvs_flash_init();
    }
    
    // Initialize TCP/IP adapter
    tcpip_adapter_init();
    
    // Initialize event loop
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    
    // Initialize WiFi in AP mode
    wifi_init_config_t wifi_init_config = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&wifi_init_config));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));
    
    // Configure WiFi AP
    wifi_config_t wifi_config = {
        .ap = {
            .ssid = STORE_NAME,
            .ssid_len = strlen(STORE_NAME),
            .channel = 1,
            .authmode = WIFI_AUTH_OPEN,
            .max_connection = 6,
        },
    };
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());
    
    // Configure IP address
    tcpip_adapter_ip_info_t ip_info;
    IP4_ADDR(&ip_info.ip, 192, 168, 4, 1);
    IP4_ADDR(&ip_info.gw, 192, 168, 4, 1);
    IP4_ADDR(&ip_info.netmask, 255, 255, 255, 0);
    tcpip_adapter_set_ap_ip_info(TCPIP_ADAPTER_IF_AP, &ip_info);
    
    // Start DHCP server
    tcpip_adapter_dhcps_start(TCPIP_ADAPTER_IF_AP);
    
    // Configure portal
    PortalConfig config = {
        .store_name = STORE_NAME,
        .promo_text = PROMO_TEXT,
        .data_controller_email = DATA_CONTROLLER_EMAIL,
        .privacy_policy_url = "/privacy",
        .require_consent_for_email = true
    };
    
    // Initialize captive portal
    ret = init_captive_portal(&config);
    if (ret != ESP_OK) {
        Serial.println("Failed to initialize captive portal");
        return;
    }
    
    // Start captive portal servers
    ret = start_captive_portal();
    if (ret != ESP_OK) {
        Serial.println("Failed to start captive portal");
        return;
    }
    
    Serial.println("Captive portal started successfully");
    Serial.println("Connect to WiFi and open any website to see the portal");
}
*/

#include "captive_portal.h"
#include "esp_log.h"
#include "esp_err.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "nvs_flash.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <string.h>

/* Tag for logging */
static const char* TAG = "INTEGRATION";

/* Configuration */
#define STORE_NAME "MainStreetShop"
#define PROMO_TEXT "10% OFF on your first purchase!"
#define DATA_CONTROLLER_EMAIL "privacy@mainstreetshop.com"

/* Global state */
static bool portal_initialized = false;

/* ============================================================================
 * EXAMPLE 2: Complete Application Integration
 * ============================================================================ */

/**
 * @brief Initialize all application components
 */
static esp_err_t app_initialize(void)
{
    esp_err_t ret;
    
    /* Initialize NVS */
    ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGE(TAG, "Erasing NVS flash...");
        ret = nvs_flash_erase();
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "NVS erase failed: %s", esp_err_to_name(ret));
            return ret;
        }
        ret = nvs_flash_init();
    }
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS init failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    /* Initialize TCP/IP adapter */
    ret = tcpip_adapter_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "TCPIP adapter init failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    /* Initialize event loop */
    ret = esp_event_loop_create_default();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Event loop create failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    /* Initialize WiFi */
    wifi_init_config_t wifi_init_config = WIFI_INIT_CONFIG_DEFAULT();
    ret = esp_wifi_init(&wifi_init_config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "WiFi init failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    ret = esp_wifi_set_mode(WIFI_MODE_AP);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "WiFi mode set failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    /* Configure WiFi AP */
    wifi_config_t wifi_config = {
        .ap = {
            .ssid = "",
            .ssid_len = 0,
            .channel = 1,
            .authmode = WIFI_AUTH_OPEN,
            .max_connection = 6,
        },
    };
    
    strncpy((char*)wifi_config.ap.ssid, STORE_NAME, 32);
    wifi_config.ap.ssid_len = strlen(STORE_NAME);
    
    ret = esp_wifi_set_config(WIFI_IF_AP, &wifi_config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "WiFi config failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    ret = esp_wifi_start();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "WiFi start failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    /* Configure IP address */
    tcpip_adapter_ip_info_t ip_info;
    IP4_ADDR(&ip_info.ip, 192, 168, 4, 1);
    IP4_ADDR(&ip_info.gw, 192, 168, 4, 1);
    IP4_ADDR(&ip_info.netmask, 255, 255, 255, 0);
    
    ret = tcpip_adapter_set_ap_ip_info(TCPIP_ADAPTER_IF_AP, &ip_info);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "IP info set failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    /* Start DHCP server */
    ret = tcpip_adapter_dhcps_start(TCPIP_ADAPTER_IF_AP);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "DHCP start failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    ESP_LOGI(TAG, "WiFi AP started: SSID=%s", STORE_NAME);
    ESP_LOGI(TAG, "AP IP: 192.168.4.1");
    
    return ESP_OK;
}

/**
 * @brief Initialize the GDPR-compliant captive portal
 */
static esp_err_t app_init_captive_portal(void)
{
    PortalConfig config = {
        .store_name = STORE_NAME,
        .promo_text = PROMO_TEXT,
        .data_controller_email = DATA_CONTROLLER_EMAIL,
        .privacy_policy_url = "/privacy",
        .require_consent_for_email = true
    };
    
    /* Initialize portal with configuration */
    esp_err_t ret = init_captive_portal(&config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Portal init failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    /* Start portal servers */
    ret = start_captive_portal();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Portal start failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    portal_initialized = true;
    
    ESP_LOGI(TAG, "GDPR-compliant captive portal started");
    ESP_LOGI(TAG, "Portal URL: http://192.168.4.1/");
    
    return ESP_OK;
}

/**
 * @brief Print compliance metrics (for debugging/admin)
 */
static void app_print_metrics(void)
{
    ComplianceMetrics metrics;
    esp_err_t ret = get_compliance_metrics(&metrics);
    
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to get metrics: %s", esp_err_to_name(ret));
        return;
    }
    
    ESP_LOGI(TAG, "=== Compliance Metrics ===");
    ESP_LOGI(TAG, "Total emails collected: %u", metrics.total_emails_collected);
    ESP_LOGI(TAG, "Total unsubscribes: %u", metrics.total_unsubscribes);
    ESP_LOGI(TAG, "Last consent timestamp: %lu", metrics.last_consent_timestamp);
    ESP_LOGI(TAG, "Storage used: %u bytes", metrics.storage_used_bytes);
    ESP_LOGI(TAG, "Storage available: %u bytes", metrics.storage_available_bytes);
    ESP_LOGI(TAG, "Storage full: %s", metrics.storage_full ? "YES" : "NO");
}

/**
 * @brief Handle configuration update from BLE or other source
 */
static esp_err_t app_update_promo(const char* new_promo)
{
    if (!new_promo || strlen(new_promo) == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    
    esp_err_t ret = update_promo_text(new_promo);
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "Promo updated: %s", new_promo);
    }
    
    return ret;
}

/**
 * @brief Handle unsubscribe request from external source
 */
static esp_err_t app_handle_unsubscribe_request(const char* email)
{
    if (!email || strlen(email) == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    
    esp_err_t ret = handle_unsubscribe(email);
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "Unsubscribe processed: %s", email);
    } else if (ret == ESP_ERR_NOT_FOUND) {
        ESP_LOGW(TAG, "Email not found for unsubscribe: %s", email);
    } else {
        ESP_LOGE(TAG, "Unsubscribe failed: %s", esp_err_to_name(ret));
    }
    
    return ret;
}

/**
 * @brief Example main application entry point
 */
extern "C" void app_main(void)
{
    ESP_LOGI(TAG, "PromoBeacon GDPR Portal Starting...");
    
    /* Initialize all components */
    esp_err_t ret = app_initialize();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "App initialization failed");
        return;
    }
    
    /* Initialize and start captive portal */
    ret = app_init_captive_portal();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Captive portal initialization failed");
        return;
    }
    
    /* Print initial metrics */
    app_print_metrics();
    
    ESP_LOGI(TAG, "=== System Ready ===");
    ESP_LOGI(TAG, "1. Connect to WiFi: %s", STORE_NAME);
    ESP_LOGI(TAG, "2. Open any website");
    ESP_LOGI(TAG, "3. You will see the GDPR-compliant captive portal");
    ESP_LOGI(TAG, "4. Email signup is OPTIONAL and requires consent");
    
    /* Main event loop */
    uint32_t loop_count = 0;
    
    while (1) {
        vTaskDelay(pdMS_TO_TICKS(1000));
        
        loop_count++;
        
        /* Print metrics every 5 minutes for monitoring */
        if (loop_count % 300 == 0) {
            app_print_metrics();
        }
        
        /* Check if portal is still active */
        if (!is_captive_portal_active()) {
            ESP_LOGW(TAG, "Captive portal stopped, attempting restart...");
            start_captive_portal();
        }
    }
}

/* ============================================================================
 * EXAMPLE 3: BLE Integration Callbacks
 * ============================================================================ */

/*
 * When integrating with BLE control app, add these callbacks:
 */

/*
void on_mode_written(uint8_t mode) {
    if (mode == MODE_G) {
        // Switch to G mode - start captive portal
        start_captive_portal();
    } else if (mode == MODE_E) {
        // Switch to E mode - stop captive portal
        stop_captive_portal();
    }
}

void on_config_updated(uint8_t* data, size_t len) {
    if (len > 0 && data[0] == CONFIG_TYPE_PROMO) {
        // Update promotion text
        char new_promo[64];
        memcpy(new_promo, &data[1], len - 1);
        new_promo[len - 1] = '\0';
        app_update_promo(new_promo);
    }
}

void on_status_request(uint8_t* buffer, size_t* len) {
    ComplianceMetrics metrics;
    get_compliance_metrics(&metrics);
    
    // Pack metrics into buffer for BLE transmission
    buffer[0] = metrics.total_emails_collected & 0xFF;
    buffer[1] = (metrics.total_emails_collected >> 8) & 0xFF;
    buffer[2] = metrics.total_unsubscribes & 0xFF;
    buffer[3] = (metrics.total_unsubscribes >> 8) & 0xFF;
    *len = 4;
}
*/

/* ============================================================================
 * EXAMPLE 4: Arduino Framework Integration
 * ============================================================================ */

/*
For Arduino framework, use this pattern:

#include <WiFi.h>
#include <WebServer.h>
#include "captive_portal.h"

WebServer server(80);

void setup() {
    Serial.begin(115200);
    
    // Start WiFi AP
    WiFi.softAP(STORE_NAME);
    IPAddress IP = WiFi.softAPIP();
    Serial.print("AP IP: ");
    Serial.println(IP);
    
    // Initialize portal
    PortalConfig config = {
        .store_name = STORE_NAME,
        .promo_text = PROMO_TEXT,
        .data_controller_email = DATA_CONTROLLER_EMAIL,
        .privacy_policy_url = "/privacy",
        .require_consent_for_email = true
    };
    
    init_captive_portal(&config);
    start_captive_portal();
    
    // Register server handlers
    server.on("/", HTTP_GET, []() {
        root_handler(NULL);  // Adapt to Arduino style
    });
    
    server.on("/connect", HTTP_POST, []() {
        String postBody = server.arg("plain");
        // Process form...
    });
    
    server.begin();
}

void loop() {
    server.handleClient();
    vTaskDelay(pdMS_TO_TICKS(10));
}
*/

/* ============================================================================
 * EXAMPLE 5: Testing Checklist
 * ============================================================================ */

/*
Compliance Testing Checklist:
================================

[ ] WiFi Welcome Message
    - [ ] Welcome section displays without email requirement
    - [ ] Clear message that WiFi access is free

[ ] Optional Email Signup
    - [ ] Email input field is present
    - [ ] Submit button works without entering email
    - [ ] Form can be skipped entirely

[ ] Consent Checkbox (CRITICAL)
    - [ ] Checkbox is UNTICKED by default
    - [ ] Checkbox label clearly states marketing content
    - [ ] Submitting with email but NO checkbox shows error
    - [ ] Error message: "Consent required"

[ ] Privacy Policy
    - [ ] Link opens /privacy endpoint
    - [ ] English version displays correctly
    - [ ] Policy includes all required sections:
        * Data controller identity
        * Data collected
        * Legal basis
        * Retention period
        * User rights
        * Unsubscribe method
        * Complaint procedure

[ ] Form Submission
    - [ ] Valid email + consent = stored with timestamp
    - [ ] Invalid email format = error message
    - [ ] Success page displays with unsubscribe link
    - [ ] Success page shows email address

[ ] Unsubscribe
    - [ ] Unsubscribe page accessible
    - [ ] Email input validates format
    - [ ] Valid email = removed from storage
    - [ ] Success confirmation displayed
    - [ ] Invalid email = appropriate error

[ ] Storage
    - [ ] Emails stored in NVS
    - [ ] Timestamps recorded
    - [ ] Unsubscribe counter increments
    - [ ] Storage limits respected

[ ] Captive Portal Detection
    - [ ] iOS: /hotspot-detect.html redirects to portal
    - [ ] Android: /generate_204 shows portal
    - [ ] Windows: /ncsi.txt shows portal
    - [ ] All browsers redirect to portal

[ ] Mobile Responsiveness
    - [ ] Portal displays correctly on mobile
    - [ ] Form is usable on small screens
    - [ ] Privacy policy readable on mobile
*/

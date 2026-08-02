/**
 * PromoBeacon ESP32 - Main Application Entry Point
 *
 * G Mode retail promotion platform featuring:
 * - WiFi Access Point with captive portal + BLE advertising
 *
 * Architecture:
 * - ble_manager: Persistent BLE GATT service for configuration
 * - g_mode: WiFi AP, DNS server, HTTP server
 *
 * Hardware: ESP32-WROOM-32 or ESP32-S3 variant
 * Framework: ESP-IDF via PlatformIO
 *
 * Author: MiniMax Agent
 * Version: 3.0.0
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_system.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_bt.h"
#include "esp_mac.h"
#include "esp_wifi.h"
// #include "esp_adc_cal.h" - Migrated to status_collector.c
#include "nvs_flash.h"
#include "esp_netif.h"
#include "esp_ota_ops.h"
#include "esp_partition.h"
#include "driver/gpio.h"

#include "g_mode.h"
#include "ble_manager.h"
#include "wifi_manager.h"
#include "web_server.h"
#include "status_collector.h"
#include "config_manager.h"
#include "ota_update.h"
#include "client_tracker.h"
#include "portal_content.h"

/* Tag for ESP_LOG output */
static const char *TAG = "MAIN";

/* Event group bits for synchronization */
#define WIFI_CONNECTED_BIT      BIT0
#define BLE_CONNECTED_BIT       BIT1

static EventGroupHandle_t system_event_group = NULL;

/* Battery monitoring is now handled by status_collector.c */

/**
 * @brief Global mode change callback
 *
 * Called by ble_manager when mode changes via BLE command.
 * This allows main.c to perform mode-specific startup/shutdown.
 */
static void on_mode_change(DeviceMode new_mode, DeviceMode old_mode)
{
    ESP_LOGI(TAG, "Mode change callback: %d -> %d", old_mode, new_mode);

    /* Mode-specific actions can be performed here if needed */
    /* Most mode control is handled internally by g_mode */
}

/**
 * @brief Global status update callback
 *
 * Called by ble_manager when status should be updated.
 */
static void on_status_update(const DeviceStatus* status)
{
    /* Status is automatically updated by ble_manager */
    /* Additional actions can be performed here if needed */
}

/**
 * @brief Initialize ADC for battery monitoring
 */
static void init_battery_adc(void)
{
    /* Battery monitoring is handled by status_collector in this version */
    ESP_LOGI(TAG, "Battery ADC monitoring prepared");
}

/**
 * @brief Global event handler for system events
 */
static void global_event_handler(void* arg, esp_event_base_t event_base,
                                 int32_t event_id, void* event_data)
{
    if (event_base == WIFI_EVENT) {
        switch (event_id) {
            case WIFI_EVENT_AP_STACONNECTED: {
                wifi_event_ap_staconnected_t* conn =
                    (wifi_event_ap_staconnected_t*)event_data;
                ESP_LOGI(TAG, "Station connected: AID=%d, MAC=" MACSTR,
                         conn->aid, MAC2STR(conn->mac));
                on_client_connected(conn->mac);
                
                /* Track client connection */
                tracker_on_connect(conn->mac);
                break;
            }

            case WIFI_EVENT_AP_STADISCONNECTED: {
                wifi_event_ap_stadisconnected_t* disconn =
                    (wifi_event_ap_stadisconnected_t*)event_data;
                ESP_LOGI(TAG, "Station disconnected: AID=%d, MAC=" MACSTR,
                         disconn->aid, MAC2STR(disconn->mac));
                on_client_disconnected(disconn->mac);
                
                /* Track client disconnection */
                tracker_on_disconnect(disconn->mac);
                break;
            }

            default:
                break;
        }
    } else if (event_base == IP_EVENT) {
        if (event_id == IP_EVENT_ASSIGNED_IP_TO_CLIENT) {
            xEventGroupSetBits(system_event_group, WIFI_CONNECTED_BIT);
        }
    }
}

/**
 * @brief Get battery percentage
 */
uint8_t get_battery_percent(void)
{
    /* Bridge to the new status collector implementation */
    return get_battery_level();
}

/**
 * @brief Main application entry point
 */
void app_main(void)
{
    esp_err_t ret;

    /* Initialize Status LED
     * NOTE: On ESP32-C3 DevKitM-1, GPIO8 is a boot strapping pin.
     * Setting it as OUTPUT can interfere with boot. Skip on C3. */
#ifndef CONFIG_IDF_TARGET_ESP32C3
    gpio_reset_pin(STATUS_LED_PIN);
    gpio_set_direction(STATUS_LED_PIN, GPIO_MODE_OUTPUT);
    gpio_set_level(STATUS_LED_PIN, 0);
#endif

    ESP_LOGI(TAG, "==================================================");
    ESP_LOGI(TAG, "PromoBeacon firmware starting on %s", DEVICE_CHIP_NAME);
    ESP_LOGI(TAG, "==================================================");

    /* Initialize NVS (required for WiFi) */
    ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGE(TAG, "NVS flash error, erasing...");
        nvs_flash_erase();
        ret = nvs_flash_init();
    }
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS flash init failed: %s", esp_err_to_name(ret));
        return;
    }

    /* Initialize TCP/IP stack */
    esp_netif_init();

    /* Create event group for synchronization */
    system_event_group = xEventGroupCreate();
    if (!system_event_group) {
        ESP_LOGE(TAG, "Failed to create event group");
        return;
    }

    /* Register event handlers */
    ret = esp_event_loop_create_default();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Event loop create failed: %s", esp_err_to_name(ret));
        return;
    }

    ret = esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID,
                                      &global_event_handler, NULL);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "WIFI event handler registration failed: %s", esp_err_to_name(ret));
    }

    ret = esp_event_handler_register(IP_EVENT, ESP_EVENT_ANY_ID,
                                      &global_event_handler, NULL);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "IP event handler registration failed: %s", esp_err_to_name(ret));
    }
    /* Note: Bluetooth events are handled via native callbacks in ble_manager.c */

    /* Initialize battery ADC */
    init_battery_adc();

    /* Initialize configuration manager */
    init_config_manager();

    /* Initialize OTA update subsystem (must be after NVS) */
    ota_init();

    /* Initialize client tracker (must be after NVS) */
    tracker_init();

    /* Initialize portal content manager (must be before G-Mode) */
    portal_content_init();

    /* Initialize status collector */
    init_status_collector();

#ifdef PROMOBEACON_QEMU
    /* QEMU does not emulate the BLE radio or WiFi RF. NimBLE controller init
     * and WiFi PHY init both busy-wait on hardware interrupts that never fire
     * under emulation, so skip them. Config/portal/tracker/status logic and
     * the main loop remain fully testable. */
    ESP_LOGW(TAG, "QEMU mode: BLE + WiFi disabled (no emulated radio)");
    ESP_LOGI(TAG, "PromoBeacon ESP32 started successfully (QEMU)");
    ESP_LOGI(TAG, "Free heap size: %" PRIu32 " bytes", (uint32_t)esp_get_free_heap_size());
    ESP_LOGI(TAG, "Current mode: G (simulated)");
#else
    /* Initialize BLE manager FIRST so NimBLE stack is ready */
    ret = init_ble_manager();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "BLE manager init failed: %s", esp_err_to_name(ret));
        return;
    }

    /* Register callbacks with ble_manager */
    ble_register_mode_change_callback(on_mode_change);
    ble_register_status_callback(on_status_update);

    /* Initialize G-Mode modules and START services automatically */
    /* BLE must be up first so g_mode can update advertising name */
    ret = init_g_mode();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "G-Mode auto-start failed: %s", esp_err_to_name(ret));
        return;
    }
#endif /* PROMOBEACON_QEMU */

    /* BLE manager handles configuration */
    /* Default mode is G mode */

    /* Mark firmware as valid to prevent rollback (must be after all init) */
    ota_mark_valid();

#ifndef PROMOBEACON_QEMU
    ESP_LOGI(TAG, "PromoBeacon ESP32 started successfully");
    ESP_LOGI(TAG, "Free heap size: %" PRIu32 " bytes", (uint32_t)esp_get_free_heap_size());
    ESP_LOGI(TAG, "Current mode: %s", is_g_mode_active() ? "G" : "E");
#endif

    /* Main event loop */
    TickType_t last_wake_time = xTaskGetTickCount();
    uint32_t loop_counter = 0;

    while (1) {
        /* Check for BLE connection events */
        (void)xEventGroupWaitBits(system_event_group,
                                  BLE_CONNECTED_BIT,
                                  pdTRUE, pdFALSE, 0);

        /* Mode-specific handling based on current mode */
        if (is_g_mode_active()) {
            /* Handle HTTP requests (managed by ESP-HTTP server task) */
            handle_http_requests();
        } else {
            /* E mode placeholder — future implementation */
        }

        /* Update status every second (100 * 10ms) */
        if (++loop_counter >= 100) {
            update_status();

#ifdef PROMOBEACON_QEMU
            /* QEMU test aid: log status once per minute so boot/liveness is
             * observable in the emulator (production builds stay silent). */
            static uint32_t qemu_status_log = 0;
            if (++qemu_status_log >= 60) {
                const StatusPacket* st = get_status();
                ESP_LOGI(TAG, "QEMU status: uptime=%us clients=%u flags=0x%02x battery=%u%%",
                         (unsigned)(st->session_duration_sec),
                         (unsigned)st->client_count,
                         (unsigned)st->flags,
                         (unsigned)st->battery_percent);
                qemu_status_log = 0;
            }
#endif
            
            /* Check for timed out clients (10 minute timeout) */
            tracker_check_timeouts(600);
            
            /* Update tracker activity timestamp */
            tracker_update_activity();
            
            /* Save tracker state periodically (every 10 seconds) */
            if (loop_counter >= 1000) {
                tracker_save_to_nvs();
                tracker_mac_save_to_nvs();
                loop_counter = 0;
            }
        }

        /* Low-power status blink: 1 blue blink every 10 minutes */
        static uint32_t led_timer_counter = 0;
        if (++led_timer_counter >= 60000) {  /* 60,000 * 10ms = 600s = 10min */
            gpio_set_level(STATUS_LED_PIN, 1);
            vTaskDelay(pdMS_TO_TICKS(50));   /* Visible 50ms blink */
            gpio_set_level(STATUS_LED_PIN, 0);
            led_timer_counter = 0;
        }

        /* Watchdog-friendly delay (10ms tick) */
        vTaskDelayUntil(&last_wake_time, pdMS_TO_TICKS(10));
    }
}

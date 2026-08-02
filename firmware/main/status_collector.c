/**
 * Status Collector Implementation
 * 
 * Monitors and tracks device status including connected clients,
 * session duration, portal engagement time, and battery level.
 */

#include "status_collector.h"
#include "esp_log.h"
#include "esp_err.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_wifi.h"
#include "esp_mac.h"
#include <string.h>
#include <stdlib.h>
#include <inttypes.h>

static const char* TAG = "STATUS";

/* Status state */
static StatusPacket current_status;
static uint32_t session_start_time = 0;
static uint32_t total_portal_time = 0;
static uint32_t portal_session_count = 0;

/* Client tracking */
static client_info_t clients[MAX_TRACKED_CLIENTS];

/* Battery monitoring components */
static adc_oneshot_unit_handle_t adc_handle;
static adc_cali_handle_t cali_handle;
static bool cali_enabled = false;
static uint8_t last_battery_percent = 100;

/**
 * @brief Initialize status collector
 */
void init_status_collector(void)
{
    memset(&current_status, 0, sizeof(current_status));
    memset(clients, 0, sizeof(clients));
    
    session_start_time = xTaskGetTickCount() * portTICK_PERIOD_MS / 1000;
    total_portal_time = 0;
    portal_session_count = 0;

#ifdef PROMOBEACON_QEMU
    /* QEMU does not emulate the ADC peripheral (no SAR ADC hardware event
     * ever fires), so adc_oneshot_read() busy-waits forever and triggers an
     * interrupt watchdog panic. Skip hardware init and report 100% battery. */
    ESP_LOGW(TAG, "QEMU mode: ADC disabled (no emulated ADC), battery fixed at 100%%");
    cali_enabled = false;
    last_battery_percent = 100;
    ESP_LOGI(TAG, "Status collector initialized (QEMU mode, ADC skipped)");
    return;
#endif

    /* 1. Initialize ADC Unit */
    adc_oneshot_unit_init_cfg_t init_config = {
        .unit_id = ADC_UNIT_1,
        .ulp_mode = ADC_ULP_MODE_DISABLE,
    };
    esp_err_t ret = adc_oneshot_new_unit(&init_config, &adc_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "ADC unit init failed: %s", esp_err_to_name(ret));
        return;
    }

    /* 2. Configure Channel */
    adc_oneshot_chan_cfg_t config = {
        .bitwidth = ADC_BITWIDTH_DEFAULT,
        .atten = ADC_ATTEN_DB_12, /* C3 successor to 11dB */
    };
    ret = adc_oneshot_config_channel(adc_handle, ADC_CHANNEL_BATTERY, &config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "ADC channel config failed: %s", esp_err_to_name(ret));
        return;
    }

    /* 3. Initialize Calibration */
#if ADC_CALI_SCHEME_CURVE_FITTING_SUPPORTED
    adc_cali_curve_fitting_config_t cali_config = {
        .unit_id = ADC_UNIT_1,
        .chan = ADC_CHANNEL_BATTERY,
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    ret = adc_cali_create_scheme_curve_fitting(&cali_config, &cali_handle);
    if (ret == ESP_OK) {
        cali_enabled = true;
        ESP_LOGI(TAG, "ADC calibration initialized (Curve Fitting)");
    }
#elif ADC_CALI_SCHEME_LINE_FITTING_SUPPORTED
    adc_cali_line_fitting_config_t cali_config = {
        .unit_id = ADC_UNIT_1,
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    ret = adc_cali_create_scheme_line_fitting(&cali_config, &cali_handle);
    if (ret == ESP_OK) {
        cali_enabled = true;
        ESP_LOGI(TAG, "ADC calibration initialized (Line Fitting)");
    }
#endif
    
    /* Initialize battery reading */
    last_battery_percent = update_battery_percent();
    
    ESP_LOGI(TAG, "Status collector initialized (4MB Expansion Active)");
    ESP_LOGI(TAG, "Session start time: %" PRIu32, session_start_time);
}

/**
 * @brief Update status fields
 */
void update_status(void)
{
    uint32_t current_time = xTaskGetTickCount() * portTICK_PERIOD_MS / 1000;
    uint32_t session_seconds;
    if (current_time >= session_start_time) {
        session_seconds = current_time - session_start_time;
    } else {
        session_seconds = (UINT32_MAX - session_start_time) + current_time + 1;
    }
    
    /* Update flags */
    current_status.flags = 0x03;  /* Both AP and BLE active */
    
    /* Update client count from WiFi */
    wifi_sta_list_t sta_list;
    esp_wifi_ap_get_sta_list(&sta_list);
    current_status.client_count = sta_list.num;
    
    /* Update session duration (32-bit seconds since boot/mode start) */
    current_status.session_duration_sec = session_seconds;
    
    /* Calculate average portal time */
    if (portal_session_count > 0) {
        /* Cast to uint8_t saturates at 255 automatically — no extra check needed */
        uint32_t avg = total_portal_time / portal_session_count;
        current_status.portal_time_avg_sec = (avg > 255) ? 255 : (uint8_t)avg;
    }
    
    /* Update battery every 30 seconds */
    static uint32_t last_battery_update = 0;
    if (current_time - last_battery_update > 30) {
        current_status.battery_percent = update_battery_percent();
        last_battery_update = current_time;
    } else {
        current_status.battery_percent = last_battery_percent;
    }
}

/**
 * @brief Serialize status to buffer
 */
void serialize_status(uint8_t* buffer)
{
    if (!buffer) return;
    
    buffer[0] = current_status.flags;
    buffer[1] = current_status.client_count;
    buffer[2] = (uint8_t)(current_status.session_duration_sec & 0xFF);
    buffer[3] = (uint8_t)((current_status.session_duration_sec >> 8) & 0xFF);
    buffer[4] = (uint8_t)((current_status.session_duration_sec >> 16) & 0xFF);
    buffer[5] = (uint8_t)((current_status.session_duration_sec >> 24) & 0xFF);
    buffer[6] = current_status.portal_time_avg_sec;
    buffer[7] = current_status.battery_percent;
}

/**
 * @brief Get current status
 */
const StatusPacket* get_status(void)
{
    return &current_status;
}

/**
 * @brief Handle client connection
 */
void on_client_connected(const uint8_t* mac)
{
    if (!mac) return;
    
    /* Find available slot */
    int slot = -1;
    for (int i = 0; i < MAX_TRACKED_CLIENTS; i++) {
        if (!clients[i].active) {
            slot = i;
            break;
        }
    }
    
    if (slot < 0) {
        ESP_LOGW(TAG, "No available client slots");
        return;
    }
    
    /* Record connection */
    clients[slot].active = true;
    memcpy(clients[slot].mac, mac, 6);
    clients[slot].connect_time = xTaskGetTickCount() * portTICK_PERIOD_MS / 1000;
    clients[slot].portal_start_time = clients[slot].connect_time;
    
    ESP_LOGD(TAG, "Client connected: slot=%d, MAC=" MACSTR, slot, MAC2STR(mac));
}

/**
 * @brief Handle client disconnection
 */
void on_client_disconnected(const uint8_t* mac)
{
    uint32_t current_time = xTaskGetTickCount() * portTICK_PERIOD_MS / 1000;
    
    /* Find matching client */
    for (int i = 0; i < MAX_TRACKED_CLIENTS; i++) {
        if (clients[i].active && memcmp(clients[i].mac, mac, 6) == 0) {
            /* Calculate portal engagement time */
            uint32_t portal_time = current_time - clients[i].portal_start_time;
            total_portal_time += portal_time;
            portal_session_count++;
            
            /* Clear client record */
            clients[i].active = false;
            memset(clients[i].mac, 0, 6);
            
            ESP_LOGD(TAG, "Client disconnected: slot=%d, portal_time=%" PRIu32, i, portal_time);
            return;
        }
    }
}

/**
 * @brief Get session duration
 */
uint32_t get_session_duration(void)
{
    uint32_t current_time = xTaskGetTickCount() * portTICK_PERIOD_MS / 1000;
    return current_time - session_start_time;
}

/**
 * @brief Get average portal engagement time
 */
uint8_t get_portal_engagement_time(void)
{
    if (portal_session_count == 0) {
        return 0;
    }
    return (uint8_t)(total_portal_time / portal_session_count);
}

/**
 * @brief Get connected client count
 */
uint8_t get_connected_client_count(void)
{
    return current_status.client_count;
}

int get_current_wifi_client_count(void)
{
    wifi_sta_list_t sta_list;
    esp_err_t ret = esp_wifi_ap_get_sta_list(&sta_list);
    if (ret != ESP_OK) {
        return 0;
    }
    return sta_list.num;
}

/**
 * @brief Update and return battery percentage
 */
uint8_t update_battery_percent(void)
{
    if (!cali_enabled) {
        return 100;
    }
    
    /* Read ADC multiple times and average */
    int adc_raw;
    uint32_t adc_sum = 0;
    for (int i = 0; i < 8; i++) {
        esp_err_t err = adc_oneshot_read(adc_handle, ADC_CHANNEL_BATTERY, &adc_raw);
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "ADC read failed: %s", esp_err_to_name(err));
            return last_battery_percent;
        }
        adc_sum += adc_raw;
    }
    uint32_t adc_reading = adc_sum / 8;
    
    /* Convert to voltage (mV) */
    int voltage_mv = 0;
    if (cali_enabled) {
        esp_err_t err = adc_cali_raw_to_voltage(cali_handle, adc_reading, &voltage_mv);
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "ADC calibration failed: %s", esp_err_to_name(err));
            return last_battery_percent;
        }
    } else {
        /* Simple linear fallback if calibration fails */
        voltage_mv = (adc_reading * DEFAULT_VREF) / 4095;
    }
    
    /* Apply voltage divider compensation — 10:1 resistor divider: Vbat = Vadc_mv * 10 */
    uint32_t battery_voltage = voltage_mv * 10;
    
    /* Convert to percentage */
    /* Assuming: 4.2V = 100%, 3.2V = 0% */
    uint8_t percent;
    if (battery_voltage >= 4200) {
        percent = 100;
    } else if (battery_voltage <= 3200) {
        percent = 0;
    } else {
        percent = (uint8_t)((battery_voltage - 3200) / 10);
    }
    
    last_battery_percent = percent;
    
    ESP_LOGD(TAG, "Battery: %" PRIu32 " mV, %d%%", battery_voltage, percent);
    
    return percent;
}

uint8_t get_battery_level(void)
{
    return last_battery_percent;
}

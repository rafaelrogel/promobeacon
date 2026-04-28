/**
 * Status Collector Header
 * 
 * Defines the interface for device status monitoring.
 * Tracks connected clients, session duration, portal engagement,
 * and battery level with minimal memory overhead.
 */

#ifndef STATUS_COLLECTOR_H
#define STATUS_COLLECTOR_H

#include "sdkconfig.h"
#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Maximum tracked clients */
#define MAX_TRACKED_CLIENTS       6

/* Hardware configuration (Multi-Chip Support)
 * Automatically detects the ESP32 variant during compilation */
#if defined(CONFIG_IDF_TARGET_ESP32S3)
    #define ADC_CHANNEL_BATTERY   ADC_CHANNEL_6    /* GPIO7 on S3 */
    #define DEVICE_CHIP_NAME      "ESP32-S3"
    #define STATUS_LED_PIN        8                /* Standard LED */
    #define ADC_WIDTH_RES         ADC_BITWIDTH_12
#elif defined(CONFIG_IDF_TARGET_ESP32S2)
    #define ADC_CHANNEL_BATTERY   ADC_CHANNEL_6    /* GPIO7 on S2 */
    #define DEVICE_CHIP_NAME      "ESP32-S2"
    #define STATUS_LED_PIN        15               /* Standard LED */
    #define ADC_WIDTH_RES         ADC_BITWIDTH_13
#elif defined(CONFIG_IDF_TARGET_ESP32C3)
    #define ADC_CHANNEL_BATTERY   ADC_CHANNEL_4    /* GPIO4 on C3 */
    #define DEVICE_CHIP_NAME      "ESP32-C3"
    #define STATUS_LED_PIN        8                /* Blue LED on Super Mini */
    #define ADC_WIDTH_RES         ADC_BITWIDTH_12
#elif defined(CONFIG_IDF_TARGET_ESP32C2)
    #define ADC_CHANNEL_BATTERY   ADC_CHANNEL_4    /* GPIO4 on C2 */
    #define DEVICE_CHIP_NAME      "ESP32-C2"
    #define STATUS_LED_PIN        8                /* Standard LED */
    #define ADC_WIDTH_RES         ADC_BITWIDTH_12
#elif defined(CONFIG_IDF_TARGET_ESP32C6) || defined(CONFIG_IDF_TARGET_ESP32C61)
    #define ADC_CHANNEL_BATTERY   ADC_CHANNEL_4    /* GPIO4 on C6/C61 */
    #define DEVICE_CHIP_NAME      "ESP32-C6/C61"
    #define STATUS_LED_PIN        15               /* Standard LED */
    #define ADC_WIDTH_RES         ADC_BITWIDTH_12
#elif defined(CONFIG_IDF_TARGET_ESP32C5)
    #define ADC_CHANNEL_BATTERY   ADC_CHANNEL_4    /* GPIO4 on C5 */
    #define DEVICE_CHIP_NAME      "ESP32-C5"
    #define STATUS_LED_PIN        8                /* Standard LED */
    #define ADC_WIDTH_RES         ADC_BITWIDTH_12
#elif defined(CONFIG_IDF_TARGET_ESP32H2)
    #define ADC_CHANNEL_BATTERY   ADC_CHANNEL_4    /* GPIO5 on H2 */
    #define DEVICE_CHIP_NAME      "ESP32-H2"
    #define STATUS_LED_PIN        8                /* Standard LED */
    #define ADC_WIDTH_RES         ADC_BITWIDTH_12
#else
    #define ADC_CHANNEL_BATTERY   ADC_CHANNEL_6    /* Classic ESP32 */
    #define DEVICE_CHIP_NAME      "ESP32"
    #define STATUS_LED_PIN        2                /* Blue LED on DevKit V1 */
    #define ADC_WIDTH_RES         ADC_BITWIDTH_12
#endif

#define DEFAULT_VREF              1100             /* mV — Default reference voltage */

/**
 * @brief Device status structure (8 bytes for BLE transmission)
 */
typedef struct __attribute__((packed)) {
    uint8_t flags;                    /* Bit0: AP active, Bit1: BLE active, Bits2-7: reserved */
    uint8_t client_count;             /* 0-6 connected clients */
    uint32_t session_duration_sec;    /* Seconds since mode start (32-bit to avoid 18.2h wraparound) */
    uint8_t portal_time_avg_sec;      /* Average portal engagement time per client */
    uint8_t battery_percent;          /* 0-100 battery percentage */
} StatusPacket;

/**
 * @brief Client tracking structure
 */
typedef struct {
    bool active;                      /* Client connection active */
    uint8_t mac[6];                   /* Client MAC address */
    uint32_t connect_time;            /* Connection timestamp (seconds) */
    uint32_t portal_start_time;       /* Portal engagement start timestamp */
} client_info_t;

/**
 * @brief Initialize status collector
 * 
 * Initializes all tracking structures and resets counters.
 */
void init_status_collector(void);

/**
 * @brief Update status
 * 
 * Called periodically to update status fields.
 * Should be called from main loop every ~1 second.
 */
void update_status(void);

/**
 * @brief Serialize status to buffer
 * 
 * Packs the DeviceStatus structure into an 8-byte buffer
 * suitable for BLE transmission.
 * 
 * @param buffer Buffer to receive packed data (8 bytes minimum)
 */
void serialize_status(uint8_t* buffer);

/**
 * @brief Get current status
 * 
 * @return Pointer to current DeviceStatus structure
 */
const StatusPacket* get_status(void);

/**
 * @brief Notify client connected
 * 
 * Called when a WiFi client connects.
 * 
 * @param mac Client MAC address (6 bytes)
 */
void on_client_connected(const uint8_t* mac);

/**
 * @brief Notify client disconnected
 * 
 * Called when a WiFi client disconnects.
 * Updates portal engagement time tracking.
 * 
 * @param mac Client MAC address (6 bytes)
 */
void on_client_disconnected(const uint8_t* mac);

/**
 * @brief Get session duration in seconds
 * 
 * @return Seconds since current mode started
 */
uint32_t get_session_duration(void);

/**
 * @brief Get average portal engagement time
 * 
 * @return Average seconds clients spend on portal
 */
uint8_t get_portal_engagement_time(void);

/**
 * @brief Get connected client count
 * 
 * @return Number of active client connections
 */
uint8_t get_connected_client_count(void);

/**
 * @brief Get the actual number of connected WiFi clients directly from the driver
 * 
 * @return Number of connected clients, or 0 on error
 */
int get_current_wifi_client_count(void);

/**
 * @brief Force battery update
 * 
 * Immediately reads and updates the battery percentage.
 * Normally called periodically, but can be called on demand.
 * 
 * @return Current battery percentage (0-100)
 */
uint8_t update_battery_percent(void);

/**
 * @brief Get the last measured battery level
 * 
 * @return Last measured battery percentage (0-100)
 */
uint8_t get_battery_level(void);

#ifdef __cplusplus
}
#endif

#endif /* STATUS_COLLECTOR_H */

/**
 * WiFi Manager Header
 * 
 * Defines the interface for WiFi Access Point functionality.
 * Provides soft-AP configuration, DNS wildcard server,
 * and client management for the captive portal.
 */

#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include "esp_wifi_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/* WiFi configuration constants */
#define MAX_SSID_LENGTH           32
#define MAX_PASSWORD_LENGTH       64
#define MAX_CLIENT_CONNECTIONS    6
#define DEFAULT_AP_CHANNEL        1
#define DEFAULT_BEACON_INTERVAL   100

/* DNS server configuration */
#define DNS_SERVER_PORT           53
#define DNS_BUFFER_SIZE           512
#define DNS_DEFAULT_TTL           300

/* Soft-AP IP configuration */
#define AP_IP_ADDR                192, 168, 4, 1
#define AP_NETMASK                255, 255, 255, 0
#define DHCP_START_ADDR           192, 168, 4, 2
#define DHCP_END_ADDR             192, 168, 4, 6

/**
 * @brief WiFi AP configuration structure
 * Renamed to avoid conflict with ESP-IDF wifi_ap_config_t
 */
typedef struct {
    char ssid[MAX_SSID_LENGTH + 1];
    char password[MAX_PASSWORD_LENGTH + 1];
    bool encryption_enabled;
    uint8_t channel;
    uint16_t beacon_interval;
} pb_wifi_ap_config_t;

/**
 * @brief Initialize WiFi Access Point
 * 
 * Configures and starts the WiFi soft-AP with provided SSID.
 * No password means open network (no encryption).
 * 
 * @param ssid Access Point name (promotion text)
 * @param password Optional password (NULL for open network)
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t init_wifi_ap(const char* ssid, const char* password);

/**
 * @brief Stop WiFi Access Point
 * 
 * Stops the soft-AP and releases all associated resources.
 */
void stop_wifi_ap(void);

/**
 * @brief Reconfigure WiFi AP SSID
 * 
 * Updates the Access Point name while keeping other settings.
 * 
 * @param new_ssid New SSID to use
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t update_ap_ssid(const char* new_ssid);

/**
 * @brief Reconfigure WiFi AP password
 * 
 * Updates or removes the Access Point password.
 * 
 * @param new_password New password (NULL to disable encryption)
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t update_ap_password(const char* new_password);

/**
 * @brief Get connected client count
 * 
 * @return Number of currently connected WiFi clients
 */
uint8_t get_wifi_client_count(void);

/**
 * @brief Check if WiFi AP is active
 * 
 * @return true if Access Point is running
 */
bool is_wifi_ap_active(void);

/**
 * @brief Disconnect all connected clients
 *
 * Sends deauthentication frames to all connected stations,
 * forcing them to forget the network. This ensures clients
 * must manually reconnect on next access.
 *
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t disconnect_all_clients(void);

/**
 * @brief Initialize DNS wildcard server
 * 
 * Starts DNS server that resolves all queries to AP IP.
 * This enables the captive portal redirect functionality.
 * 
 * @return ESP_OK on success, error code otherwise
 */
esp_err_t init_dns_server(void);

/**
 * @brief Stop DNS server
 * 
 * Stops the DNS server and releases resources.
 */
void stop_dns_server(void);

/**
 * @brief Handle DNS server requests
 * 
 * Called from main loop to process pending DNS queries.
 * Non-blocking, processes all available queries.
 */
void handle_dns_requests(void);

/**
 * @brief Get AP IP address
 * 
 * @return Pointer to IP address structure
 */
const char* get_ap_ip_address(void);

#ifdef __cplusplus
}
#endif

#endif /* WIFI_MANAGER_H */

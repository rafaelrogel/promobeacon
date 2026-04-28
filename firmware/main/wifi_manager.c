#include "wifi_manager.h"
#include "esp_log.h"
#include "esp_err.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_mac.h"
#include "lwip/err.h"
#include "lwip/sockets.h"
#include "lwip/sys.h"
#include <lwip/netdb.h>
#include <inttypes.h>
#include <string.h>
#include <errno.h>

static const char* TAG = "WIFI_MGR";

/* WiFi AP state */
static bool wifi_ap_active = false;
static TaskHandle_t dns_task_handle = NULL;
static volatile bool dns_server_active = false;
static char ap_ssid[MAX_SSID_LENGTH + 1] = {0};
static char ap_password[MAX_PASSWORD_LENGTH + 1] = {0};
static bool encryption_enabled = false;
static esp_netif_t* ap_netif = NULL;

/* DNS server state */
static int dns_socket = -1;
static struct sockaddr_in dns_server_addr;
static esp_ip4_addr_t ap_ip_addr;

/* Forward declarations removed - using compact implementation */

esp_err_t init_wifi_ap(const char* ssid, const char* password)
{
    esp_err_t ret;
    
    if (wifi_ap_active) {
        ESP_LOGW(TAG, "WiFi AP already active");
        return ESP_OK;
    }
    
    if (!ssid || strlen(ssid) == 0) {
        ESP_LOGE(TAG, "Invalid SSID");
        return ESP_ERR_INVALID_ARG;
    }
    
    ESP_LOGI(TAG, "Initializing WiFi AP: %s", ssid);
    
    /* Netif initialization is handled by main.c */
    
    /* Create Netif default AP */
    ap_netif = esp_netif_create_default_wifi_ap();
    if (ap_netif == NULL) {
        ESP_LOGE(TAG, "Failed to create Netif AP");
        return ESP_FAIL;
    }

    /* Configure IP address */
    esp_netif_ip_info_t ip_info;
    memset(&ip_info, 0, sizeof(esp_netif_ip_info_t));
    IP4_ADDR(&ip_info.ip, AP_IP_ADDR);
    IP4_ADDR(&ip_info.gw, AP_IP_ADDR);
    IP4_ADDR(&ip_info.netmask, AP_NETMASK);
    
    esp_netif_dhcps_stop(ap_netif);
    ret = esp_netif_set_ip_info(ap_netif, &ip_info);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "IP info set failed: %s", esp_err_to_name(ret));
        return ret;
    }

    /* Set DHCP range to accommodate all clients */
    dhcps_lease_t lease;
    lease.enable = true;
    IP4_ADDR(&lease.start_ip, DHCP_START_ADDR);
    IP4_ADDR(&lease.end_ip, DHCP_END_ADDR);
    esp_netif_dhcps_option(ap_netif, ESP_NETIF_OP_SET, ESP_NETIF_IP_LEASE, &lease, sizeof(lease));

    esp_netif_dhcps_start(ap_netif);
    
    /* Store AP IP address for DNS server */
    ap_ip_addr = ip_info.ip;

    /* Store configuration */
    strncpy(ap_ssid, ssid, MAX_SSID_LENGTH);
    ap_ssid[MAX_SSID_LENGTH] = '\0';
    
    if (password && strlen(password) >= 8) {
        strncpy(ap_password, password, MAX_PASSWORD_LENGTH);
        ap_password[MAX_PASSWORD_LENGTH] = '\0';
        encryption_enabled = true;
    } else {
        ap_password[0] = '\0';
        encryption_enabled = false;
    }
    
    /* Initialize WiFi */
    wifi_init_config_t init_config = WIFI_INIT_CONFIG_DEFAULT();
    ret = esp_wifi_init(&init_config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "WiFi init failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    /* Event handler registration removed - handled by main.c */
    
    /* Configure WiFi */
    wifi_config_t wifi_config = {
        .ap = {
            .ssid = "",
            .ssid_len = 0,
            .channel = DEFAULT_AP_CHANNEL,
            .authmode = encryption_enabled ? WIFI_AUTH_WPA2_PSK : WIFI_AUTH_OPEN,
            .max_connection = MAX_CLIENT_CONNECTIONS,
            .beacon_interval = DEFAULT_BEACON_INTERVAL,
        },
    };
    
    memcpy(wifi_config.ap.ssid, ap_ssid, strlen(ap_ssid));
    wifi_config.ap.ssid_len = strlen(ap_ssid);
    
    if (encryption_enabled) {
        memcpy(wifi_config.ap.password, ap_password, strlen(ap_password));
    }
    
    /* Set WiFi mode to AP */
    ret = esp_wifi_set_mode(WIFI_MODE_AP);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "WiFi mode set failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    /* Apply configuration */
    ret = esp_wifi_set_config(WIFI_IF_AP, &wifi_config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "WiFi config set failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    /* Start WiFi */
    ret = esp_wifi_start();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "WiFi start failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    wifi_ap_active = true;
    
    ESP_LOGI(TAG, "WiFi AP started: %s (%s)", ap_ssid, 
             encryption_enabled ? "WPA2" : "OPEN");
    ESP_LOGI(TAG, "AP IP: " IPSTR, IP2STR(&ip_info.ip));
    
    return ESP_OK;
}

void stop_wifi_ap(void)
{
    if (!wifi_ap_active) {
        return;
    }
    
    ESP_LOGI(TAG, "Stopping WiFi AP");
    
    /* Stop WiFi */
    esp_wifi_stop();
    esp_wifi_deinit();
    
    if (ap_netif) {
        esp_netif_destroy_default_wifi(ap_netif);
        ap_netif = NULL;
    }

    /* Unregister event handler removed */
    
    wifi_ap_active = false;
    
    ESP_LOGI(TAG, "WiFi AP stopped");
}

esp_err_t update_ap_ssid(const char* new_ssid)
{
    if (!wifi_ap_active) {
        return ESP_ERR_INVALID_STATE;
    }
    
    if (!new_ssid || strlen(new_ssid) == 0 || strlen(new_ssid) > MAX_SSID_LENGTH) {
        return ESP_ERR_INVALID_ARG;
    }
    
    strncpy(ap_ssid, new_ssid, MAX_SSID_LENGTH);
    ap_ssid[MAX_SSID_LENGTH] = '\0';
    
    wifi_config_t wifi_config = {0};
    esp_err_t ret = esp_wifi_get_config(WIFI_IF_AP, &wifi_config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to get WiFi config: %s", esp_err_to_name(ret));
        return ret;
    }
    
    memcpy(wifi_config.ap.ssid, ap_ssid, strlen(ap_ssid));
    wifi_config.ap.ssid_len = strlen(ap_ssid);
    
    ret = esp_wifi_set_config(WIFI_IF_AP, &wifi_config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "SSID update failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    ESP_LOGI(TAG, "AP SSID updated: %s", ap_ssid);
    
    return ESP_OK;
}

esp_err_t update_ap_password(const char* new_password)
{
    if (!wifi_ap_active) {
        return ESP_ERR_INVALID_STATE;
    }
    
    wifi_config_t wifi_config = {0};
    esp_err_t ret = esp_wifi_get_config(WIFI_IF_AP, &wifi_config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to get WiFi config: %s", esp_err_to_name(ret));
        return ret;
    }
    
    if (new_password && strlen(new_password) >= 8) {
        strncpy(ap_password, new_password, MAX_PASSWORD_LENGTH);
        ap_password[MAX_PASSWORD_LENGTH] = '\0';
        encryption_enabled = true;
        wifi_config.ap.authmode = WIFI_AUTH_WPA2_PSK;
        memcpy(wifi_config.ap.password, ap_password, strlen(ap_password));
    } else {
        ap_password[0] = '\0';
        encryption_enabled = false;
        wifi_config.ap.authmode = WIFI_AUTH_OPEN;
        wifi_config.ap.password[0] = '\0';
    }
    
    ret = esp_wifi_set_config(WIFI_IF_AP, &wifi_config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Password update failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    ESP_LOGI(TAG, "AP password updated: %s", 
             encryption_enabled ? "enabled" : "disabled");
    
    return ESP_OK;
}

/* get_wifi_client_count removed - use get_current_wifi_client_count from status_collector.c */

bool is_wifi_ap_active(void)
{
    return wifi_ap_active;
}

esp_err_t disconnect_all_clients(void)
{
    if (!wifi_ap_active) {
        return ESP_ERR_INVALID_STATE;
    }
    
    /* In ESP-IDF 5.x, we reliably clear clients by restarting AP */
    esp_wifi_stop();
    esp_wifi_start();

    
    return ESP_OK;
}

/* DNS Server Implementation */

/* Old DNS implementation removed */

static void dns_server_task(void *pvParameters)
{
    ESP_LOGI(TAG, "DNS server task started");
    while (dns_server_active) {
        handle_dns_requests();
        vTaskDelay(pdMS_TO_TICKS(10)); // Yield to other tasks
    }
    ESP_LOGI(TAG, "DNS server task stopping");
    vTaskDelete(NULL);
}

esp_err_t init_dns_server(void)
{
    if (dns_server_active) {
        ESP_LOGW(TAG, "DNS server already active");
        return ESP_OK;
    }
    
    ESP_LOGI(TAG, "Initializing DNS server");
    
    /* Create DNS socket */
    dns_socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (dns_socket < 0) {
        ESP_LOGE(TAG, "DNS socket creation failed: %d", errno);
        return ESP_FAIL;
    }
    
    /* Set socket timeout */
    struct timeval timeout = { .tv_sec = 0, .tv_usec = 100000 }; 
    setsockopt(dns_socket, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
    
    /* Bind to port 53 */
    memset(&dns_server_addr, 0, sizeof(dns_server_addr));
    dns_server_addr.sin_family = AF_INET;
    dns_server_addr.sin_addr.s_addr = INADDR_ANY;
    dns_server_addr.sin_port = htons(DNS_SERVER_PORT);
    
    if (bind(dns_socket, (struct sockaddr*)&dns_server_addr, 
             sizeof(dns_server_addr)) < 0) {
        ESP_LOGE(TAG, "DNS socket bind failed: %d", errno);
        close(dns_socket);
        dns_socket = -1;
        return ESP_FAIL;
    }
    
    dns_server_active = true;
    
    /* Start DNS task */
    if (xTaskCreate(dns_server_task, "dns_server_task", 4096, NULL, 5, &dns_task_handle) != pdPASS) {
        ESP_LOGE(TAG, "Failed to create DNS task");
        close(dns_socket);
        dns_socket = -1;
        dns_server_active = false;
        return ESP_FAIL;
    }
    
    ESP_LOGI(TAG, "DNS wildcard server started on port %d", DNS_SERVER_PORT);
    
    return ESP_OK;
}

void stop_dns_server(void)
{
    if (!dns_server_active) { return; }
    
    dns_server_active = false;
    
    vTaskDelay(pdMS_TO_TICKS(100));
    
    if (dns_socket >= 0) {
        close(dns_socket);
        dns_socket = -1;
    }
    
    if (dns_task_handle != NULL) {
        vTaskDelete(dns_task_handle);
        dns_task_handle = NULL;
    }
}

void handle_dns_requests(void)
{
    if (!dns_server_active || dns_socket < 0) return;

    uint8_t buffer[DNS_BUFFER_SIZE];
    struct sockaddr_in client_addr;
    socklen_t client_len = sizeof(client_addr);

    ssize_t recv_len = recvfrom(dns_socket, buffer, sizeof(buffer), 0,
                                (struct sockaddr*)&client_addr, &client_len);

    if (recv_len < 12) return; // Min DNS header is 12 bytes
    
    ESP_LOGI(TAG, "DNS Query received (Len: %d)", (int)recv_len);

    /* DNS Query Mirroring Technique:
     * We reflect the original query back to the mobile device with 
     * the 'Answer' section appended. This is the most robust method for CP.
     */
     
    /* 1. Modify Header in place */
    buffer[2] |= 0x80; // Set QR bit (Response)
    buffer[3] |= 0x80; // Set RA bit (Recursion Available - optional)
    
    /* 2. Set Answer Count = 1, Auth/Add = 0 */
    buffer[6] = 0; buffer[7] = 1;  /* Answer RRs = 1 */
    buffer[8] = 0; buffer[9] = 0;  /* Authority RRs = 0 */
    buffer[10] = 0; buffer[11] = 0; /* Additional RRs = 0 */

    /* 3. Find the end of the Question section */
    uint8_t* ptr = buffer + 12; // Skip header
    while (ptr < buffer + recv_len && *ptr > 0) {
        ptr += (*ptr + 1);
    }
    ptr++; // Skip null terminator of labels
    ptr += 4; // Skip Type and Class (4 bytes)

    if (ptr + 16 > buffer + DNS_BUFFER_SIZE) return; // Prevention

    /* 4. Append Answer Section (Resource Record) */
    /* Name Pointer 0xC00C (Points back to query name at byte 12) */
    *ptr++ = 0xC0; *ptr++ = 0x0C;
    /* Type A (Host Address) */
    *ptr++ = 0x00; *ptr++ = 0x01;
    /* Class IN (Internet) */
    *ptr++ = 0x00; *ptr++ = 0x01;
    /* TTL (60 seconds) */
    *ptr++ = 0x00; *ptr++ = 0x00; *ptr++ = 0x00; *ptr++ = 0x3C;
    /* Data Length (4 bytes for IP) */
    *ptr++ = 0x00; *ptr++ = 0x04;
    /* IP from macro */
    uint8_t ip_bytes[] = { AP_IP_ADDR };
    *ptr++ = ip_bytes[0]; *ptr++ = ip_bytes[1]; *ptr++ = ip_bytes[2]; *ptr++ = ip_bytes[3];

    size_t response_len = ptr - buffer;
    sendto(dns_socket, buffer, response_len, 0,
           (struct sockaddr*)&client_addr, client_len);
}

const char* get_ap_ip_address(void)
{
    static char ip_str[16];
    snprintf(ip_str, sizeof(ip_str), IPSTR, IP2STR(&ap_ip_addr));
    return ip_str;
}

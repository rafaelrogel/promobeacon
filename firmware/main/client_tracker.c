/**
 * Client Tracker Implementation
 *
 * Tracks WiFi AP client connections, session durations, and HTTP request paths.
 * Data is persisted in NVS and exposed via BLE for mobile app access.
 *
 * Architecture:
 * - Active client tracking in RAM for current sessions
 * - Ring buffer history for last 100 sessions in NVS
 * - Bitmask-based path tracking to minimize memory usage
 * - BLE-compatible data serialization
 *
 * Author: MiniMax Agent
 * Version: 2.0.0
 */

#include "client_tracker.h"
#include "esp_log.h"
#include "esp_err.h"
#include "esp_timer.h"
#include "esp_mac.h"
#include "esp_wifi.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "esp_flash.h"
#include "esp_random.h"
#include <string.h>
#include "stdlib.h"
#include "esp_rom_crc.h"
#include <inttypes.h>
#include <time.h>

static const char* TAG = "CLIENT_TRACKER";

/* Magic number for NVS validation */
#define TRACKER_MAGIC_NUMBER        0x54424155  /* "TBAU" - Tracker Beacon Analytics */
#define TRACKER_VERSION             1

/* NVS key for MAC count table */
#define MAC_COUNT_NVS_KEY           "mac_counts"

/* Local static variables */
static tracker_state_t g_state = {0};
static tracker_active_t g_active = {0};
static bool g_initialized = false;
static bool g_dirty = false;  /* Flag for unsaved changes */

/* MAC connection count tracking */
static mac_count_table_t g_mac_count_table = {0};
static bool g_mac_count_initialized = false;
static bool g_mac_count_dirty = false;

/* ============================================================================
 * STATIC HELPER FUNCTIONS
 * ============================================================================ */

/**
 * @brief Calculate CRC32 for data integrity verification
 */
static uint32_t calculate_crc32(const void* data, size_t length)
{
    /* Simple CRC32 implementation */
    const uint8_t* bytes = (const uint8_t*)data;
    uint32_t crc = 0xFFFFFFFF;
    
    for (size_t i = 0; i < length; i++) {
        crc ^= bytes[i];
        for (int j = 0; j < 8; j++) {
            crc = (crc >> 1) ^ (0xEDB88320 & -(crc & 1));
        }
    }
    
    return crc ^ 0xFFFFFFFF;
}

/**
 * @brief Validate tracker state in NVS
 */
static bool validate_state(tracker_state_t* state)
{
    if (state->magic_number != TRACKER_MAGIC_NUMBER) {
        return false;
    }
    
    uint32_t stored_crc = state->crc32;
    state->crc32 = 0;
    uint32_t calculated_crc = calculate_crc32(state, sizeof(tracker_state_t) - sizeof(uint32_t));
    state->crc32 = stored_crc;
    
    return stored_crc == calculated_crc;
}

/**
 * @brief Find active client by MAC address
 */
static int find_active_client(const uint8_t* mac_addr)
{
    for (int i = 0; i < g_active.active_count; i++) {
        if (memcmp(g_active.active[i].mac_addr, mac_addr, 6) == 0) {
            return i;
        }
    }
    return -1;
}

/**
 * @brief Find first empty active client slot
 */
static int find_empty_slot(void)
{
    for (int i = 0; i < MAX_ACTIVE_CLIENTS; i++) {
        if (!g_active.active[i].is_still_connected) {
            return i;
        }
    }
    return -1;
}

/**
 * @brief Convert path string to bitmask flag
 */
static uint16_t path_to_flag(const char* path)
{
    if (path == NULL || path[0] == '\0') {
        return PATH_NONE;
    }
    
    /* Handle root path */
    if (strcmp(path, "/") == 0 || strcmp(path, "") == 0) {
        return PATH_ROOT;
    }
    
    /* Android captive portal detection */
    if (strstr(path, "generate_204") != NULL) {
        return PATH_GENERATE_204;
    }
    
    /* iOS captive portal detection */
    if (strstr(path, "hotspot-detect.html") != NULL) {
        return PATH_HOTSPOT_DETECT;
    }
    
    /* Windows captive portal detection */
    if (strstr(path, "connecttest.txt") != NULL) {
        return PATH_CONNECT_TEST;
    }
    
    if (strstr(path, "ncsi.txt") != NULL) {
        return PATH_ND;
    }
    
    /* Firmware update endpoints */
    if (strstr(path, "update") != NULL) {
        return PATH_UPDATE;
    }
    
    /* Form submission */
    if (strstr(path, "action") != NULL) {
        return PATH_ACTION;
    }
    
    /* Status page */
    if (strstr(path, "status") != NULL) {
        return PATH_STATUS;
    }
    
    /* Unknown path */
    return PATH_UNKNOWN;
}

/**
 * @brief Infer connection type from paths accessed
 */
static connection_type_t infer_connection_type(uint16_t paths_bitmask)
{
    /* If only captive portal detection paths were accessed, it's automatic */
    if ((paths_bitmask & ~(PATH_ROOT | PATH_GENERATE_204 | PATH_HOTSPOT_DETECT | 
                          PATH_CONNECT_TEST | PATH_ND)) == 0) {
        return CONN_TYPE_AUTOMATIC;
    }
    
    /* If update or action paths were accessed, user was manually browsing */
    if (paths_bitmask & (PATH_UPDATE | PATH_ACTION | PATH_STATUS)) {
        return CONN_TYPE_MANUAL;
    }
    
    /* If root was accessed without detection paths, likely manual */
    if (paths_bitmask & PATH_ROOT) {
        /* Check if it was part of automatic detection sequence */
        if ((paths_bitmask & (PATH_GENERATE_204 | PATH_HOTSPOT_DETECT | 
                             PATH_CONNECT_TEST | PATH_ND)) == 0) {
            return CONN_TYPE_MANUAL;
        }
    }
    
    return CONN_TYPE_UNKNOWN;
}

/**
 * @brief Check if MAC address is unique (not seen before)
 */
static bool is_unique_mac(const uint8_t* mac_addr)
{
    /* Check active clients */
    for (int i = 0; i < g_active.active_count; i++) {
        if (memcmp(g_active.active[i].mac_addr, mac_addr, 6) == 0) {
            return false;
        }
    }
    
    /* Check history */
    for (int i = 0; i < g_state.history.count; i++) {
        if (memcmp(g_state.history.sessions[i].mac_addr, mac_addr, 6) == 0) {
            return false;
        }
    }
    
    return true;
}

/**
 * @brief Update aggregated statistics
 */
static void update_stats_on_connect(const uint8_t* mac_addr)
{
    g_state.stats.total_connections++;
    g_state.stats.active_sessions++;
    g_state.stats.last_connection_time = (uint32_t)(esp_timer_get_time() / 1000000);
    
    if (is_unique_mac(mac_addr)) {
        g_state.stats.total_unique_clients++;
    }
    
    g_dirty = true;
}

/**
 * @brief Update aggregated statistics on disconnect
 */
static void update_stats_on_disconnect(client_session_t* session)
{
    g_state.stats.active_sessions--;
    g_state.stats.completed_sessions++;
    g_state.stats.total_session_time += session->duration_seconds;
    g_state.stats.total_requests += session->request_count;
    g_state.stats.total_bytes_sent += session->bytes_sent;
    g_state.stats.total_bytes_received += session->bytes_received;
    
    /* Recalculate average duration */
    if (g_state.stats.completed_sessions > 0) {
        g_state.stats.average_session_duration = 
            (float)g_state.stats.total_session_time / g_state.stats.completed_sessions;
    }
    
    g_dirty = true;
}

/**
 * @brief Add session to history ring buffer
 */
static void add_to_history(client_session_t* session)
{
    /* Infer connection type if not set */
    if (session->conn_type == CONN_TYPE_UNKNOWN) {
        session->conn_type = infer_connection_type(session->paths_bitmask);
    }
    
    /* Add to ring buffer */
    memcpy(&g_state.history.sessions[g_state.history.head_index], session, sizeof(client_session_t));
    
    /* Update ring buffer state */
    g_state.history.head_index = (g_state.history.head_index + 1) % MAX_HISTORY_ENTRIES;
    if (g_state.history.count < MAX_HISTORY_ENTRIES) {
        g_state.history.count++;
    }
    g_state.history.total_ever_logged++;
    
    /* Update statistics */
    update_stats_on_disconnect(session);
    
    /* Mark for NVS save */
    g_dirty = true;
}

/* ============================================================================
 * CORE API IMPLEMENTATION
 * ============================================================================ */

void tracker_init(void)
{
    if (g_initialized) {
        ESP_LOGW(TAG, "Client tracker already initialized");
        return;
    }
    
    ESP_LOGI(TAG, "Initializing client tracker");
    
    /* Initialize active tracking */
    memset(&g_active, 0, sizeof(tracker_active_t));
    g_active.active_count = 0;
    
    /* Load state from NVS */
    nvs_handle_t nvs_handle;
    esp_err_t ret = nvs_open(TRACKER_NVS_NAMESPACE, NVS_READONLY, &nvs_handle);
    
    if (ret == ESP_OK) {
        size_t required_size = sizeof(tracker_state_t);
        ret = nvs_get_blob(nvs_handle, TRACKER_NVS_KEY, &g_state, &required_size);
        
        if (ret == ESP_OK && required_size == sizeof(tracker_state_t)) {
            if (validate_state(&g_state)) {
                ESP_LOGI(TAG, "Loaded tracker state from NVS: %" PRIu32 " sessions, %" PRIu32 " total logged",
                         (uint32_t)g_state.history.count, (uint32_t)g_state.history.total_ever_logged);
                
                /* Log stats on load */
                ESP_LOGI(TAG, "Stats: %" PRIu32 " connections, %" PRIu32 " unique clients, avg duration: %.1f seconds",
                         g_state.stats.total_connections,
                         g_state.stats.total_unique_clients,
                         g_state.stats.average_session_duration);
            } else {
                ESP_LOGW(TAG, "Invalid tracker state in NVS, resetting");
                memset(&g_state, 0, sizeof(tracker_state_t));
            }
        } else {
            ESP_LOGI(TAG, "No existing tracker state found, initializing fresh");
            memset(&g_state, 0, sizeof(tracker_state_t));
        }
        nvs_close(nvs_handle);
    } else if (ret == ESP_ERR_NVS_NOT_FOUND) {
        /* First boot - initialize state */
        memset(&g_state, 0, sizeof(tracker_state_t));
        g_state.magic_number = TRACKER_MAGIC_NUMBER;
        ESP_LOGI(TAG, "First boot - tracker state initialized");
    } else {
        ESP_LOGE(TAG, "Failed to open NVS: %s", esp_err_to_name(ret));
        memset(&g_state, 0, sizeof(tracker_state_t));
        g_state.magic_number = TRACKER_MAGIC_NUMBER;
    }
    
    /* Initialize first connection timestamp if not set */
    if (g_state.stats.first_connection_time == 0) {
        g_state.stats.first_connection_time = (uint32_t)(esp_timer_get_time() / 1000000);
    }
    
    /* Initialize MAC connection count tracking */
    tracker_mac_count_init();
    
    g_initialized = true;
    ESP_LOGI(TAG, "Client tracker initialized successfully");
}

void tracker_deinit(void)
{
    if (!g_initialized) {
        return;
    }
    
    ESP_LOGI(TAG, "Deinitializing client tracker");
    
    /* Save any pending changes */
    if (g_dirty) {
        tracker_save_to_nvs();
    }
    
    /* Save MAC count table */
    if (g_mac_count_initialized) {
        tracker_mac_save_to_nvs();
    }
    
    g_initialized = false;
}

void tracker_save_to_nvs(void)
{
    if (!g_initialized) {
        return;
    }
    
    /* Calculate CRC before saving */
    g_state.crc32 = 0;
    g_state.crc32 = calculate_crc32(&g_state, sizeof(tracker_state_t) - sizeof(uint32_t));
    
    nvs_handle_t nvs_handle;
    esp_err_t ret = nvs_open(TRACKER_NVS_NAMESPACE, NVS_READWRITE, &nvs_handle);
    
    if (ret == ESP_OK) {
        ret = nvs_set_blob(nvs_handle, TRACKER_NVS_KEY, &g_state, sizeof(tracker_state_t));
        
        if (ret == ESP_OK) {
            ret = nvs_commit(nvs_handle);
            if (ret == ESP_OK) {
                g_dirty = false;
                ESP_LOGD(TAG, "Tracker state saved to NVS");
            } else {
                ESP_LOGE(TAG, "Failed to commit NVS: %s", esp_err_to_name(ret));
            }
        } else {
            ESP_LOGE(TAG, "Failed to write NVS blob: %s", esp_err_to_name(ret));
        }
        nvs_close(nvs_handle);
    } else {
        ESP_LOGE(TAG, "Failed to open NVS for writing: %s", esp_err_to_name(ret));
    }
}

void tracker_clear_all(void)
{
    if (!g_initialized) {
        return;
    }
    
    ESP_LOGI(TAG, "Clearing all tracker data");
    
    /* Clear active clients */
    memset(&g_active, 0, sizeof(tracker_active_t));
    g_active.active_count = 0;
    
    /* Clear history */
    memset(&g_state.history, 0, sizeof(tracker_history_t));
    
    /* Reset statistics */
    memset(&g_state.stats, 0, sizeof(tracker_stats_t));
    g_state.stats.first_connection_time = (uint32_t)(esp_timer_get_time() / 1000000);
    
    /* Clear MAC connection counts */
    tracker_mac_clear_all();
    
    /* Save cleared state */
    g_dirty = true;
    tracker_save_to_nvs();
    
    ESP_LOGI(TAG, "All tracker data cleared");
}

/* ============================================================================
 * CLIENT TRACKING IMPLEMENTATION
 * ============================================================================ */

void tracker_on_connect(const uint8_t* mac_addr)
{
    if (!g_initialized || mac_addr == NULL) {
        return;
    }
    
    ESP_LOGI(TAG, "Client connected: " MACSTR, MAC2STR(mac_addr));
    
    /* Record MAC connection count */
    tracker_mac_record_connection(mac_addr);
    
    /* Check if already tracking this client */
    int existing_idx = find_active_client(mac_addr);
    if (existing_idx >= 0) {
        ESP_LOGW(TAG, "Client already being tracked, updating");
        /* Refresh connection time */
        g_active.active[existing_idx].connect_timestamp = 
            (uint32_t)(esp_timer_get_time() / 1000000);
        return;
    }
    
    /* Find empty slot */
    int slot = find_empty_slot();
    if (slot < 0) {
        ESP_LOGW(TAG, "Maximum active clients reached, dropping oldest");
        /* Find oldest session and replace it */
        uint32_t oldest_time = UINT32_MAX;
        int oldest_idx = 0;
        for (int i = 0; i < MAX_ACTIVE_CLIENTS; i++) {
            if (g_active.active[i].connect_timestamp < oldest_time) {
                oldest_time = g_active.active[i].connect_timestamp;
                oldest_idx = i;
            }
        }
        slot = oldest_idx;
    }
    
    /* Initialize new session */
    client_session_t* session = &g_active.active[slot];
    memset(session, 0, sizeof(client_session_t));
    
    memcpy(session->mac_addr, mac_addr, 6);
    session->connect_timestamp = (uint32_t)(esp_timer_get_time() / 1000000);
    session->is_still_connected = true;
    session->request_count = 0;
    session->paths_bitmask = PATH_NONE;
    session->bytes_sent = 0;
    session->bytes_received = 0;
    
    /* Update active count if this is a new slot */
    if (slot >= g_active.active_count) {
        g_active.active_count = slot + 1;
    }
    
    /* Update statistics */
    update_stats_on_connect(mac_addr);
    
    ESP_LOGD(TAG, "Active clients: %u", g_active.active_count);
}

void tracker_on_disconnect(const uint8_t* mac_addr)
{
    if (!g_initialized || mac_addr == NULL) {
        return;
    }
    
    ESP_LOGI(TAG, "Client disconnected: " MACSTR, MAC2STR(mac_addr));
    
    /* Find active session */
    int idx = find_active_client(mac_addr);
    if (idx < 0) {
        ESP_LOGW(TAG, "Disconnect for unknown client: " MACSTR, MAC2STR(mac_addr));
        return;
    }
    
    /* Get session and finalize */
    client_session_t* session = &g_active.active[idx];
    
    /* Calculate duration */
    uint32_t now = (uint32_t)(esp_timer_get_time() / 1000000);
    session->disconnect_timestamp = now;
    session->duration_seconds = now - session->connect_timestamp;
    session->is_still_connected = false;
    
    /* Update MAC connection time tracking */
    tracker_mac_record_disconnect(mac_addr, session->duration_seconds);
    
    /* Log session */
    ESP_LOGI(TAG, "Session duration: %" PRIu32 " seconds, %" PRIu32 " requests, paths: 0x%04X",
             (uint32_t)session->duration_seconds, (uint32_t)session->request_count, (unsigned int)session->paths_bitmask);
    
    /* Add to history */
    add_to_history(session);
    
    /* Clear active slot */
    memset(session, 0, sizeof(client_session_t));
    
    /* Update active count */
    g_active.active_count = 0;
    for (int i = 0; i < MAX_ACTIVE_CLIENTS; i++) {
        if (g_active.active[i].is_still_connected) {
            g_active.active_count++;
        }
    }
    
    ESP_LOGD(TAG, "Active clients remaining: %u", g_active.active_count);
}

void tracker_on_request(const uint8_t* mac_addr, const char* path, bool is_incoming, uint32_t bytes)
{
    if (!g_initialized || mac_addr == NULL) {
        return;
    }
    
    /* Find active session */
    int idx = find_active_client(mac_addr);
    if (idx < 0) {
        /* Client might have connected before tracker was initialized */
        ESP_LOGW(TAG, "Request from unknown client, creating session");
        tracker_on_connect(mac_addr);
        idx = find_active_client(mac_addr);
        if (idx < 0) {
            return;
        }
    }
    
    client_session_t* session = &g_active.active[idx];
    
    /* Update request count */
    session->request_count++;
    
    /* Update bytes transferred */
    if (is_incoming) {
        session->bytes_received += bytes;
    } else {
        session->bytes_sent += bytes;
    }
    
    /* Update path tracking */
    uint16_t path_flag = path_to_flag(path);
    if (path_flag != PATH_NONE) {
        /* Check if this is a new path */
        if ((session->paths_bitmask & path_flag) == 0) {
            session->paths_bitmask |= path_flag;
            
            /* Record first path if not set */
            if (session->first_path[0] == '\0' && path != NULL) {
                strncpy(session->first_path, path, sizeof(session->first_path) - 1);
                session->first_path[sizeof(session->first_path) - 1] = '\0';
            }
        }
    }
    
    /* Update last activity time */
    g_active.last_activity_time = (uint32_t)(esp_timer_get_time() / 1000000);
    
    g_dirty = true;
}

void tracker_update_activity(void)
{
    if (!g_initialized) {
        return;
    }
    
    g_active.last_activity_time = (uint32_t)(esp_timer_get_time() / 1000000);
}

uint8_t tracker_check_timeouts(uint32_t timeout_seconds)
{
    if (!g_initialized || timeout_seconds == 0) {
        return 0;
    }
    
    uint32_t now = (uint32_t)(esp_timer_get_time() / 1000000);
    uint8_t timed_out = 0;
    
    for (int i = 0; i < MAX_ACTIVE_CLIENTS; i++) {
        if (g_active.active[i].is_still_connected) {
            uint32_t idle_time = now - g_active.active[i].connect_timestamp;
            
            if (idle_time > timeout_seconds) {
                ESP_LOGI(TAG, "Client timed out after %" PRIu32 " seconds: " MACSTR,
                         (uint32_t)idle_time, MAC2STR(g_active.active[i].mac_addr));
                
                /* Process as disconnect */
                tracker_on_disconnect(g_active.active[i].mac_addr);
                timed_out++;
            }
        }
    }
    
    return timed_out;
}

/* ============================================================================
 * DATA ACCESS IMPLEMENTATION
 * ============================================================================ */

tracker_history_t* tracker_get_history(void)
{
    return &g_state.history;
}

tracker_active_t* tracker_get_active(void)
{
    return &g_active;
}

void tracker_get_stats(tracker_stats_t* stats)
{
    if (stats) {
        *stats = g_state.stats;
    }
}

esp_err_t tracker_get_session(uint16_t index, client_session_t* session)
{
    if (!g_initialized || session == NULL) {
        return ESP_ERR_INVALID_ARG;
    }
    
    if (index >= g_state.history.count) {
        return ESP_ERR_NOT_FOUND;
    }
    
    /* Handle ring buffer wrap-around for logical indexing */
    uint16_t actual_index = (g_state.history.head_index + index) % MAX_HISTORY_ENTRIES;
    *session = g_state.history.sessions[actual_index];
    
    return ESP_OK;
}

void tracker_mac_to_str(const uint8_t* mac, char* buffer)
{
    if (mac == NULL || buffer == NULL) {
        if (buffer) {
            snprintf(buffer, 18, "00:00:00:00:00:00");
        }
        return;
    }
    
    snprintf(buffer, 18, "%02X:%02X:%02X:%02X:%02X:%02X",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
}

/* ============================================================================
 * MAC CONNECTION COUNT TRACKING IMPLEMENTATION
 * ============================================================================ */

/**
 * @brief Find MAC entry in count table
 */
static int find_mac_entry(const uint8_t* mac_addr)
{
    for (int i = 0; i < g_mac_count_table.count; i++) {
        if (memcmp(g_mac_count_table.entries[i].mac_addr, mac_addr, 6) == 0) {
            return i;
        }
    }
    return -1;
}

/**
 * @brief Find least recently used entry for eviction
 */
static int find_lru_entry(void)
{
    int lru_idx = 0;
    uint32_t oldest_ts = UINT32_MAX;
    
    for (int i = 0; i < g_mac_count_table.count; i++) {
        if (g_mac_count_table.entries[i].last_seen_timestamp < oldest_ts) {
            oldest_ts = g_mac_count_table.entries[i].last_seen_timestamp;
            lru_idx = i;
        }
    }
    
    return lru_idx;
}

void tracker_mac_count_init(void)
{
    if (g_mac_count_initialized) {
        ESP_LOGW(TAG, "MAC count table already initialized");
        return;
    }
    
    ESP_LOGI(TAG, "Initializing MAC connection count table");
    
    /* Load from NVS */
    nvs_handle_t nvs_handle;
    esp_err_t ret = nvs_open(TRACKER_NVS_NAMESPACE, NVS_READONLY, &nvs_handle);
    
    if (ret == ESP_OK) {
        size_t required_size = sizeof(mac_count_table_t);
        ret = nvs_get_blob(nvs_handle, MAC_COUNT_NVS_KEY, &g_mac_count_table, &required_size);
        
        if (ret == ESP_OK && required_size == sizeof(mac_count_table_t)) {
            ESP_LOGI(TAG, "Loaded MAC count table: %u unique MACs tracked",
                     g_mac_count_table.count);
            
            /* Log some entries for debugging */
            for (int i = 0; i < g_mac_count_table.count && i < 5; i++) {
                char mac_str[18];
                tracker_mac_to_str(g_mac_count_table.entries[i].mac_addr, mac_str);
                ESP_LOGI(TAG, "  MAC %s: %lu connections",
                         mac_str,
                         (unsigned long)g_mac_count_table.entries[i].connection_count);
            }
        } else {
            ESP_LOGI(TAG, "No existing MAC count table found, initializing fresh");
            memset(&g_mac_count_table, 0, sizeof(mac_count_table_t));
        }
        nvs_close(nvs_handle);
    } else if (ret == ESP_ERR_NVS_NOT_FOUND) {
        memset(&g_mac_count_table, 0, sizeof(mac_count_table_t));
        ESP_LOGI(TAG, "First boot - MAC count table initialized");
    } else {
        ESP_LOGE(TAG, "Failed to open NVS for MAC counts: %s", esp_err_to_name(ret));
        memset(&g_mac_count_table, 0, sizeof(mac_count_table_t));
    }
    
    g_mac_count_initialized = true;
    ESP_LOGI(TAG, "MAC connection count table initialized successfully");
}

void tracker_mac_record_connection(const uint8_t* mac_addr)
{
    if (!g_mac_count_initialized || mac_addr == NULL) {
        return;
    }
    
    int idx = find_mac_entry(mac_addr);
    uint32_t now = (uint32_t)(esp_timer_get_time() / 1000000);
    
    if (idx >= 0) {
        /* MAC already exists, increment count */
        g_mac_count_table.entries[idx].connection_count++;
        g_mac_count_table.entries[idx].last_seen_timestamp = now;
        g_mac_count_table.total_connections++;
        
        char mac_str[18];
        tracker_mac_to_str(mac_addr, mac_str);
        ESP_LOGI(TAG, "MAC %s reconnected: %lu total visits",
                 mac_str,
                 (unsigned long)g_mac_count_table.entries[idx].connection_count);
    } else {
        /* New MAC - add to table */
        if (g_mac_count_table.count < MAX_TRACKED_MACS) {
            /* Add new entry */
            memset(&g_mac_count_table.entries[g_mac_count_table.count], 0, 
                   sizeof(mac_connection_count_t));
            memcpy(g_mac_count_table.entries[g_mac_count_table.count].mac_addr, 
                   mac_addr, 6);
            g_mac_count_table.entries[g_mac_count_table.count].connection_count = 1;
            g_mac_count_table.entries[g_mac_count_table.count].last_seen_timestamp = now;
            g_mac_count_table.count++;
            g_mac_count_table.total_connections++;
            
            char mac_str[18];
            tracker_mac_to_str(mac_addr, mac_str);
            ESP_LOGI(TAG, "New MAC tracked: %s (first visit)", mac_str);
        } else {
            /* Table full - evict LRU and add new */
            int evict_idx = find_lru_entry();
            
            char evicted_mac[18];
            tracker_mac_to_str(g_mac_count_table.entries[evict_idx].mac_addr, evicted_mac);
            
            /* Overwrite with new MAC */
            memset(&g_mac_count_table.entries[evict_idx], 0, 
                   sizeof(mac_connection_count_t));
            memcpy(g_mac_count_table.entries[evict_idx].mac_addr, mac_addr, 6);
            g_mac_count_table.entries[evict_idx].connection_count = 1;
            g_mac_count_table.entries[evict_idx].last_seen_timestamp = now;
            g_mac_count_table.total_connections++;
            
            char new_mac[18];
            tracker_mac_to_str(mac_addr, new_mac);
            ESP_LOGI(TAG, "Table full - evicted %s, added new MAC: %s", 
                     evicted_mac, new_mac);
        }
    }
    
    g_mac_count_dirty = true;
}

uint32_t tracker_mac_get_count(const uint8_t* mac_addr)
{
    if (!g_mac_count_initialized || mac_addr == NULL) {
        return 0;
    }
    
    int idx = find_mac_entry(mac_addr);
    if (idx >= 0) {
        return g_mac_count_table.entries[idx].connection_count;
    }
    
    return 0;
}

uint32_t tracker_mac_get_total_time(const uint8_t* mac_addr)
{
    if (!g_mac_count_initialized || mac_addr == NULL) {
        return 0;
    }
    
    int idx = find_mac_entry(mac_addr);
    if (idx >= 0) {
        return g_mac_count_table.entries[idx].total_connected_sec;
    }
    
    return 0;
}

void tracker_mac_record_disconnect(const uint8_t* mac_addr, uint32_t duration_seconds)
{
    if (!g_mac_count_initialized || mac_addr == NULL) {
        return;
    }
    
    int idx = find_mac_entry(mac_addr);
    if (idx >= 0) {
        g_mac_count_table.entries[idx].total_connected_sec += duration_seconds;
        g_mac_count_dirty = true;
        
        char mac_str[18];
        tracker_mac_to_str(mac_addr, mac_str);
        ESP_LOGI(TAG, "MAC %s session: %lu sec, total: %lu sec across %lu visits",
                 mac_str,
                 (unsigned long)duration_seconds,
                 (unsigned long)g_mac_count_table.entries[idx].total_connected_sec,
                 (unsigned long)g_mac_count_table.entries[idx].connection_count);
    }
}

mac_count_table_t* tracker_mac_get_table(void)
{
    return &g_mac_count_table;
}

void tracker_mac_get_info_string(const uint8_t* mac_addr, char* buffer, size_t buffer_size)
{
    if (buffer == NULL || buffer_size == 0) {
        return;
    }
    
    char mac_str[18];
    tracker_mac_to_str(mac_addr, mac_str);
    
    uint32_t count = tracker_mac_get_count(mac_addr);
    
    snprintf(buffer, buffer_size, "%s - %lu connections", 
             mac_str, (unsigned long)count);
}

void tracker_mac_save_to_nvs(void)
{
    if (!g_mac_count_initialized || !g_mac_count_dirty) {
        return;
    }
    
    nvs_handle_t nvs_handle;
    esp_err_t ret = nvs_open(TRACKER_NVS_NAMESPACE, NVS_READWRITE, &nvs_handle);
    
    if (ret == ESP_OK) {
        ret = nvs_set_blob(nvs_handle, MAC_COUNT_NVS_KEY, 
                          &g_mac_count_table, sizeof(mac_count_table_t));
        
        if (ret == ESP_OK) {
            ret = nvs_commit(nvs_handle);
            if (ret == ESP_OK) {
                g_mac_count_dirty = false;
                ESP_LOGD(TAG, "MAC count table saved to NVS");
            } else {
                ESP_LOGE(TAG, "Failed to commit MAC NVS: %s", esp_err_to_name(ret));
            }
        } else {
            ESP_LOGE(TAG, "Failed to write MAC NVS blob: %s", esp_err_to_name(ret));
        }
        nvs_close(nvs_handle);
    } else {
        ESP_LOGE(TAG, "Failed to open NVS for MAC writing: %s", esp_err_to_name(ret));
    }
}

void tracker_mac_clear_all(void)
{
    if (!g_mac_count_initialized) {
        return;
    }
    
    ESP_LOGI(TAG, "Clearing all MAC connection counts");
    
    memset(&g_mac_count_table, 0, sizeof(mac_count_table_t));
    g_mac_count_dirty = true;
    tracker_mac_save_to_nvs();
    
    ESP_LOGI(TAG, "All MAC connection counts cleared");
}

/* ============================================================================
 * BLE EXPORT IMPLEMENTATION
 * ============================================================================ */

uint16_t tracker_serialize_for_ble(uint8_t* buffer, size_t buffer_size, uint16_t start_index, uint8_t max_entries)
{
    if (buffer == NULL || buffer_size == 0) {
        return 0;
    }
    
    uint16_t written = 0;
    client_session_t session;
    
    /* Limit entries to available */
    if (start_index >= g_state.history.count) {
        return 0;
    }
    
    uint8_t entries = max_entries;
    if (start_index + entries > g_state.history.count) {
        entries = g_state.history.count - start_index;
    }
    
    for (uint8_t i = 0; i < entries && written < buffer_size; i++) {
        uint16_t src_index = (g_state.history.head_index + start_index + i) % MAX_HISTORY_ENTRIES;
        session = g_state.history.sessions[src_index];
        
        /* Calculate remaining space */
        size_t remaining = buffer_size - written;
        size_t session_size = sizeof(client_session_t);
        
        if (remaining < session_size) {
            /* Partial write - copy what fits */
            memcpy(buffer + written, &session, remaining);
            written += remaining;
            break;
        }
        
        /* Copy full session */
        memcpy(buffer + written, &session, session_size);
        written += session_size;
    }
    
    return written;
}

uint32_t tracker_get_ble_data_size(void)
{
    return (uint32_t)(g_state.history.count * sizeof(client_session_t));
}

esp_err_t tracker_get_stats_string(char* buffer, size_t buffer_size)
{
    if (buffer == NULL || buffer_size == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    
    snprintf(buffer, buffer_size,
             "Conn:%lu Uniq:%lu Active:%lu AvgDur:%.1fs Req:%lu",
             (unsigned long)g_state.stats.total_connections,
             (unsigned long)g_state.stats.total_unique_clients,
             (unsigned long)g_state.stats.active_sessions,
             g_state.stats.average_session_duration,
             (unsigned long)g_state.stats.total_requests);
    
    return ESP_OK;
}

void tracker_paths_to_string(uint16_t bitmask, char* buffer, size_t buffer_size)
{
    if (buffer == NULL || buffer_size == 0) {
        return;
    }
    
    buffer[0] = '\0';
    
    /* Build string of paths */
    if (bitmask & PATH_ROOT) {
        strncat(buffer, "ROOT ", buffer_size - strlen(buffer) - 1);
    }
    if (bitmask & PATH_GENERATE_204) {
        strncat(buffer, "ANDROID ", buffer_size - strlen(buffer) - 1);
    }
    if (bitmask & PATH_HOTSPOT_DETECT) {
        strncat(buffer, "IOS ", buffer_size - strlen(buffer) - 1);
    }
    if (bitmask & PATH_CONNECT_TEST) {
        strncat(buffer, "WIN ", buffer_size - strlen(buffer) - 1);
    }
    if (bitmask & PATH_UPDATE) {
        strncat(buffer, "UPDATE ", buffer_size - strlen(buffer) - 1);
    }
    if (bitmask & PATH_ACTION) {
        strncat(buffer, "ACTION ", buffer_size - strlen(buffer) - 1);
    }
    if (bitmask & PATH_UNKNOWN) {
        strncat(buffer, "OTHER ", buffer_size - strlen(buffer) - 1);
    }
    
    /* Remove trailing space if present */
    size_t len = strlen(buffer);
    if (len > 0 && buffer[len - 1] == ' ') {
        buffer[len - 1] = '\0';
    }
}

/**
 * @brief Convert path bitmask to pipe-separated string for CSV
 */
static void paths_to_csv_string(uint16_t bitmask, char* buffer, size_t buffer_size)
{
    if (buffer == NULL || buffer_size == 0) {
        return;
    }
    
    buffer[0] = '\0';
    bool first = true;
    
    if (bitmask & PATH_ROOT) {
        strncat(buffer, first ? "" : "|", buffer_size - strlen(buffer) - 1);
        strncat(buffer, "ROOT", buffer_size - strlen(buffer) - 1);
        first = false;
    }
    if (bitmask & PATH_GENERATE_204) {
        strncat(buffer, first ? "" : "|", buffer_size - strlen(buffer) - 1);
        strncat(buffer, "ANDROID", buffer_size - strlen(buffer) - 1);
        first = false;
    }
    if (bitmask & PATH_HOTSPOT_DETECT) {
        strncat(buffer, first ? "" : "|", buffer_size - strlen(buffer) - 1);
        strncat(buffer, "IOS", buffer_size - strlen(buffer) - 1);
        first = false;
    }
    if (bitmask & PATH_CONNECT_TEST) {
        strncat(buffer, first ? "" : "|", buffer_size - strlen(buffer) - 1);
        strncat(buffer, "WIN", buffer_size - strlen(buffer) - 1);
        first = false;
    }
    if (bitmask & PATH_UPDATE) {
        strncat(buffer, first ? "" : "|", buffer_size - strlen(buffer) - 1);
        strncat(buffer, "UPDATE", buffer_size - strlen(buffer) - 1);
        first = false;
    }
    if (bitmask & PATH_ACTION) {
        strncat(buffer, first ? "" : "|", buffer_size - strlen(buffer) - 1);
        strncat(buffer, "ACTION", buffer_size - strlen(buffer) - 1);
        first = false;
    }
    if (bitmask & PATH_UNKNOWN) {
        strncat(buffer, first ? "" : "|", buffer_size - strlen(buffer) - 1);
        strncat(buffer, "OTHER", buffer_size - strlen(buffer) - 1);
    }
}

uint32_t tracker_get_csv_size(void)
{
    /* Estimate size: header + per session row + summary */
    /* Header: ~80 bytes */
    /* Each session: ~100 bytes */
    /* Summary: ~200 bytes */
    /* With 100 sessions: ~100 + 100*100 + 200 = 10,300 bytes */
    return 12000;  /* Safe upper bound */
}

uint32_t tracker_generate_csv(char* buffer, size_t buffer_size)
{
    if (buffer == NULL || buffer_size == 0) {
        return 0;
    }
    
    char mac_str[18];
    char paths_str[64];
    uint32_t pos = 0;
    uint32_t session_num = 0;
    
    /* Check if buffer is large enough */
    if (buffer_size < 256) {
        ESP_LOGE(TAG, "CSV buffer too small");
        return 0;
    }
    
    /* Write CSV header with CRLF for Excel compatibility */
    pos += snprintf(buffer + pos, buffer_size - pos,
        "Session ID,Date,Time,MAC Address,Duration (s),Requests,Paths Accessed,Bytes Sent,Bytes Received\r\n");
    
    /* Calculate session start time for relative timestamps */
    uint32_t base_time = g_state.stats.first_connection_time;
    
    /* Write each session as a row */
    for (int i = 0; i < g_state.history.count && pos < buffer_size - 200; i++) {
        /* Handle ring buffer wrap-around for chronological order */
        uint16_t src_idx = (g_state.history.head_index + i) % MAX_HISTORY_ENTRIES;
        client_session_t* session = &g_state.history.sessions[src_idx];
        
        if (session->mac_addr[0] == 0 && session->mac_addr[1] == 0) {
            continue;  /* Skip empty session */
        }
        
        session_num++;
        
        /* Convert MAC to string */
        tracker_mac_to_str(session->mac_addr, mac_str);
        
        /* Convert paths bitmask to pipe-separated string */
        paths_to_csv_string(session->paths_bitmask, paths_str, sizeof(paths_str));
        
        /* Calculate date and time from timestamp */
        uint32_t timestamp = base_time + session->connect_timestamp;
        time_t time_val = timestamp;
        struct tm* timeinfo = localtime((const time_t*)&time_val);
        
        char date_str[16];
        char time_str[16];
        strftime(date_str, sizeof(date_str), "%Y-%m-%d", timeinfo);
        strftime(time_str, sizeof(time_str), "%H:%M:%S", timeinfo);
        
        /* Write CSV row */
        int written = snprintf(buffer + pos, buffer_size - pos,
            "%" PRIu32 ",%s,%s,%s,%" PRIu32 ",%" PRIu32 ",\"%s\",%" PRIu32 ",%" PRIu32 "\r\n",
            (uint32_t)(session_num + g_state.history.total_ever_logged - g_state.history.count + i),
            date_str,
            time_str,
            mac_str,
            (uint32_t)session->duration_seconds,
            (uint32_t)session->request_count,
            paths_str,
            (uint32_t)session->bytes_sent,
            (uint32_t)session->bytes_received);
        
        if (written > 0 && (size_t)written < buffer_size - pos) {
            pos += written;
        } else {
            break;  /* Buffer full */
        }
    }
    
    /* Write empty line before summary */
    pos += snprintf(buffer + pos, buffer_size - pos, "\r\n");
    
    /* Write summary section */
    pos += snprintf(buffer + pos, buffer_size - pos,
        "SUMMARY REPORT\r\n");
    pos += snprintf(buffer + pos, buffer_size - pos,
        "Total Connections,%lu,,,,\r\n",
        (unsigned long)g_state.stats.total_connections);
    pos += snprintf(buffer + pos, buffer_size - pos,
        "Unique Clients,%lu,,,,\r\n",
        (unsigned long)g_state.stats.total_unique_clients);
    pos += snprintf(buffer + pos, buffer_size - pos,
        "Completed Sessions,%lu,,,,\r\n",
        (unsigned long)g_state.stats.completed_sessions);
    pos += snprintf(buffer + pos, buffer_size - pos,
        "Active Sessions,%lu,,,,\r\n",
        (unsigned long)g_state.stats.active_sessions);
    pos += snprintf(buffer + pos, buffer_size - pos,
        "Average Duration,%.1f seconds,,,,\r\n",
        g_state.stats.average_session_duration);
    
    /* Calculate total data transfer in KB */
    uint32_t total_bytes = g_state.stats.total_bytes_sent + g_state.stats.total_bytes_received;
    pos += snprintf(buffer + pos, buffer_size - pos,
        "Total Data Transfer,%lu bytes (%.1f KB),,,,\r\n",
        (unsigned long)total_bytes,
        total_bytes / 1024.0f);
    
    pos += snprintf(buffer + pos, buffer_size - pos,
        "Total HTTP Requests,%lu,,,,\r\n",
        (unsigned long)g_state.stats.total_requests);
    
    /* Add timestamp */
    time_t now;
    time(&now);
    struct tm* timeinfo = localtime(&now);
    char timestamp_str[32];
    strftime(timestamp_str, sizeof(timestamp_str), "%Y-%m-%d %H:%M:%S", timeinfo);
    
    pos += snprintf(buffer + pos, buffer_size - pos,
        "Generated At,%s,,,,\r\n", timestamp_str);
    
    ESP_LOGI(TAG, "CSV generated: %" PRIu32 " bytes, %" PRIu32 " sessions", (uint32_t)pos, (uint32_t)session_num);
    
    return pos;
}

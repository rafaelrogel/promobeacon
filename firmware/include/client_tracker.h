/**
 * Client Tracker Header
 *
 * Tracks WiFi AP client connections, session durations, and HTTP request paths.
 * Data is persisted in NVS and exposed via BLE for mobile app access.
 *
 * Features:
 * - Client connection/disconnection tracking with MAC address
 * - Session duration calculation
 * - HTTP request path logging (captive portal detection, updates, etc.)
 * - Ring buffer history for last 100 sessions
 * - NVS persistence across reboots and OTA updates
 *
 * Author: MiniMax Agent
 * Version: 2.0.0
 */

#ifndef CLIENT_TRACKER_H
#define CLIENT_TRACKER_H

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * CONFIGURATION CONSTANTS
 * ============================================================================ */

#define MAX_HISTORY_ENTRIES         100     /* Maximum stored sessions */
#define MAX_ACTIVE_CLIENTS          8       /* Maximum simultaneous clients */
#define MAX_PATH_HISTORY            10      /* Maximum unique paths per session */
#define TRACKER_NVS_NAMESPACE       "tracker"
#define TRACKER_NVS_KEY             "history"

/* ============================================================================
 * PATH TRACKING ENUMERATIONS
 * ============================================================================ */

/**
 * @brief Bitmask flags for tracking which paths clients accessed
 * Using bitmask saves memory compared to storing full URL strings
 */
typedef enum {
    PATH_NONE            = 0x00,      /* No paths tracked */
    PATH_ROOT            = (1 << 0),  /* "/" - Root/captive portal page */
    PATH_GENERATE_204    = (1 << 1),  /* "/generate_204" - Android captive portal detection */
    PATH_HOTSPOT_DETECT  = (1 << 2),  /* "/hotspot-detect.html" - iOS captive portal detection */
    PATH_CONNECT_TEST    = (1 << 3),  /* "/connecttest.txt" - Windows captive portal detection */
    PATH_ND             = (1 << 4),  /* "/ncsi.txt" - Windows NCSI detection */
    PATH_UPDATE         = (1 << 5),  /* "/update" - Firmware update page */
    PATH_ACTION         = (1 << 6),  /* "/action" - Form submission endpoint */
    PATH_STATUS         = (1 << 7),  /* "/status" - Status page */
    PATH_UNKNOWN        = (1 << 8)   /* Unknown/redirected paths */
} path_flag_t;

/**
 * @brief Connection type inferred from paths accessed
 */
typedef enum {
    CONN_TYPE_UNKNOWN    = 0,
    CONN_TYPE_MANUAL,             /* User manually opened browser */
    CONN_TYPE_AUTOMATIC,          /* Automatic captive portal detection */
    CONN_TYPE_UPDATER             /* Client accessing update endpoint */
} connection_type_t;

/* ============================================================================
 * DATA STRUCTURES
 * ============================================================================ */

/**
 * @brief Individual path visit record
 */
typedef struct {
    char path[32];                /* Path string (truncated) */
    uint16_t visit_count;         /* Number of visits to this path */
} path_visit_t;

/**
 * @brief Single client session record
 */
typedef struct {
    uint8_t mac_addr[6];          /* Client MAC address */
    uint32_t connect_timestamp;   /* Connection time (system uptime seconds) */
    uint32_t disconnect_timestamp;/* Disconnection time (0 if still connected) */
    uint32_t duration_seconds;    /* Session duration in seconds */
    uint32_t bytes_received;      /* Data sent to client */
    uint32_t bytes_sent;          /* Data received from client */
    uint16_t request_count;       /* Total HTTP requests */
    uint16_t paths_bitmask;       /* Bitmask of paths accessed (path_flag_t) */
    uint8_t path_count;           /* Number of unique paths accessed */
    connection_type_t conn_type;  /* Inferred connection type */
    char first_path[32];          /* First path accessed */
    bool is_still_connected;      /* Current connection status */
} client_session_t;

/**
 * @brief Aggregated statistics summary
 */
typedef struct {
    uint32_t total_connections;       /* Total lifetime connections */
    uint32_t total_unique_clients;    /* Unique MAC addresses seen */
    uint32_t active_sessions;         /* Currently connected clients */
    uint32_t completed_sessions;      /* Sessions that completed normally */
    uint32_t dropped_connections;     /* Connections without proper disconnect */
    uint32_t total_session_time;      /* Total time all clients spent (seconds) */
    float average_session_duration;   /* Average session length */
    uint32_t total_requests;          /* Total HTTP requests served */
    uint32_t total_bytes_sent;        /* Total bytes transmitted */
    uint32_t total_bytes_received;    /* Total bytes received */
    uint32_t last_connection_time;    /* Timestamp of last connection */
    uint32_t first_connection_time;   /* Timestamp of first ever connection */
} tracker_stats_t;

/**
 * @brief Ring buffer for session history
 */
typedef struct {
    client_session_t sessions[MAX_HISTORY_ENTRIES]; /* Circular buffer */
    uint16_t head_index;            /* Write position (0 to MAX_HISTORY_ENTRIES-1) */
    uint16_t count;                 /* Number of valid entries in buffer */
    uint32_t total_ever_logged;     /* Total sessions ever logged (lifetime) */
} tracker_history_t;

/**
 * @brief Active client tracking
 */
typedef struct {
    client_session_t active[MAX_ACTIVE_CLIENTS];
    uint8_t active_count;
    uint32_t last_activity_time;
} tracker_active_t;

/**
 * @brief Complete tracker state (for NVS storage)
 */
typedef struct {
    tracker_history_t history;
    tracker_stats_t stats;
    uint32_t magic_number;          /* For validation */
    uint32_t crc32;                 /* Data integrity check */
} tracker_state_t;

/* ============================================================================
 * MAC CONNECTION COUNT TRACKING
 * ============================================================================ */

/**
 * @brief Maximum number of unique MAC addresses to track for connection counts
 */
#define MAX_TRACKED_MACS            100

/**
 * @brief MAC connection count record
 */
typedef struct {
    uint8_t mac_addr[6];            /* Client MAC address */
    uint32_t connection_count;      /* Number of connections from this MAC */
    uint32_t total_connected_sec;   /* Total seconds connected across all sessions */
    uint32_t last_seen_timestamp;   /* Last connection timestamp */
    uint8_t reserved;               /* Padding for alignment */
} mac_connection_count_t;

/**
 * @brief MAC connection count table
 */
typedef struct {
    mac_connection_count_t entries[MAX_TRACKED_MACS];
    uint16_t count;                 /* Number of valid entries */
    uint32_t total_connections;     /* Total lifetime connections */
} mac_count_table_t;

/* ============================================================================
 * FUNCTION PROTOTYPES - CORE API
 * ============================================================================ */

/**
 * @brief Initialize client tracker
 *
 * Loads session history from NVS and prepares for tracking.
 * Must be called before any other tracker functions.
 */
void tracker_init(void);

/**
 * @brief Deinitialize client tracker
 *
 * Saves current state to NVS and releases resources.
 */
void tracker_deinit(void);

/**
 * @brief Save tracker state to NVS
 *
 * Commits current history and statistics to persistent storage.
 * Called automatically on disconnect, but can be called manually.
 */
void tracker_save_to_nvs(void);

/**
 * @brief Clear all tracking data
 *
 * Resets history and statistics but preserves the tracker state structure.
 */
void tracker_clear_all(void);

/* ============================================================================
 * FUNCTION PROTOTYPES - CLIENT TRACKING
 * ============================================================================ */

/**
 * @brief Record client connection
 *
 * Called when a client connects to the WiFi AP.
 *
 * @param mac_addr Client MAC address (6 bytes)
 */
void tracker_on_connect(const uint8_t* mac_addr);

/**
 * @brief Record client disconnection
 *
 * Called when a client disconnects from the WiFi AP.
 * Calculates session duration and moves to history.
 *
 * @param mac_addr Client MAC address (6 bytes)
 */
void tracker_on_disconnect(const uint8_t* mac_addr);

/**
 * @brief Record HTTP request
 *
 * Called when the web server processes a request from a client.
 * Updates request count and path tracking.
 *
 * @param mac_addr Client MAC address (6 bytes)
 * @param path Requested path/URI
 * @param is_incoming True if data received from client, false if sent to client
 * @param bytes Number of bytes transferred
 */
void tracker_on_request(const uint8_t* mac_addr, const char* path, bool is_incoming, uint32_t bytes);

/**
 * @brief Record client activity
 *
 * Called periodically to update activity timestamps.
 * Used to detect stale/ghost connections.
 */
void tracker_update_activity(void);

/**
 * @brief Check for timed out clients
 *
 * Checks all active clients and disconnects those that have been
 * inactive for too long. Should be called periodically.
 *
 * @param timeout_seconds Maximum idle time before timeout
 * @return Number of clients timed out
 */
uint8_t tracker_check_timeouts(uint32_t timeout_seconds);

/* ============================================================================
 * FUNCTION PROTOTYPES - DATA ACCESS
 * ============================================================================ */

/**
 * @brief Get session history
 *
 * Returns pointer to the session history ring buffer.
 *
 * @return Pointer to history structure
 */
tracker_history_t* tracker_get_history(void);

/**
 * @brief Get active clients
 *
 * Returns pointer to currently connected clients array.
 *
 * @return Pointer to active tracking structure
 */
tracker_active_t* tracker_get_active(void);

/**
 * @brief Get aggregated statistics
 *
 * Fills the stats structure with current statistics.
 *
 * @param stats Pointer to stats structure to fill
 */
void tracker_get_stats(tracker_stats_t* stats);

/**
 * @brief Get session by index
 *
 * Retrieves a specific session from history.
 *
 * @param index Session index (0 to count-1)
 * @param session Pointer to session structure to fill
 * @return ESP_OK if session found, ESP_ERR_NOT_FOUND otherwise
 */
esp_err_t tracker_get_session(uint16_t index, client_session_t* session);

/**
 * @brief Format MAC address to string
 *
 * Converts MAC address to human-readable string.
 *
 * @param mac MAC address (6 bytes)
 * @param buffer Output buffer (at least 18 bytes)
 */
void tracker_mac_to_str(const uint8_t* mac, char* buffer);

/* ============================================================================
 * FUNCTION PROTOTYPES - BLE EXPORT
 * ============================================================================ */

/**
 * @brief Serialize history for BLE transmission
 *
 * Packs session data into a contiguous buffer for BLE GATT transfer.
 * Uses chunked transfer for data exceeding MTU.
 *
 * @param buffer Output buffer
 * @param buffer_size Size of output buffer
 * @param start_index Starting session index
 * @param max_entries Maximum entries to include
 * @return Number of bytes written
 */
uint16_t tracker_serialize_for_ble(uint8_t* buffer, size_t buffer_size, uint16_t start_index, uint8_t max_entries);

/**
 * @brief Get BLE data total size
 *
 * Returns the total size of all history data for BLE transfer.
 *
 * @return Total data size in bytes
 */
uint32_t tracker_get_ble_data_size(void);

/**
 * @brief Get statistics string for BLE
 *
 * Creates a compact string summary of statistics for BLE characteristic.
 *
 * @param buffer Output buffer
 * @param buffer_size Size of buffer
 * @return ESP_OK on success
 */
esp_err_t tracker_get_stats_string(char* buffer, size_t buffer_size);

/**
 * @brief Parse path flag to string
 *
 * Converts path bitmask to human-readable string.
 *
 * @param bitmask Path bitmask
 * @param buffer Output buffer
 * @param buffer_size Size of buffer
 */
void tracker_paths_to_string(uint16_t bitmask, char* buffer, size_t buffer_size);

/**
 * @brief Generate CSV export data
 *
 * Creates a complete CSV file content with all session data
 * and aggregated statistics. Uses pipe separator for paths
 * to avoid CSV comma conflicts.
 *
 * @param buffer Output buffer for CSV data
 * @param buffer_size Size of output buffer
 * @return Number of bytes written (0 on error or buffer too small)
 */
uint32_t tracker_generate_csv(char* buffer, size_t buffer_size);

/**
 * @brief Get CSV data size
 *
 * Returns the estimated size needed for CSV export.
 * Useful for checking if buffer is large enough.
 *
 * @return Estimated CSV size in bytes
 */
uint32_t tracker_get_csv_size(void);

/* ============================================================================
 * FUNCTION PROTOTYPES - MAC CONNECTION COUNTING
 * ============================================================================ */

/**
 * @brief Initialize MAC connection count table
 *
 * Loads the MAC count table from NVS or creates a new one.
 * Must be called after tracker_init().
 */
void tracker_mac_count_init(void);

/**
 * @brief Record a connection from a MAC address
 *
 * Called when a client connects. Increments the connection count
 * for the given MAC address or adds it if new.
 *
 * @param mac_addr Client MAC address (6 bytes)
 */
void tracker_mac_record_connection(const uint8_t* mac_addr);

/**
 * @brief Record disconnection and update total time
 *
 * Called when a client disconnects. Updates the total connected time
 * for this MAC address based on the session duration.
 *
 * @param mac_addr Client MAC address (6 bytes)
 * @param duration_seconds Duration of this session in seconds
 */
void tracker_mac_record_disconnect(const uint8_t* mac_addr, uint32_t duration_seconds);

/**
 * @brief Get connection count for a specific MAC address
 *
 * Returns the number of times this MAC has connected.
 *
 * @param mac_addr Client MAC address (6 bytes)
 * @return Connection count (0 if MAC not found)
 */
uint32_t tracker_mac_get_count(const uint8_t* mac_addr);

/**
 * @brief Get total connected time for a specific MAC address
 *
 * Returns the total seconds this MAC has been connected across all sessions.
 *
 * @param mac_addr Client MAC address (6 bytes)
 * @return Total connected seconds (0 if MAC not found)
 */
uint32_t tracker_mac_get_total_time(const uint8_t* mac_addr);

/**
 * @brief Get the MAC connection count table
 *
 * Returns pointer to the internal MAC count table.
 * Useful for iterating through all tracked MACs.
 *
 * @return Pointer to mac_count_table_t
 */
mac_count_table_t* tracker_mac_get_table(void);

/**
 * @brief Get MAC info as formatted string
 *
 * Fills buffer with MAC address and connection count.
 *
 * @param mac_addr Client MAC address (6 bytes)
 * @param buffer Output buffer (at least 32 bytes)
 * @param buffer_size Size of buffer
 */
void tracker_mac_get_info_string(const uint8_t* mac_addr, char* buffer, size_t buffer_size);

/**
 * @brief Save MAC count table to NVS
 *
 * Persists the MAC count table to flash.
 * Called automatically periodically and on shutdown.
 */
void tracker_mac_save_to_nvs(void);

/**
 * @brief Clear all MAC connection counts
 *
 * Resets the MAC count table to empty state.
 */
void tracker_mac_clear_all(void);

#ifdef __cplusplus
}
#endif

#endif /* CLIENT_TRACKER_H */

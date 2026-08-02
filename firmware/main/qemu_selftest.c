/**
 * @file qemu_selftest.c
 * @brief QEMU-only self-test battery (built only with PROMOBEACON_QEMU=1)
 *
 * Exercises every non-radio logic path with assertions so the emulator can
 * validate firmware behavior that would otherwise need physical hardware:
 *   - Config manager: get/save/load/reset round-trips
 *   - Client tracker: connect/disconnect/timeout/stats/CSV/serialize
 *   - Portal content: custom content set/load/CRC/transfer
 *   - Status collector: serialize + battery fallback
 *   - OTA subsystem: version/partition info (no actual OTA writes)
 *
 * Results are logged as "SELFTEST: PASS/FAIL <name>" lines; a final summary
 * line prints the totals so CI can grep for "SELFTEST: ALL PASSED".
 */

#include <string.h>
#include <stdio.h>
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_system.h"
#include "nvs.h"
#include "nvs_flash.h"

#include "config_manager.h"
#include "client_tracker.h"
#include "portal_content.h"
#include "status_collector.h"
#include "ota_update.h"

#define TAG "SELFTEST"

static int g_pass = 0;
static int g_fail = 0;

#define CHECK(cond, name) do {                                                  \
    if (cond) {                                                                 \
        g_pass++;                                                               \
        ESP_LOGI(TAG, "PASS: %s", name);                                        \
    } else {                                                                    \
        g_fail++;                                                               \
        ESP_LOGE(TAG, "FAIL: %s (line %d)", name, __LINE__);                    \
    }                                                                           \
} while (0)

/* ------------------------------------------------------------------ */
/* Test 1: Config manager round-trips                                   */
/* ------------------------------------------------------------------ */
static void test_config_manager(void)
{
    ESP_LOGI(TAG, "--- config manager ---");

    /* Make the test deterministic on re-runs: NVS may hold values from a
     * previous self-test run (e.g. promo text/device name). Reset to
     * defaults first so the "fresh device" assertions hold. Note:
     * reset_to_defaults() also erases the admin password, so check that
     * AFTER re-setting it below. */
    reset_configuration_state();
    reset_to_defaults();

    CHECK(is_config_initialized(), "config manager initialized");
    CHECK(is_device_configured() == false, "fresh device not configured");

    const DeviceConfig* cfg = get_config();
    CHECK(cfg != NULL, "get_config returns non-NULL");
    if (cfg) {
        CHECK(cfg->promo_text[0] != '\0', "promo text non-empty");
        CHECK(strlen(cfg->device_name) > 0, "device name non-empty");
        /* After reset_to_defaults() the admin password is cleared by
         * design; it is re-checked after the save/load round-trip. */
    }

    /* Promo text round-trip */
    esp_err_t ret = save_promo_text("SELFTEST-PROMO");
    CHECK(ret == ESP_OK, "save_promo_text OK");
    char buf[64] = {0};
    ret = load_promo_text(buf, sizeof(buf));
    CHECK(ret == ESP_OK && strcmp(buf, "SELFTEST-PROMO") == 0,
          "load_promo_text round-trip");

    /* SSID round-trip */
    ret = save_ssid("SELFTEST-SSID");
    CHECK(ret == ESP_OK, "save_ssid OK");
    buf[0] = 0;
    ret = load_ssid(buf, sizeof(buf));
    CHECK(ret == ESP_OK && strcmp(buf, "SELFTEST-SSID") == 0,
          "load_ssid round-trip");

    /* Device name round-trip */
    ret = save_device_name("SELFTEST-DEV");
    CHECK(ret == ESP_OK, "save_device_name OK");
    buf[0] = 0;
    ret = load_device_name(buf, sizeof(buf));
    CHECK(ret == ESP_OK && strcmp(buf, "SELFTEST-DEV") == 0,
          "load_device_name round-trip");

    /* Admin password round-trip (set a known one) */
    ret = save_admin_password("testpass123");
    CHECK(ret == ESP_OK, "save_admin_password OK");
    buf[0] = 0;
    ret = load_admin_password(buf, sizeof(buf));
    CHECK(ret == ESP_OK && strcmp(buf, "testpass123") == 0,
          "load_admin_password round-trip");
    CHECK(is_admin_password_set(), "admin password set after save");

    /* Configured flag */
    ret = set_device_configured();
    CHECK(ret == ESP_OK && is_device_configured() == true,
          "set_device_configured flips flag");

    /* Reset state (leave device in fresh state for other tests) */
    ret = reset_configuration_state();
    CHECK(ret == ESP_OK && is_device_configured() == false,
          "reset_configuration_state clears flag");
}

/* ------------------------------------------------------------------ */
/* Test 2: Client tracker                                               */
/* ------------------------------------------------------------------ */
static void test_client_tracker(void)
{
    ESP_LOGI(TAG, "--- client tracker ---");

    /* Deterministic start: wipe any history persisted by earlier runs */
    tracker_clear_all();

    tracker_stats_t stats;
    tracker_get_stats(&stats);
    CHECK(stats.total_connections == 0, "stats start at zero");

    /* Simulate a client connect (arbitrary MAC) */
    uint8_t mac1[6] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0x01};
    uint8_t mac2[6] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0x02};

    tracker_on_connect(mac1);
    tracker_on_request(mac1, "/", true, 512);
    tracker_on_request(mac1, "/index.html", false, 2048);

    tracker_on_connect(mac2);
    tracker_on_request(mac2, "/", true, 128);

    CHECK(tracker_check_timeouts(3600) == 0, "no timeouts while active");

    /* MAC connection count */
    tracker_mac_record_connection(mac1);
    tracker_mac_record_connection(mac1);
    tracker_mac_record_connection(mac2);
    uint32_t mac1_count = 0;
    /* Verify via a fresh lookup: count is stored, query via serialize/stats */
    /* (no direct getter exposed; verify totals instead) */

    /* Stats should reflect connections */
    tracker_get_stats(&stats);
    CHECK(stats.total_connections == 2, "two connections recorded");
    CHECK(stats.total_unique_clients >= 2, "two unique clients");
    CHECK(stats.active_sessions == 2, "two active sessions");

    /* Disconnect both clients so sessions land in history (ring buffer
     * only holds completed sessions) and requests/bytes get aggregated. */
    tracker_on_disconnect(mac1);
    tracker_on_disconnect(mac2);
    tracker_get_stats(&stats);
    CHECK(stats.active_sessions == 0, "no active sessions after disconnect");
    CHECK(stats.total_requests >= 3, "three requests recorded after disconnect");
    CHECK(stats.completed_sessions == 2, "two completed sessions");

    /* Session history (index 0 = oldest completed session) */
    client_session_t session;
    esp_err_t ret = tracker_get_session(0, &session);
    CHECK(ret == ESP_OK, "session 0 readable");
    if (ret == ESP_OK) {
        CHECK(session.is_still_connected == false, "session 0 completed");
        CHECK(session.request_count >= 1, "session 0 has requests");
        CHECK(session.bytes_received > 0, "session 0 bytes received");
    }

    /* BLE serialize should produce data now that history is populated */
    uint8_t ble_buf[512];
    uint16_t n = tracker_serialize_for_ble(ble_buf, sizeof(ble_buf), 0, 10);
    CHECK(n > 0, "tracker_serialize_for_ble produces data");

    /* CSV export — buffer on the heap: the main task stack is only 3584
     * bytes and tracker_get_csv_size() reports a 12000-byte estimate. */
    uint32_t csv_size = tracker_get_csv_size();
    CHECK(csv_size > 0, "CSV size > 0");
    char* csv = malloc(csv_size ? csv_size : 1);
    CHECK(csv != NULL, "CSV heap buffer allocated");
    if (csv) {
        uint32_t written = tracker_generate_csv(csv, csv_size);
        CHECK(written > 0, "CSV generation produces data");
        CHECK(strstr(csv, "AA:BB:CC:DD:EE:01") != NULL,
              "CSV contains MAC 1");
        free(csv);
    }

    /* Stats string */
    char stats_str[256];
    ret = tracker_get_stats_string(stats_str, sizeof(stats_str));
    CHECK(ret == ESP_OK && strlen(stats_str) > 0, "stats string generated");

    /* Timeout: no timeouts with a 1h threshold (clients just disconnected) */
    uint8_t timed_out = tracker_check_timeouts(3600);
    CHECK(timed_out == 0, "no timeouts with 1h threshold");
}

/* ------------------------------------------------------------------ */
/* Test 3: Portal content                                               */
/* ------------------------------------------------------------------ */
static void test_portal_content(void)
{
    ESP_LOGI(TAG, "--- portal content ---");

    CHECK(portal_content_get() != NULL, "portal content available");
    CHECK(portal_content_get_size() > 0, "portal content non-empty");
    CHECK(portal_content_is_custom() == false, "default content not custom");

    /* Custom content + CRC round-trip */
    const char* custom = "<html><body>QEMU TEST PORTAL</body></html>";
    esp_err_t ret = portal_content_set(custom, strlen(custom));
    CHECK(ret == ESP_OK, "portal_content_set OK");
    CHECK(portal_content_is_custom() == true, "content marked custom");

    /* CRC validation */
    uint32_t crc = portal_calculate_crc();
    CHECK(portal_validate_crc(crc) == true, "CRC validates");
    CHECK(portal_validate_crc(crc + 1) == false, "bad CRC rejected");

    /* Chunked transfer simulation */
    ret = portal_transfer_start(64, 0xDEADBEEF);
    CHECK(ret == ESP_OK, "portal_transfer_start OK");
    uint8_t chunk[32];
    memset(chunk, 'A', sizeof(chunk));
    ret = portal_transfer_process_chunk(0, chunk, sizeof(chunk));
    CHECK(ret == ESP_OK, "portal_transfer_process_chunk OK");
    ret = portal_transfer_process_chunk(1, chunk, sizeof(chunk));
    CHECK(ret == ESP_OK, "portal_transfer_process_chunk 2 OK");

    uint8_t tstatus = 0, tprogress = 0;
    portal_transfer_get_status(&tstatus, &tprogress);
    CHECK(tstatus == PORTAL_STATUS_RECEIVING || tstatus == PORTAL_STATUS_COMPLETE,
          "transfer status is receiving/complete");

    /* Abort cleans up (discards in-progress content) */
    portal_transfer_abort();
    CHECK(portal_transfer_get_status(&tstatus, &tprogress) == ESP_OK,
          "abort leaves valid status");

    /* Re-set custom content, then persistence: save to NVS, reset to
     * default, load back. (Abort above discarded the buffer by design.) */
    ret = portal_content_set(custom, strlen(custom));
    CHECK(ret == ESP_OK, "re-set content after abort");
    ret = portal_save_to_nvs();
    CHECK(ret == ESP_OK, "portal_save_to_nvs OK");
    ret = portal_reset_to_default();
    CHECK(ret == ESP_OK, "portal_reset_to_default OK");
    CHECK(portal_content_is_custom() == false, "reset clears custom flag");
    /* Reset wipes the NVS keys by design: loading must report NOT_FOUND. */
    ret = portal_load_from_nvs();
    CHECK(ret == ESP_ERR_NVS_NOT_FOUND, "load after reset reports NOT_FOUND");
    /* Full round-trip: set -> save -> load (no reset in between) proves the
     * NVS persistence path. */
    ret = portal_content_set(custom, strlen(custom));
    CHECK(ret == ESP_OK, "re-set after reset");
    ret = portal_save_to_nvs();
    CHECK(ret == ESP_OK, "save after reset");
    ret = portal_reset_to_default();
    CHECK(ret == ESP_OK, "reset again");
    CHECK(portal_content_is_custom() == false, "reset wipes custom flag");
    /* After reset, NVS keys are gone: load must report NOT_FOUND. */
    ret = portal_load_from_nvs();
    CHECK(ret == ESP_ERR_NVS_NOT_FOUND, "load after reset NOT_FOUND (2)");
    /* Now set + save + load to prove the full persistence round-trip. */
    ret = portal_content_set(custom, strlen(custom));
    CHECK(ret == ESP_OK, "set for round-trip");
    ret = portal_save_to_nvs();
    CHECK(ret == ESP_OK, "save for round-trip");
    ret = portal_load_from_nvs();
    CHECK(ret == ESP_OK, "portal_load_from_nvs OK");
    CHECK(portal_content_is_custom() == true, "load restores custom flag");

    /* Cleanup: delete custom so subsequent boots start default */
    portal_delete_custom_content();
    CHECK(portal_content_is_custom() == false, "delete clears custom");
}

/* ------------------------------------------------------------------ */
/* Test 4: Status collector                                             */
/* ------------------------------------------------------------------ */
static void test_status_collector(void)
{
    ESP_LOGI(TAG, "--- status collector ---");

    const StatusPacket* st = get_status();
    CHECK(st != NULL, "get_status non-NULL");

    update_status();
    st = get_status();

    CHECK(st->flags == 0x03, "flags indicate AP+BLE active");
    CHECK(st->battery_percent <= 100, "battery within range");
    CHECK(st->client_count == 0, "no clients connected");

    /* Serialize should produce 8 bytes with matching fields */
    uint8_t buf[8];
    serialize_status(buf);
    CHECK(buf[7] == st->battery_percent, "serialized battery matches");
    CHECK(buf[1] == st->client_count, "serialized client count matches");
    CHECK(buf[0] == st->flags, "serialized flags match");

    /* Battery fallback */
    uint8_t batt = get_battery_level();
    CHECK(batt <= 100, "battery level bounded");

    /* Client connected/disconnected callbacks maintain the portal-engagement
     * array; the authoritative client_count comes from esp_wifi_ap_get_sta_list()
     * in update_status() (always 0 in QEMU since WiFi is not emulated).
     * So assert the callbacks are safe to call and update_status stays sane. */
    uint8_t mac[6] = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06};
    on_client_connected(mac);
    on_client_disconnected(mac);
    update_status();
    st = get_status();
    CHECK(st->client_count == 0, "client count 0 (no WiFi in QEMU)");
    CHECK(get_connected_client_count() == st->client_count,
          "get_connected_client_count matches status");
}

/* ------------------------------------------------------------------ */
/* Test 5: OTA subsystem                                                */
/* ------------------------------------------------------------------ */
static void test_ota_subsystem(void)
{
    ESP_LOGI(TAG, "--- OTA subsystem ---");

    CHECK(get_firmware_version() != NULL, "firmware version string");
    CHECK(strlen(get_firmware_version()) > 0, "version non-empty");
    CHECK(get_firmware_version_int() > 0, "version int > 0");
    CHECK(ota_is_in_progress() == false, "no OTA in progress");

    char pinfo[256];
    ota_get_partition_info(pinfo, sizeof(pinfo));
    CHECK(strlen(pinfo) > 0, "partition info string");

    char stat_str[256];
    ota_get_status_string(stat_str, sizeof(stat_str));
    CHECK(strlen(stat_str) > 0, "status string non-empty");

    /* ota_mark_valid should be safe to call */
    ota_mark_valid();
    CHECK(true, "ota_mark_valid safe");
}

/* ------------------------------------------------------------------ */
/* Runner                                                              */
/* ------------------------------------------------------------------ */
void qemu_selftest_run(void)
{
    ESP_LOGI(TAG, "==============================================");
    ESP_LOGI(TAG, "QEMU self-test starting (PROMOBEACON_QEMU=1)");
    ESP_LOGI(TAG, "==============================================");

    test_config_manager();
    ESP_LOGI(TAG, "HEAP after config: %lu", (unsigned long)esp_get_free_heap_size());
    test_client_tracker();
    ESP_LOGI(TAG, "HEAP after tracker: %lu", (unsigned long)esp_get_free_heap_size());
    test_portal_content();
    ESP_LOGI(TAG, "HEAP after portal: %lu", (unsigned long)esp_get_free_heap_size());
    test_status_collector();
    ESP_LOGI(TAG, "HEAP after status: %lu", (unsigned long)esp_get_free_heap_size());
    test_ota_subsystem();
    ESP_LOGI(TAG, "HEAP after OTA: %lu", (unsigned long)esp_get_free_heap_size());

    ESP_LOGI(TAG, "==============================================");
    ESP_LOGI(TAG, "SELFTEST RESULT: %d passed, %d failed", g_pass, g_fail);
    if (g_fail == 0) {
        ESP_LOGI(TAG, "SELFTEST: ALL PASSED");
    } else {
        ESP_LOGE(TAG, "SELFTEST: FAILURES DETECTED");
    }
    ESP_LOGI(TAG, "==============================================");
}

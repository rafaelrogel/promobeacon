/**
 * Portal Content Manager Implementation
 *
 * Manages custom HTML content storage and retrieval for the captive portal.
 * Supports receiving content via BLE chunked transfer and storing in NVS flash.
 *
 * Architecture:
 * - Dual buffer system: working buffer for transfer, NVS for persistence
 * - CRC32 validation ensures data integrity
 * - Graceful fallback to default content on errors
 *
 * Author: MiniMax Agent
 * Version: 2.0.0
 */

#include "esp_rom_crc.h"
#include <inttypes.h>
#include "nvs.h"
#include "esp_flash.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include "esp_log.h"
#include "portal_content.h"
#include "index_html.h"

static const char* TAG = "PORTAL_CONTENT";


/* Default portal content - shown when no custom content is loaded */
static const char DEFAULT_HTML[] =
    "<!DOCTYPE html>"
    "<html>"
    "<head>"
    "<meta charset=\"UTF-8\">"
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
    "<title>PromoBeacon - %s</title>"
    "<style>"
    ":root{--p:#6366f1;--s:#a855f7;--bg:#0f172a;}"
    "*{margin:0;padding:0;box-sizing:border-box;font-family:'Outfit','Inter',sans-serif;}"
    "body{background:var(--bg);color:#f8fafc;min-height:100vh;display:flex;align-items:center;justify-content:center;overflow:hidden;}"
    ".bg{position:fixed;inset:0;background:radial-gradient(circle at 0% 0%, #4338ca 0%, transparent 50%), radial-gradient(circle at 100% 100%, #1e1b4b 0%, transparent 50%);z-index:-1;}"
    ".glass{background:rgba(30,41,59,0.7);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.1);border-radius:2rem;padding:3rem 2rem;max-width:400px;width:90%%;text-align:center;box-shadow:0 25px 50px -12px rgba(0,0,0,0.5);animation:slideUp 0.8s cubic-bezier(0.16,1,0.3,1);}"
    "h1{font-size:2.5rem;font-weight:900;background:linear-gradient(to right,#818cf8,#c084fc);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:1rem;}"
    "p{color:#94a3b8;font-size:1.1rem;line-height:1.6;margin-bottom:2.5rem;}"
    ".btn{display:inline-block;width:100%%;padding:1.25rem;background:linear-gradient(135deg,var(--p),var(--s));color:white;text-decoration:none;border-radius:1rem;font-weight:700;font-size:1.1rem;box-shadow:0 10px 15px -3px rgba(99,102,241,0.3);transition:transform 0.2s,filter 0.2s;}"
    ".btn:active{transform:scale(0.98);filter:brightness(1.1);}"
    "@keyframes slideUp{from{opacity:0;transform:translateY(30px);}to{opacity:1;transform:translateY(0);}}"
    "</style>"
    "</head>"
    "<body>"
    "<div class=\"bg\"></div>"
    "<div class=\"glass\">"
    "<h1>%s</h1>"
    "<p>Conectado à rede oficial PromoBeacon.<br>Acesse agora para ver ofertas exclusivas preparadas para você.</p>"
    "<a href=\"/connect\" class=\"btn\">Acessar Ofertas</a>"
    "</div>"
    "</body>"
    "</html>";

/* Static buffers and state */
static uint8_t* g_content_buffer = NULL;       /* Working buffer for content */
static uint32_t g_content_size = 0;            /* Current content size */
static uint32_t g_allocated_size = 0;          /* Allocated buffer size */

static portal_transfer_state_t g_transfer = {0}; /* Transfer state */
static bool g_initialized = false;              /* Initialization flag */
static bool g_is_custom = false;                /* Using custom content */

/* ============================================================================
 * CRC32 IMPLEMENTATION
 * ============================================================================ */

/**
 * @brief Calculate CRC32 for data integrity
 */
static uint32_t calculate_crc32(const uint8_t* buffer, size_t length)
{
    /* Standard IEEE 802.3 CRC32 - esp_rom_crc32_le handles seed/XOR internally when called with 0 */
    return esp_rom_crc32_le(0, buffer, length);
}

/* ============================================================================
 * NVS OPERATIONS
 * ============================================================================ */

/**
 * @brief Save content to NVS flash
 */
esp_err_t portal_save_to_nvs(void)
{
    if (g_content_buffer == NULL || g_content_size == 0) {
        return ESP_ERR_INVALID_ARG;
    }

    nvs_handle_t nvs_handle;
    esp_err_t ret = nvs_open(PORTAL_NVS_NAMESPACE, NVS_READWRITE, &nvs_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to open NVS: %s", esp_err_to_name(ret));
        return ret;
    }

    /* Calculate and store CRC */
    uint32_t crc = calculate_crc32(g_content_buffer, g_content_size);

    ret = nvs_set_blob(nvs_handle, PORTAL_NVS_CONTENT_KEY, g_content_buffer, g_content_size);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to write content: %s", esp_err_to_name(ret));
        nvs_close(nvs_handle);
        return ret;
    }

    ret = nvs_set_u32(nvs_handle, PORTAL_NVS_SIZE_KEY, g_content_size);
    if (ret != ESP_OK) {
        nvs_close(nvs_handle);
        return ret;
    }

    ret = nvs_set_u32(nvs_handle, PORTAL_NVS_CRC_KEY, crc);
    if (ret != ESP_OK) {
        nvs_close(nvs_handle);
        return ret;
    }

    ret = nvs_commit(nvs_handle);
    nvs_close(nvs_handle);

    if (ret == ESP_OK) {
        g_is_custom = true;
        ESP_LOGI(TAG, "Content saved to NVS: %" PRIu32 " bytes, CRC=0x%08" PRIX32, g_content_size, crc);
    }

    return ret;
}

/**
 * @brief Load content from NVS flash
 */
esp_err_t portal_load_from_nvs(void)
{
    nvs_handle_t nvs_handle;
    esp_err_t ret = nvs_open(PORTAL_NVS_NAMESPACE, NVS_READONLY, &nvs_handle);
    if (ret != ESP_OK) {
        ESP_LOGI(TAG, "No NVS content found, using default");
        g_is_custom = false;
        return ESP_ERR_NVS_NOT_FOUND;
    }

    /* Get content size */
    uint32_t size = 0;
    ret = nvs_get_u32(nvs_handle, PORTAL_NVS_SIZE_KEY, &size);
    if (ret == ESP_ERR_NVS_NOT_FOUND) {
        ESP_LOGI(TAG, "No saved content size (key absent)");
        nvs_close(nvs_handle);
        g_is_custom = false;
        return ESP_ERR_NVS_NOT_FOUND;
    }
    if (ret != ESP_OK || size == 0 || size > PORTAL_MAX_SIZE) {
        ESP_LOGW(TAG, "Invalid content size in NVS (ret=%s size=%lu)", esp_err_to_name(ret), (unsigned long)size);
        nvs_close(nvs_handle);
        g_is_custom = false;
        return ESP_ERR_INVALID_SIZE;
    }

    /* Allocate buffer if needed */
    if (g_allocated_size < size) {
        if (g_content_buffer) {
            free(g_content_buffer);
        }
        g_content_buffer = (uint8_t*)malloc(size + 1);
        if (g_content_buffer == NULL) {
            ESP_LOGE(TAG, "Failed to allocate buffer for NVS content");
            nvs_close(nvs_handle);
            return ESP_ERR_NO_MEM;
        }
        g_allocated_size = size + 1;
    }

    /* Read content */
    size_t read_size = size;
    ret = nvs_get_blob(nvs_handle, PORTAL_NVS_CONTENT_KEY, g_content_buffer, &read_size);
    if (ret != ESP_OK || read_size != size) {
        ESP_LOGE(TAG, "Failed to read content: %s", esp_err_to_name(ret));
        nvs_close(nvs_handle);
        return ret;
    }

    /* Verify CRC */
    uint32_t stored_crc;
    ret = nvs_get_u32(nvs_handle, PORTAL_NVS_CRC_KEY, &stored_crc);
    if (ret != ESP_OK) {
        ESP_LOGW(TAG, "No CRC found, skipping validation");
    } else {
        uint32_t calculated_crc = calculate_crc32(g_content_buffer, size);
        if (calculated_crc != stored_crc) {
            ESP_LOGE(TAG, "CRC mismatch: stored=0x%08" PRIX32 ", calculated=0x%08" PRIX32,
                     stored_crc, calculated_crc);
            nvs_close(nvs_handle);
            /* Try to recover by clearing invalid content */
            esp_err_t open_ret = nvs_open(PORTAL_NVS_NAMESPACE, NVS_READWRITE, &nvs_handle);
            if (open_ret == ESP_OK) {
                nvs_erase_key(nvs_handle, PORTAL_NVS_CONTENT_KEY);
                nvs_commit(nvs_handle);
                nvs_close(nvs_handle);
            } else {
                ESP_LOGE(TAG, "Recovery failed: cannot open NVS: %s", esp_err_to_name(open_ret));
            }
            g_is_custom = false;
            return ESP_ERR_INVALID_CRC;
        }
    }

    nvs_close(nvs_handle);

    g_content_buffer[size] = '\0';
    g_content_size = size;

    ESP_LOGI(TAG, "Loaded content from NVS: %" PRIu32 " bytes", g_content_size);
    g_is_custom = true;

    return ESP_OK;
}

/**
 * @brief Delete custom content from NVS
 */
esp_err_t portal_delete_custom_content(void)
{
    nvs_handle_t nvs_handle;
    esp_err_t ret = nvs_open(PORTAL_NVS_NAMESPACE, NVS_READWRITE, &nvs_handle);
    if (ret != ESP_OK) {
        return ret;
    }

    ret = nvs_erase_key(nvs_handle, PORTAL_NVS_CONTENT_KEY);
    if (ret != ESP_OK && ret != ESP_ERR_NVS_NOT_FOUND) {
        nvs_close(nvs_handle);
        return ret;
    }

    ret = nvs_erase_key(nvs_handle, PORTAL_NVS_SIZE_KEY);
    if (ret != ESP_OK && ret != ESP_ERR_NVS_NOT_FOUND) {
        nvs_close(nvs_handle);
        return ret;
    }

    ret = nvs_erase_key(nvs_handle, PORTAL_NVS_CRC_KEY);
    if (ret != ESP_OK && ret != ESP_ERR_NVS_NOT_FOUND) {
        nvs_close(nvs_handle);
        return ret;
    }

    ret = nvs_commit(nvs_handle);
    nvs_close(nvs_handle);

    if (ret == ESP_OK) {
        g_is_custom = false;
        ESP_LOGI(TAG, "Custom content deleted from NVS");
    }

    return ret;
}

/* ============================================================================
 * TRANSFER OPERATIONS
 * ============================================================================ */

/**
 * @brief Start portal content transfer
 */
esp_err_t portal_transfer_start(uint32_t total_size, uint32_t crc32)
{
    if (total_size == 0 || total_size > PORTAL_MAX_SIZE) {
        ESP_LOGE(TAG, "Invalid transfer size: %" PRIu32, total_size);
        return ESP_ERR_INVALID_SIZE;
    }

    /* Abort any existing transfer */
    portal_transfer_abort();

    /* Allocate buffer */
    if (g_content_buffer) free(g_content_buffer);
    g_content_buffer = (uint8_t*)malloc(total_size + 1);
    if (g_content_buffer == NULL) {
        ESP_LOGE(TAG, "Failed to allocate transfer buffer: %" PRIu32 " bytes", total_size);
        return ESP_ERR_NO_MEM;
    }

    memset(g_content_buffer, 0, total_size + 1);
    g_allocated_size = total_size + 1;
    g_content_size = total_size;

    /* Initialize transfer state */
    g_transfer.status = PORTAL_STATUS_RECEIVING;
    g_transfer.total_size = total_size;
    g_transfer.bytes_received = 0;
    g_transfer.expected_seq = 0;
    g_transfer.crc32 = crc32;
    g_transfer.buffer = g_content_buffer;

    ESP_LOGI(TAG, "Transfer started: %" PRIu32 " bytes, CRC=0x%08" PRIX32,
             (uint32_t)total_size, (uint32_t)crc32);

    return ESP_OK;
}

/**
 * @brief Process received data chunk
 */
esp_err_t portal_transfer_process_chunk(uint16_t seq_num, const uint8_t* data, uint16_t data_len)
{
    if (g_transfer.status != PORTAL_STATUS_RECEIVING) {
        ESP_LOGE(TAG, "Not in receiving state");
        return ESP_ERR_INVALID_STATE;
    }

    if (g_content_buffer == NULL) {
        ESP_LOGE(TAG, "No transfer buffer");
        return ESP_ERR_INVALID_STATE;
    }

    /* Check sequence number */
    if (seq_num != g_transfer.expected_seq) {
        ESP_LOGW(TAG, "Sequence mismatch: expected=%u, received=%u",
                 g_transfer.expected_seq, seq_num);
        /* Continue anyway - we might still recover */
    }

    /* Check bounds */
    if (g_transfer.bytes_received + data_len > g_transfer.total_size) {
        ESP_LOGE(TAG, "Buffer overflow: %lu + %u > %lu",
                 (unsigned long)g_transfer.bytes_received, data_len,
                 (unsigned long)g_transfer.total_size);
        portal_transfer_abort();
        return ESP_ERR_INVALID_SIZE;
    }

    /* Copy data to buffer */
    memcpy(g_content_buffer + g_transfer.bytes_received, data, data_len);
    g_transfer.bytes_received += data_len;
    g_transfer.expected_seq++;

    ESP_LOGD(TAG, "Chunk %" PRIu16 ": %" PRIu16 " bytes, total: %" PRIu32 " / %" PRIu32,
             seq_num, data_len,
             (uint32_t)g_transfer.bytes_received,
             (uint32_t)g_transfer.total_size);

    return ESP_OK;
}

/**
 * @brief Complete portal content transfer
 */
esp_err_t portal_transfer_complete(void)
{
    if (g_transfer.status != PORTAL_STATUS_RECEIVING) {
        return ESP_ERR_INVALID_STATE;
    }

    /* Verify we received all bytes */
    if (g_transfer.bytes_received != g_content_size) {
        ESP_LOGE(TAG, "Transfer size mismatch: received=%" PRIu32 ", expected=%" PRIu32,
                 (uint32_t)g_transfer.bytes_received,
                 (uint32_t)g_content_size);
        portal_transfer_abort();
        return ESP_ERR_INVALID_SIZE;
    }

    /* Verify CRC */
    uint32_t calculated_crc = calculate_crc32(g_content_buffer, g_content_size);
    if (calculated_crc != g_transfer.crc32) {
        ESP_LOGE(TAG, "CRC mismatch: expected=0x%08" PRIX32 ", calculated=0x%08" PRIX32,
                 g_transfer.crc32, calculated_crc);
        portal_transfer_abort();
        return ESP_ERR_INVALID_CRC;
    }

    /* Null terminate */
    g_content_buffer[g_content_size] = '\0';

    /* Save to NVS */
    esp_err_t ret = portal_save_to_nvs();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to save to NVS: %s", esp_err_to_name(ret));
        portal_transfer_abort();
        return ret;
    }

    /* Keep the buffer in memory for immediate serving */
    g_is_custom = true;
    g_transfer.status = PORTAL_STATUS_COMPLETE;
    g_transfer.buffer = NULL; /* Just clear the transfer pointer, keep g_content_buffer */

    ESP_LOGI(TAG, "Transfer complete: %" PRIu32 " bytes saved and active", g_content_size);

    return ESP_OK;
}

/**
 * @brief Abort portal content transfer
 */
void portal_transfer_abort(void)
{
    if (g_transfer.buffer) {
        free(g_transfer.buffer);
        g_transfer.buffer = NULL;
    }
    
    g_content_buffer = NULL;
    g_content_size = 0;
    /* The buffer backing g_content_buffer was freed above; reset the
     * allocation bookkeeping too, otherwise a later portal_content_set()
     * or portal_load_from_nvs() sees g_allocated_size >= needed size and
     * memcpy()s into a dangling pointer (use-after-free -> crash). */
    g_allocated_size = 0;

    memset(&g_transfer, 0, sizeof(portal_transfer_state_t));
    g_transfer.status = PORTAL_STATUS_IDLE;

    ESP_LOGI(TAG, "Transfer aborted");
}

/**
 * @brief Get current transfer status
 */
esp_err_t portal_transfer_get_status(uint8_t* status, uint8_t* progress)
{
    if (!status || !progress) {
        return ESP_ERR_INVALID_ARG;
    }

    *status = g_transfer.status;

    if (g_transfer.status == PORTAL_STATUS_RECEIVING && g_transfer.total_size > 0) {
        *progress = (uint8_t)((g_transfer.bytes_received * 100) / g_transfer.total_size);
    } else {
        *progress = 0;
    }

    return ESP_OK;
}

/* ============================================================================
 * CONTENT MANAGEMENT
 * ============================================================================ */

/**
 * @brief Initialize portal content manager
 */
esp_err_t portal_content_init(void)
{
    if (g_initialized) {
        ESP_LOGW(TAG, "Already initialized");
        return ESP_OK;
    }

    ESP_LOGI(TAG, "Initializing portal content manager");

    /* Initialize transfer state */
    memset(&g_transfer, 0, sizeof(portal_transfer_state_t));
    g_transfer.status = PORTAL_STATUS_IDLE;

    /* Try to load custom content from NVS */
    esp_err_t ret = portal_load_from_nvs();
    if (ret != ESP_OK) {
        /* Use default content - pointer to default HTML */
        g_content_buffer = NULL;
        g_content_size = 0;
        g_is_custom = false;
    }

    g_initialized = true;

    ESP_LOGI(TAG, "Portal content manager initialized, custom=%s",
             g_is_custom ? "yes" : "no");

    return ESP_OK;
}

/**
 * @brief Deinitialize portal content manager
 */
void portal_content_deinit(void)
{
    if (!g_initialized) {
        return;
    }

    ESP_LOGI(TAG, "Deinitializing portal content manager");

    /* Abort any ongoing transfer */
    portal_transfer_abort();

    /* Free content buffer if allocated */
    if (g_content_buffer && !g_is_custom) {
        /* Buffer was from NVS load, should keep it */
    }

    if (g_content_buffer != NULL) {
        free(g_content_buffer);
    }
    g_content_buffer = NULL;
    g_content_size = 0;
    g_allocated_size = 0;
    g_is_custom = false;

    g_initialized = false;

    ESP_LOGI(TAG, "Portal content manager deinitialized");
}

/**
 * @brief Get portal content for serving
 */
const char* portal_content_get(void)
{
    if (g_content_buffer != NULL && g_content_size > 0) {
        return (const char*)g_content_buffer;
    }

    /* Fallback to robust embedded index.html */
    return INDEX_HTML;
}

esp_err_t portal_content_set(const char* content, size_t length)
{
    if (!content || length == 0 || length > PORTAL_MAX_SIZE) {
        return ESP_ERR_INVALID_ARG;
    }

    if (g_allocated_size < length + 1) {
        if (g_content_buffer) free(g_content_buffer);
        g_content_buffer = (uint8_t*)malloc(length + 1);
        if (g_content_buffer == NULL) return ESP_ERR_NO_MEM;
        g_allocated_size = length + 1;
    }

    memcpy(g_content_buffer, content, length);
    g_content_buffer[length] = '\0';
    g_content_size = length;
    g_is_custom = true;

    return portal_save_to_nvs();
}

/**
 * @brief Get portal content size
 */
size_t portal_content_get_size(void)
{
    if (g_is_custom) {
        return g_content_size;
    }
    
    /* Size of robust embedded index.html */
    return strlen(INDEX_HTML);
}

/**
 * @brief Check if custom content is loaded
 */
bool portal_content_is_custom(void)
{
    return g_is_custom;
}

/**
 * @brief Get portal content information
 */
esp_err_t portal_get_info(portal_content_info_t* info)
{
    if (!info) {
        return ESP_ERR_INVALID_ARG;
    }

    info->size = g_content_size;
    info->valid = (g_content_buffer != NULL && g_content_size > 0);
    info->exists = g_is_custom;

    if (info->valid && info->exists) {
        info->crc32 = calculate_crc32(g_content_buffer, g_content_size);
    } else {
        info->crc32 = 0;
    }

    return ESP_OK;
}

/**
 * @brief Reset to default content
 */
esp_err_t portal_reset_to_default(void)
{
    esp_err_t ret = portal_delete_custom_content();

    /* Free custom content buffer if loaded */
    if (g_content_buffer && g_is_custom) {
        free(g_content_buffer);
        g_content_buffer = NULL;
        /* Keep allocation bookkeeping in sync: a later portal_content_set()
         * or portal_load_from_nvs() must reallocate instead of writing into
         * the freed buffer. */
        g_allocated_size = 0;
    }

    g_content_size = 0;
    g_is_custom = false;

    return ret;
}

/**
 * @brief Validate content CRC32
 */
bool portal_validate_crc(uint32_t expected_crc)
{
    if (g_content_buffer == NULL || g_content_size == 0) {
        return false;
    }

    uint32_t calculated = calculate_crc32(g_content_buffer, g_content_size);
    return (calculated == expected_crc);
}

/**
 * @brief Calculate CRC32 of content
 */
uint32_t portal_calculate_crc(void)
{
    if (g_content_buffer == NULL || g_content_size == 0) {
        return 0;
    }

    return calculate_crc32(g_content_buffer, g_content_size);
}

/**
 * @brief Send transfer status notification (stub for BLE integration)
 */
void portal_notify_status(uint8_t status, uint8_t progress)
{
    /* This will be called by ble_manager when we integrate */
    ESP_LOGD(TAG, "Status notification: status=%u, progress=%u%%", status, progress);
}

/**
 * @brief Get default HTML with promo text substituted
 */
const char* portal_get_default_html(const char* promo_text)
{
    static char default_buffer[8192];
    const char* text = promo_text ? promo_text : "Welcome!";
    snprintf(default_buffer, sizeof(default_buffer), DEFAULT_HTML, text, text);
    return default_buffer;
}

/**
 * @brief Get default HTML with promo text and device ID
 */
const char* portal_get_default_html_with_id(const char* promo_text, const char* device_id)
{
    static char default_buffer[2048];
    const char* text = promo_text ? promo_text : "Welcome!";
    const char* id = device_id ? device_id : "PB-UNKNOWN";

    /* Generate HTML with device ID in corner */
    snprintf(default_buffer, sizeof(default_buffer),
        "<!DOCTYPE html><html><head><meta charset=\"UTF-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
        "<title>%s</title>"
        "<style>"
        ":root{--p:#6366f1;--s:#a855f7;--bg:#0f172a;}"
        "*{margin:0;padding:0;box-sizing:border-box;font-family:sans-serif;}"
        "body{background:var(--bg);color:#f8fafc;min-height:100vh;display:flex;align-items:center;justify-content:center;}"
        ".bg{position:fixed;inset:0;background:radial-gradient(circle at 0%% 0%%,#4338ca 0%%,transparent 50%%),radial-gradient(circle at 100%% 100%%,#1e1b4b 0%%,transparent 50%%);z-index:-1;}"
        ".glass{background:rgba(30,41,59,0.7);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,0.1);border-radius:2rem;padding:2.5rem 1.5rem;max-width:380px;width:95%%;text-align:center;box-shadow:0 10px 30px rgba(0,0,0,0.5);}"
        "h1{font-size:2.2rem;font-weight:800;background:linear-gradient(to right,#818cf8,#c084fc);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:1rem;}"
        "p{color:#94a3b8;font-size:1rem;line-height:1.5;margin-bottom:2rem;}"
        ".btn{display:inline-block;width:100%%;padding:1rem;background:linear-gradient(135deg,var(--p),var(--s));color:white;text-decoration:none;border-radius:0.75rem;font-weight:700;}"
        ".id{margin-top:2rem;color:rgba(255,255,255,0.2);font-size:10px;font-family:monospace;}"
        "</style></head><body><div class=\"bg\"></div>"
        "<div class=\"glass\"><h1>%s</h1>"
        "<p>Você está conectado à rede PromoBeacon.<br>Clique abaixo para acessar as ofertas.</p>"
        "<a href=\"/connect\" class=\"btn\">Acessar Ofertas</a>"
        "<div class=\"id\">ID: %s</div></div></body></html>",
        text, text, id);

    return default_buffer;
}

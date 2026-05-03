/**
 * Configuration Manager Implementation
 * 
 * Manages persistent configuration storage using NVS.
 * Stores promotion text, portal HTML, WiFi password, and mode settings.
 */

#include "config_manager.h"
#include "esp_log.h"
#include "esp_err.h"
#include "esp_wifi.h"
#include "nvs.h"
#include "esp_flash.h"
#include "esp_random.h"
#include <string.h>
#include <stdlib.h>
#include <inttypes.h>
#include "esp_mac.h"

static const char* TAG = "CONFIG";

/* Configuration storage */
static DeviceConfig current_config;
static bool config_initialized = false;
static bool device_configured = false;


/**
 * @brief Initialize configuration manager
 */
esp_err_t init_config_manager(void)
{
    esp_err_t ret;
    
    if (config_initialized) {
        ESP_LOGW(TAG, "Config manager already initialized");
        return ESP_OK;
    }
    
    ESP_LOGI(TAG, "Initializing configuration manager");
    
    /* Load configuration from NVS */
    ret = load_promo_text(current_config.promo_text, sizeof(current_config.promo_text));
    if (ret != ESP_OK) {
        /* Use default promotion text */
        strncpy(current_config.promo_text, DEFAULT_PROMO_TEXT, 
                MAX_PROMO_TEXT_LENGTH);
        current_config.promo_text[MAX_PROMO_TEXT_LENGTH] = '\0';
    }
    
    /* Load WiFi password */
    ret = load_wifi_password(current_config.wifi_password, sizeof(current_config.wifi_password));
    if (ret != ESP_OK) {
        current_config.wifi_password[0] = '\0';
        current_config.wifi_encrypted = false;
    } else {
        current_config.wifi_encrypted = strlen(current_config.wifi_password) > 0;
    }
    
    /* Load device name */
    ret = load_device_name(current_config.device_name, sizeof(current_config.device_name));
    if (ret != ESP_OK) {
        strncpy(current_config.device_name, DEFAULT_DEVICE_NAME, MAX_DEVICE_NAME_LENGTH);
        current_config.device_name[MAX_DEVICE_NAME_LENGTH] = '\0';
    }
    
    /* Load admin password */
    ret = load_admin_password(current_config.admin_password, sizeof(current_config.admin_password));
    if (ret != ESP_OK || current_config.admin_password[0] == '\0') {
        {
            const char charset[] = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789";
            char random_pwd[9];
            for (int i = 0; i < 8; i++) {
                uint32_t rand_val = esp_random();
                random_pwd[i] = charset[rand_val % (sizeof(charset) - 1)];
            }
            random_pwd[8] = '\0';
            strncpy(current_config.admin_password, random_pwd, MAX_PASSWORD_LENGTH);
            current_config.admin_password[MAX_PASSWORD_LENGTH] = '\0';
            save_admin_password(random_pwd);
            ESP_LOGW(TAG, "============================================");
            ESP_LOGW(TAG, "DEFAULT ADMIN PASSWORD: %s", random_pwd);
            ESP_LOGW(TAG, "Write this down! It will be required for admin access.");
            ESP_LOGW(TAG, "============================================");
        }
    }

    /* Load configuration state */
    nvs_handle_t state_handle;
    ret = nvs_open(CONFIG_NAMESPACE, NVS_READONLY, &state_handle);
    if (ret == ESP_OK) {
        int8_t configured = 0;
        ret = nvs_get_i8(state_handle, KEY_IS_CONFIGURED, &configured);
        if (ret == ESP_OK) {
            device_configured = (configured != 0);
        } else if (ret == ESP_ERR_NVS_NOT_FOUND) {
            device_configured = false;  /* Fresh device */
        }
        nvs_close(state_handle);
    }

    config_initialized = true;
    
    ESP_LOGI(TAG, "Configuration loaded");
    ESP_LOGI(TAG, "Promo text: %s", current_config.promo_text);
    ESP_LOGI(TAG, "WiFi encrypted: %s", 
             current_config.wifi_encrypted ? "yes" : "no");
    ESP_LOGI(TAG, "Device name: %s", current_config.device_name);
    ESP_LOGI(TAG, "Admin password: %s", 
             current_config.admin_password[0] ? "set" : "not set");
    ESP_LOGI(TAG, "Device configured: %s", device_configured ? "yes" : "no");
    
    return ESP_OK;
}

/**
 * @brief Deinitialize configuration manager
 */
void deinit_config_manager(void)
{
    if (!config_initialized) {
        return;
    }
    
    ESP_LOGI(TAG, "Configuration manager deinitialized");
    config_initialized = false;
}

/**
 * @brief Get current configuration
 */
const DeviceConfig* get_config(void)
{
    return &current_config;
}

/**
 * @brief Save promotion text
 * Note: Promotion text and SSID are intentionally kept identical by design.
 */
esp_err_t save_promo_text(const char* promo_text)
{
    if (!promo_text || strlen(promo_text) == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    
    nvs_handle_t handle;
    esp_err_t ret;
    
    ret = nvs_open(CONFIG_NAMESPACE, NVS_READWRITE, &handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS open failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    char truncated[MAX_PROMO_TEXT_LENGTH + 1];
    strncpy(truncated, promo_text, MAX_PROMO_TEXT_LENGTH);
    truncated[MAX_PROMO_TEXT_LENGTH] = '\0';

    ret = nvs_set_str(handle, KEY_PROMO_TEXT, truncated);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS write failed: %s", esp_err_to_name(ret));
        nvs_close(handle);
        return ret;
    }
    
    ret = nvs_commit(handle);
    nvs_close(handle);
    
    if (ret == ESP_OK) {
        /* Update local copy */
        strncpy(current_config.promo_text, promo_text, MAX_PROMO_TEXT_LENGTH);
        current_config.promo_text[MAX_PROMO_TEXT_LENGTH] = '\0';
        ESP_LOGI(TAG, "Promo text saved: %s", promo_text);
    }
    
    return ret;
}

/**
 * @brief Load promotion text
 */
esp_err_t load_promo_text(char* buffer, size_t buffer_size)
{
    if (!buffer || buffer_size == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    
    nvs_handle_t handle;
    esp_err_t ret;
    
    ret = nvs_open(CONFIG_NAMESPACE, NVS_READONLY, &handle);
    if (ret != ESP_OK) {
        return ret;
    }
    
    size_t required_size = buffer_size;
    ret = nvs_get_str(handle, KEY_PROMO_TEXT, buffer, &required_size);
    nvs_close(handle);
    
    if (ret == ESP_ERR_NVS_NOT_FOUND) {
        /* Use default */
        strncpy(buffer, DEFAULT_PROMO_TEXT, buffer_size - 1);
        buffer[buffer_size - 1] = '\0';
        return ESP_OK;
    }
    
    return ret;
}

/**
 * @brief Save SSID
 * Note: SSID and promotion text are intentionally kept identical by design.
 */
esp_err_t save_ssid(const char* ssid)
{
    if (!ssid || strlen(ssid) == 0) {
        return ESP_ERR_INVALID_ARG;
    }

    nvs_handle_t handle;
    esp_err_t ret;

    ret = nvs_open(CONFIG_NAMESPACE, NVS_READWRITE, &handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS open failed: %s", esp_err_to_name(ret));
        return ret;
    }

    char truncated[MAX_SSID_LENGTH + 1];
    strncpy(truncated, ssid, MAX_SSID_LENGTH);
    truncated[MAX_SSID_LENGTH] = '\0';

    ret = nvs_set_str(handle, KEY_SSID, truncated);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS write failed: %s", esp_err_to_name(ret));
        nvs_close(handle);
        return ret;
    }

    ret = nvs_commit(handle);
    nvs_close(handle);

    if (ret == ESP_OK) {
        /* Update local copy — SSID maps to promo_text field */
        strncpy(current_config.promo_text, ssid, MAX_PROMO_TEXT_LENGTH);
        current_config.promo_text[MAX_PROMO_TEXT_LENGTH] = '\0';
        ESP_LOGI(TAG, "SSID saved: %s", ssid);
    }

    return ret;
}

/**
 * @brief Load SSID
 */
esp_err_t load_ssid(char* buffer, size_t buffer_size)
{
    if (!buffer || buffer_size == 0) {
        return ESP_ERR_INVALID_ARG;
    }

    nvs_handle_t handle;
    esp_err_t ret;

    ret = nvs_open(CONFIG_NAMESPACE, NVS_READONLY, &handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS open failed: %s", esp_err_to_name(ret));
        return ret;
    }

    size_t required_size = buffer_size;
    ret = nvs_get_str(handle, KEY_SSID, buffer, &required_size);
    nvs_close(handle);

    if (ret == ESP_ERR_NVS_NOT_FOUND) {
        /* Use default promo text as SSID */
        strncpy(buffer, DEFAULT_PROMO_TEXT, buffer_size - 1);
        buffer[buffer_size - 1] = '\0';
        return ESP_OK;
    }

    return ret;
}

/**
 * @brief Save portal HTML
 */
esp_err_t save_portal_html(const char* html_content, size_t length)
{
    if (!html_content || length == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    
    if (length > MAX_PORTAL_HTML_SIZE) {
        ESP_LOGE(TAG, "HTML content too large: %zu (max %d)", 
                 length, (int)MAX_PORTAL_HTML_SIZE);
        return ESP_ERR_INVALID_SIZE;
    }
    
    nvs_handle_t handle;
    esp_err_t ret;
    
    ret = nvs_open(CONFIG_NAMESPACE, NVS_READWRITE, &handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS open failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    ret = nvs_set_blob(handle, KEY_PORTAL_HTML, html_content, length);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS blob write failed: %s", esp_err_to_name(ret));
        nvs_close(handle);
        return ret;
    }
    
    ret = nvs_commit(handle);
    nvs_close(handle);
    
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "Portal HTML saved: %zu bytes", length);
    }
    
    return ret;
}

/**
 * @brief Load portal HTML
 */
ssize_t load_portal_html(char* buffer, size_t buffer_size)
{
    if (!buffer || buffer_size == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    
    nvs_handle_t handle;
    esp_err_t ret;
    
    ret = nvs_open(CONFIG_NAMESPACE, NVS_READONLY, &handle);
    if (ret != ESP_OK) {
        return ret;
    }
    
    size_t required_size = buffer_size;
    ret = nvs_get_blob(handle, KEY_PORTAL_HTML, buffer, &required_size);
    nvs_close(handle);
    
    if (ret == ESP_ERR_NVS_NOT_FOUND) {
        return 0;  /* No custom HTML stored */
    }
    
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS blob read failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    ESP_LOGI(TAG, "Portal HTML loaded: %zu bytes", required_size);
    
    return required_size;
}

/**
 * @brief Save WiFi password
 */
esp_err_t save_wifi_password(const char* password)
{
    nvs_handle_t handle;
    esp_err_t ret;
    
    ret = nvs_open(CONFIG_NAMESPACE, NVS_READWRITE, &handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS open failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    if (password && strlen(password) >= 8) {
        ret = nvs_set_str(handle, KEY_WIFI_PASSWORD, password);
        current_config.wifi_encrypted = true;
    } else {
        ret = nvs_erase_key(handle, KEY_WIFI_PASSWORD);
        current_config.wifi_encrypted = false;
    }
    
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS write failed: %s", esp_err_to_name(ret));
        nvs_close(handle);
        return ret;
    }
    
    ret = nvs_commit(handle);
    nvs_close(handle);
    
    if (ret == ESP_OK) {
        if (password && strlen(password) >= 8) {
            strncpy(current_config.wifi_password, password, MAX_PASSWORD_LENGTH);
            current_config.wifi_password[MAX_PASSWORD_LENGTH] = '\0';
        } else {
            current_config.wifi_password[0] = '\0';
        }
        ESP_LOGI(TAG, "WiFi password saved: %s", 
                 current_config.wifi_encrypted ? "enabled" : "disabled");
    }
    
    return ret;
}

/**
 * @brief Load WiFi password
 */
esp_err_t load_wifi_password(char* buffer, size_t buffer_size)
{
    if (!buffer || buffer_size == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    
    nvs_handle_t handle;
    esp_err_t ret;
    
    ret = nvs_open(CONFIG_NAMESPACE, NVS_READONLY, &handle);
    if (ret != ESP_OK) {
        return ret;
    }
    
    size_t required_size = buffer_size;
    ret = nvs_get_str(handle, KEY_WIFI_PASSWORD, buffer, &required_size);
    nvs_close(handle);
    
    if (ret == ESP_ERR_NVS_NOT_FOUND) {
        buffer[0] = '\0';
        return ESP_OK;
    }
    
    return ret;
}

/**
 * @brief Save device name
 */
esp_err_t save_device_name(const char* name)
{
    nvs_handle_t handle;
    esp_err_t ret;
    
    ret = nvs_open(CONFIG_NAMESPACE, NVS_READWRITE, &handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS open failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    if (name && strlen(name) > 0) {
        char truncated[MAX_DEVICE_NAME_LENGTH + 1];
        strncpy(truncated, name, MAX_DEVICE_NAME_LENGTH);
        truncated[MAX_DEVICE_NAME_LENGTH] = '\0';

        ret = nvs_set_str(handle, KEY_DEVICE_NAME, truncated);
    } else {
        ret = nvs_erase_key(handle, KEY_DEVICE_NAME);
    }
    
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS write failed: %s", esp_err_to_name(ret));
        nvs_close(handle);
        return ret;
    }
    
    ret = nvs_commit(handle);
    nvs_close(handle);
    
    if (ret == ESP_OK) {
        if (name && strlen(name) > 0) {
            strncpy(current_config.device_name, name, MAX_DEVICE_NAME_LENGTH);
            current_config.device_name[MAX_DEVICE_NAME_LENGTH] = '\0';
        } else {
            strncpy(current_config.device_name, DEFAULT_DEVICE_NAME, MAX_DEVICE_NAME_LENGTH);
            current_config.device_name[MAX_DEVICE_NAME_LENGTH] = '\0';
        }
        ESP_LOGI(TAG, "Device name saved: %s", current_config.device_name);
    }
    
    return ret;
}

/**
 * @brief Load device name
 */
esp_err_t load_device_name(char* buffer, size_t buffer_size)
{
    if (!buffer || buffer_size == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    
    nvs_handle_t handle;
    esp_err_t ret;
    
    ret = nvs_open(CONFIG_NAMESPACE, NVS_READONLY, &handle);
    if (ret != ESP_OK) {
        return ret;
    }
    
    size_t required_size = buffer_size;
    ret = nvs_get_str(handle, KEY_DEVICE_NAME, buffer, &required_size);
    nvs_close(handle);
    
    if (ret == ESP_ERR_NVS_NOT_FOUND) {
        /* Use default device name */
        strncpy(buffer, DEFAULT_DEVICE_NAME, buffer_size - 1);
        buffer[buffer_size - 1] = '\0';
        return ESP_OK;
    }
    
    return ret;
}

/**
 * @brief Save admin password
 */
esp_err_t save_admin_password(const char* password)
{
    nvs_handle_t handle;
    esp_err_t ret;
    
    ret = nvs_open(CONFIG_NAMESPACE, NVS_READWRITE, &handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS open failed: %s", esp_err_to_name(ret));
        return ret;
    }
    
    if (password && strlen(password) >= MIN_ADMIN_PASSWORD_LENGTH) {
        ret = nvs_set_str(handle, KEY_ADMIN_PASSWORD, password);
    } else {
        ret = nvs_erase_key(handle, KEY_ADMIN_PASSWORD);
    }
    
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS write failed: %s", esp_err_to_name(ret));
        nvs_close(handle);
        return ret;
    }
    
    ret = nvs_commit(handle);
    nvs_close(handle);
    
    if (ret == ESP_OK) {
        if (password && strlen(password) >= MIN_ADMIN_PASSWORD_LENGTH) {
            strncpy(current_config.admin_password, password, MAX_PASSWORD_LENGTH);
            current_config.admin_password[MAX_PASSWORD_LENGTH] = '\0';
        } else {
            current_config.admin_password[0] = '\0';
        }
        ESP_LOGI(TAG, "Admin password saved: %s", 
                 current_config.admin_password[0] ? "enabled" : "disabled");
    }
    
    return ret;
}

/**
 * @brief Load admin password
 */
esp_err_t load_admin_password(char* buffer, size_t buffer_size)
{
    if (!buffer || buffer_size == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    
    nvs_handle_t handle;
    esp_err_t ret;
    
    ret = nvs_open(CONFIG_NAMESPACE, NVS_READONLY, &handle);
    if (ret != ESP_OK) {
        return ret;
    }
    
    size_t required_size = buffer_size;
    ret = nvs_get_str(handle, KEY_ADMIN_PASSWORD, buffer, &required_size);
    nvs_close(handle);
    
    if (ret == ESP_ERR_NVS_NOT_FOUND) {
        buffer[0] = '\0';
        return ESP_OK;
    }
    
    return ret;
}

/**
 * @brief Check if admin password is set
 */
bool is_admin_password_set(void)
{
    return current_config.admin_password[0] != '\0';
}

/**
 * @brief Verify admin password
 */
bool verify_admin_password(const char* password)
{
    if (!password) return false;
    
    const char *stored = current_config.admin_password;
    size_t pw_len = strlen(stored);
    size_t in_len = strlen(password);
    
    volatile int match = (pw_len != in_len);
    volatile const char *s = stored;
    volatile const char *p = password;
    size_t max_len = MAX_PASSWORD_LENGTH;
    for (size_t i = 0; i < max_len; i++) {
        char sc = (i < pw_len) ? s[i] : 0;
        char pc = (i < in_len) ? p[i] : 0;
        match |= (sc ^ pc);
    }
    return match == 0;
}

/**
 * @brief Check if configuration is initialized
 */
bool is_config_initialized(void)
{
    return config_initialized;
}

/**
 * @brief Check if device has been configured
 */
bool is_device_configured(void)
{
    return device_configured;
}

/**
 * @brief Mark device as configured
 */
esp_err_t set_device_configured(void)
{
    nvs_handle_t handle;
    esp_err_t ret;

    ret = nvs_open(CONFIG_NAMESPACE, NVS_READWRITE, &handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS open failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = nvs_set_i8(handle, KEY_IS_CONFIGURED, 1);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS write failed: %s", esp_err_to_name(ret));
        nvs_close(handle);
        return ret;
    }

    ret = nvs_commit(handle);
    nvs_close(handle);

    if (ret == ESP_OK) {
        device_configured = true;
        ESP_LOGI(TAG, "Device marked as configured - web portal locked");
    }

    return ret;
}

/**
 * @brief Reset configuration state
 */
esp_err_t reset_configuration_state(void)
{
    nvs_handle_t handle;
    esp_err_t ret;

    ret = nvs_open(CONFIG_NAMESPACE, NVS_READWRITE, &handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS open failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = nvs_set_i8(handle, KEY_IS_CONFIGURED, 0);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS write failed: %s", esp_err_to_name(ret));
        nvs_close(handle);
        return ret;
    }

    ret = nvs_commit(handle);
    nvs_close(handle);

    if (ret == ESP_OK) {
        device_configured = false;
        ESP_LOGI(TAG, "Configuration state reset - web portal unlocked");
    }

    return ret;
}

/**
 * @brief Get unique device identifier
 */
esp_err_t get_device_id(char* buffer, size_t buffer_size)
{
    if (!buffer || buffer_size < MAX_DEVICE_ID_LENGTH) {
        return ESP_ERR_INVALID_ARG;
    }

    uint8_t mac[6];
    esp_err_t ret = esp_read_mac(mac, ESP_MAC_WIFI_STA);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to read MAC address: %s", esp_err_to_name(ret));
        /* Fallback to a generated ID based on internal flash ID */
        uint32_t flash_id;
        ret = esp_flash_read_id(NULL, &flash_id);
        if (ret == ESP_OK) {
            snprintf(buffer, buffer_size, "PB-%06" PRIX32, flash_id & 0xFFFFFF);
            return ESP_OK;
        }
        /* Last resort: use a placeholder */
        snprintf(buffer, buffer_size, "PB-UNKNOWN");
        return ESP_OK;
    }

    /* Format: PB-XXXXXX where XXXXXX is last 6 hex digits of MAC */
    snprintf(buffer, buffer_size, "PB-%02X%02X%02X%02X%02X%02X",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

    ESP_LOGI(TAG, "Device ID: %s", buffer);

    return ESP_OK;
}

/**
 * @brief Generate a random authentication token
 */
esp_err_t generate_auth_token(char* buffer, size_t buffer_size)
{
    if (!buffer || buffer_size < (AUTH_TOKEN_LENGTH * 2 + 1)) {
        return ESP_ERR_INVALID_ARG;
    }

    /* Generate random bytes using ESP32 hardware RNG */
    /* NOTE: esp_fill_random() returns void, it always succeeds */
    uint8_t token_bytes[AUTH_TOKEN_LENGTH];
    esp_fill_random(token_bytes, AUTH_TOKEN_LENGTH);

    /* Convert to hex string */
    for (int i = 0; i < AUTH_TOKEN_LENGTH; i++) {
        snprintf(buffer + (i * 2), 3, "%02X", token_bytes[i]);
    }
    buffer[AUTH_TOKEN_LENGTH * 2] = '\0';

    ESP_LOGI(TAG, "Auth token generated: %.8s...", buffer);

    return ESP_OK;
}

/**
 * @brief Save authentication token
 */
esp_err_t save_auth_token(const char* token)
{
    if (!token || strlen(token) != (AUTH_TOKEN_LENGTH * 2)) {
        return ESP_ERR_INVALID_ARG;
    }

    nvs_handle_t handle;
    esp_err_t ret;

    ret = nvs_open(CONFIG_NAMESPACE, NVS_READWRITE, &handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS open failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = nvs_set_str(handle, KEY_AUTH_TOKEN, token);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS write failed: %s", esp_err_to_name(ret));
        nvs_close(handle);
        return ret;
    }

    ret = nvs_commit(handle);
    nvs_close(handle);

    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "Auth token saved");
    }

    return ret;
}

/**
 * @brief Load authentication token
 */
esp_err_t load_auth_token(char* buffer, size_t buffer_size)
{
    if (!buffer || buffer_size == 0) {
        return ESP_ERR_INVALID_ARG;
    }

    nvs_handle_t handle;
    esp_err_t ret;

    ret = nvs_open(CONFIG_NAMESPACE, NVS_READONLY, &handle);
    if (ret != ESP_OK) {
        return ret;
    }

    size_t required_size = buffer_size;
    ret = nvs_get_str(handle, KEY_AUTH_TOKEN, buffer, &required_size);
    nvs_close(handle);

    if (ret == ESP_ERR_NVS_NOT_FOUND) {
        buffer[0] = '\0';
        return ESP_OK;
    }

    return ret;
}

/**
 * @brief Verify authentication token
 */
bool verify_auth_token(const char* token)
{
    if (!token || strlen(token) != (AUTH_TOKEN_LENGTH * 2)) {
        return false;
    }

    char stored_token[AUTH_TOKEN_LENGTH * 2 + 1];
    esp_err_t ret = load_auth_token(stored_token, sizeof(stored_token));
    if (ret != ESP_OK || stored_token[0] == '\0') {
        return false;
    }

    /* Constant-time comparison to prevent timing attacks */
    int match = 0;
    for (size_t i = 0; i < (AUTH_TOKEN_LENGTH * 2); i++) {
        match |= (token[i] ^ stored_token[i]);
    }

    return match == 0;
}

/**
 * @brief Check if authentication token is set
 */
bool is_auth_token_set(void)
{
    char token[AUTH_TOKEN_LENGTH * 2 + 1];
    esp_err_t ret = load_auth_token(token, sizeof(token));
    return (ret == ESP_OK && token[0] != '\0');
}

/**
 * @brief Reset configuration to factory defaults
 *        (BUG-09 fix: was declared in header but never implemented)
 */
esp_err_t reset_to_defaults(void)
{
    nvs_handle_t handle;
    esp_err_t ret;

    ret = nvs_open(CONFIG_NAMESPACE, NVS_READWRITE, &handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS open failed: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = nvs_erase_all(handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "NVS erase failed: %s", esp_err_to_name(ret));
        nvs_close(handle);
        return ret;
    }

    ret = nvs_commit(handle);
    nvs_close(handle);

    if (ret == ESP_OK) {
        strncpy(current_config.promo_text, DEFAULT_PROMO_TEXT, MAX_PROMO_TEXT_LENGTH);
        current_config.promo_text[MAX_PROMO_TEXT_LENGTH] = '\0';
        current_config.wifi_password[0] = '\0';
        current_config.wifi_encrypted = false;
        strncpy(current_config.device_name, DEFAULT_DEVICE_NAME, MAX_DEVICE_NAME_LENGTH);
        current_config.device_name[MAX_DEVICE_NAME_LENGTH] = '\0';
        current_config.admin_password[0] = '\0';
        device_configured = false;
        ESP_LOGI(TAG, "Configuration reset to factory defaults");
    }

    return ret;
}


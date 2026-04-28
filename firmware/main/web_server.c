/**
 * Web Server Implementation
 * 
 * High-performance HTTP server using ESP-IDF httpd component.
 * Handles captive portal, device setup, and streaming OTA firmware updates.
 */

#include "web_server.h"
#include "ota_update.h"
#include "client_tracker.h"
#include "portal_content.h"
#include "config_manager.h"
#include "esp_log.h"
#include "esp_err.h"
#include "esp_http_server.h"
#include "esp_wifi.h"
#include "esp_system.h"
#include <string.h>
#include <inttypes.h>
#include "esp_mac.h"
#include <stdlib.h>
#include <sys/param.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include "lwip/sockets.h"

static const char* TAG = "WEB_SVR";

/* HTTP server state */
static httpd_handle_t server = NULL;
static bool http_server_active = false;
static form_submit_callback_t form_callback = NULL;

/* Portal content caching - no longer used linearly, we pull from manager */
static char* local_content_cache = NULL;
static size_t local_content_len = 0;

/* Client authentication tracking (IP-based) */
#define MAX_AUTH_CLIENTS 32
static uint32_t auth_clients[MAX_AUTH_CLIENTS] = {0};
static int auth_client_count = 0;

static void authenticate_client(uint32_t ip) {
    for (int i = 0; i < auth_client_count; i++) {
        if (auth_clients[i] == ip) return;
    }
    if (auth_client_count < MAX_AUTH_CLIENTS) {
        auth_clients[auth_client_count++] = ip;
        ESP_LOGI(TAG, "Client authenticated: %u", (unsigned int)ip);
    }
}

static bool is_client_authenticated(uint32_t ip) {
    for (int i = 0; i < auth_client_count; i++) {
        if (auth_clients[i] == ip) return true;
    }
    return false;
}

/**
 * @brief Generate setup portal HTML with device ID
 */
static const char* get_setup_html(const char* device_id)
{
    static char setup_buffer[4096];
    const char* id = device_id ? device_id : "PB-UNKNOWN";

    snprintf(setup_buffer, sizeof(setup_buffer),
        "<!DOCTYPE html><html><head><meta charset=\"UTF-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
        "<title>PromoBeacon Setup</title>"
        "<style>"
        "body{font-family:'Inter',system-ui,sans-serif;margin:0;background:#0f172a;color:#f8fafc;display:flex;justify-content:center;align-items:center;min-height:100vh;}"
        ".container{width:100%%;max-width:400px;background:rgba(30,41,59,0.7);backdrop-filter:blur(10px);padding:2rem;border-radius:1rem;border:1px solid rgba(255,255,255,0.1);box-shadow:0 10px 25px rgba(0,0,0,0.5);}"
        "h1{font-size:1.5rem;margin-bottom:1.5rem;background:linear-gradient(to right,#38bdf8,#818cf8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}"
        "label{display:block;margin-bottom:0.5rem;font-size:0.875rem;font-weight:500;color:#94a3b8;}"
        "input{width:100%%;padding:0.75rem;margin-bottom:1.25rem;background:#0f172a;border:1px solid #334155;border-radius:0.5rem;color:white;box-sizing:border-box;transition:border 0.2s;}"
        "input:focus{outline:none;border-color:#38bdf8;}"
        "button{width:100%%;padding:0.75rem;background:linear-gradient(to right,#0ea5e9,#6366f1);color:white;border:none;border-radius:0.5rem;font-weight:600;cursor:pointer;transition:opacity 0.2s;}"
        "button:hover{opacity:0.9;}"
        ".footer{text-align:center;margin-top:1.5rem;font-size:0.75rem;color:#64748b;font-family:monospace;}"
        "</style></head><body><div class=\"container\">"
        "<h1>Setup PromoBeacon</h1>"
        "<form method=\"POST\" action=\"/setup\">"
        "<label>Promotion Name (WiFi SSID)</label>"
        "<input type=\"text\" name=\"promo_text\" placeholder=\"e.g. 20% OFF\" required maxlength=\"32\">"
        "<label>Admin Password (required)</label>"
        "<input type=\"password\" name=\"admin_pwd\" placeholder=\"For OTA updates\" required minlength=\"4\">"
        "<button type=\"submit\">Complete Setup</button></form>"
        "<div class=\"footer\">DEVID: %s</div></div></body></html>", id);

    return setup_buffer;
}

/**
 * @brief GET / - Root handler
 */
static esp_err_t root_get_handler(httpd_req_t *req)
{
    ESP_LOGI(TAG, "HTTP GET / - Device configured: %d - Free Heap: %d", 
             is_device_configured(), (int)xPortGetFreeHeapSize());

    if (!is_device_configured()) {
        char device_id[32];
        get_device_id(device_id, sizeof(device_id));
        ESP_LOGI(TAG, "Serving setup page for ID: %s", device_id);
        const char* html = get_setup_html(device_id);
        httpd_resp_send(req, html, strlen(html));
        return ESP_OK;
    }

    /* Device is configured, serve promotion index */
    httpd_resp_set_type(req, "text/html");
    
    /* Dynamic content sync: always check for custom content first */
    const char* custom_html = portal_content_get();
    if (custom_html) {
        httpd_resp_send(req, custom_html, portal_content_get_size());
    } else {
        /* Fallback to default generated with current promo text */
        char device_id[32];
        get_device_id(device_id, sizeof(device_id));
        const char* default_html = portal_get_default_html_with_id(get_config()->promo_text, device_id);
        httpd_resp_send(req, default_html, strlen(default_html));
    }
    
    return ESP_OK;
}

/**
 * @brief GET /connect - User interacts with portal to 'gain internet'
 */
static esp_err_t connect_get_handler(httpd_req_t *req)
{
    struct sockaddr_in client_addr;
    int sockfd = httpd_req_to_sockfd(req);
    socklen_t addr_len = sizeof(client_addr);
    getpeername(sockfd, (struct sockaddr*)&client_addr, &addr_len);
    
    authenticate_client(client_addr.sin_addr.s_addr);
    
    /* Redirect to index, but now OS will see 'Internet' */
    httpd_resp_set_status(req, "302 Found");
    httpd_resp_set_hdr(req, "Location", "http://192.168.4.1/");
    httpd_resp_send(req, NULL, 0);
    return ESP_OK;
}

/**
 * @brief Decode URL-encoded strings in-place (handles '+' and '%xx')
 */
static void urldecode_in_place(char *str) {
    char *pstr = str, *buf = str;
    while (*pstr) {
        if (*pstr == '%') {
            if (pstr[1] && pstr[2]) {
                pstr++;
                char c = 0;
                for (int i = 0; i < 2; i++) {
                    c <<= 4;
                    if (*pstr >= '0' && *pstr <= '9') c |= (*pstr - '0');
                    else if (*pstr >= 'A' && *pstr <= 'F') c |= (*pstr - 'A' + 10);
                    else if (*pstr >= 'a' && *pstr <= 'f') c |= (*pstr - 'a' + 10);
                    pstr++;
                }
                *buf++ = c;
            }
        } else if (*pstr == '+') {
            *buf++ = ' ';
            pstr++;
        } else {
            *buf++ = *pstr++;
        }
    }
    *buf = '\0';
}

/**
 * @brief POST /setup - Handle initial configuration
 */
static esp_err_t setup_post_handler(httpd_req_t *req)
{
    char buf[256];
    int ret = httpd_req_recv(req, buf, sizeof(buf) - 1);
    if (ret <= 0) return ESP_FAIL;
    buf[ret] = '\0';

    char promo[64] = {0}, wifi_pwd[64] = {0}, admin_pwd[64] = {0};
    
    /* Decent enough parsing for setup form */
    if (httpd_query_key_value(buf, "promo_text", promo, sizeof(promo)) == ESP_OK) {
        urldecode_in_place(promo);
        save_promo_text(promo);
    }
    if (httpd_query_key_value(buf, "wifi_pwd", wifi_pwd, sizeof(wifi_pwd)) == ESP_OK && strlen(wifi_pwd) >= 8) {
        urldecode_in_place(wifi_pwd);
        save_wifi_password(wifi_pwd);
    } else {
        save_wifi_password(""); /* Defaults to open network */
    }
    if (httpd_query_key_value(buf, "admin_pwd", admin_pwd, sizeof(admin_pwd)) == ESP_OK) {
        urldecode_in_place(admin_pwd);
        save_admin_password(admin_pwd);
    }

    set_device_configured();

    const char* success = "<html><body style='font-family:sans-serif;text-align:center;padding:50px;background:#f0f9ff;'>"
                          "<h1 style='color:#0369a1'>Setup Successful!</h1>"
                          "<p>Device is restarting to apply changes...</p></body></html>";
    httpd_resp_send(req, success, strlen(success));

    /* Restart after a brief delay */
    ESP_LOGI(TAG, "Setup complete, rebooting...");
    vTaskDelay(pdMS_TO_TICKS(1000));
    esp_restart();
    
    return ESP_OK;
}

/**
 * @brief GET /update - OTA Upload Interface (with Password Protection)
 */
static esp_err_t update_get_handler(httpd_req_t *req)
{
    const char* html = 
        "<!DOCTYPE html><html><head><meta charset=\"UTF-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
        "<title>Firmware Update</title>"
        "<style>"
        "body{font-family:'Inter',sans-serif;margin:0;background:#0f172a;color:white;display:flex;justify-content:center;align-items:center;min-height:100vh;}"
        ".card{width:100%%;max-width:400px;background:rgba(30,41,59,0.7);backdrop-filter:blur(10px);padding:2rem;border-radius:1rem;border:1px solid rgba(255,255,255,0.1);}"
        "h1{font-size:1.25rem;margin-bottom:1rem;color:#38bdf8;}"
        ".progress-container{width:100%%;height:8px;background:#1e293b;border-radius:4px;margin:1.5rem 0;overflow:hidden;display:none;}"
        ".progress-bar{height:100%%;width:0%%;background:#38bdf8;transition:width 0.2s;}"
        "input{width:100%%;padding:0.75rem;margin-bottom:1rem;background:#0f172a;border:1px solid #334155;border-radius:0.5rem;color:white;box-sizing:border-box;}"
        "input[type=file]{display:none;}"
        ".upload-btn{display:block;width:100%%;padding:1rem;background:#334155;border:2px dashed #475569;border-radius:0.5rem;text-align:center;cursor:pointer;}"
        ".submit-btn{width:100%%;padding:0.75rem;background:#38bdf8;color:#0f172a;border:none;border-radius:0.5rem;font-weight:700;margin-top:1rem;cursor:pointer;}"
        "</style></head><body><div class=\"card\">"
        "<h1>Firmware Update</h1>"
        "<div id=\"login_zone\">"
        "<input type=\"password\" id=\"admin_pwd\" placeholder=\"Enter Admin Password\">"
        "<button class=\"submit-btn\" onclick=\"unlock()\">Unlock</button></div>"
        "<div id=\"upload_zone\" style=\"display:none\">"
        "<form id=\"upload_form\">"
        "<label class=\"upload-btn\" for=\"file_input\">Select .bin file</label>"
        "<input type=\"file\" id=\"file_input\" name=\"update\">"
        "<button type=\"button\" class=\"submit-btn\" onclick=\"doUpdate()\">Start Update</button></form>"
        "<div class=\"progress-container\" id=\"prg_cont\"><div class=\"progress-bar\" id=\"prg\"></div></div>"
        "<div id=\"status\" style=\"margin-top:1rem;font-size:0.875rem;color:#94a3b8\"></div></div>"
        "<script>"
        "function unlock(){"
        "  const p = document.getElementById('admin_pwd').value;"
        "  if(!p) return;"
        "  sessionStorage.setItem('admin_pwd', p);"
        "  document.getElementById('login_zone').style.display = 'none';"
        "  document.getElementById('upload_zone').style.display = 'block';"
        "}"
        "function doUpdate(){"
        "  const file = document.getElementById('file_input').files[0];"
        "  const pwd = sessionStorage.getItem('admin_pwd');"
        "  if(!file) return alert('Select file');"
        "  document.getElementById('prg_cont').style.display = 'block';"
        "  const xhr = new XMLHttpRequest();"
        "  xhr.upload.addEventListener('progress', e => {"
        "    const p = Math.round((e.loaded/e.total)*100);"
        "    document.getElementById('prg').style.width = p + '%%';"
        "    document.getElementById('status').innerText = 'Uploading: ' + p + '%%';"
        "  });"
        "  xhr.onload = () => {"
        "    if(xhr.status == 200) { document.getElementById('status').innerText = 'Success! Rebooting...'; }"
        "    else { document.getElementById('status').innerText = 'Access Denied or Error'; sessionStorage.clear(); location.reload(); }"
        "  };"
        "  xhr.open('POST', '/update');"
        "  xhr.setRequestHeader('X-Admin-Pwd', pwd);"
        "  xhr.send(file);"
        "}</script></div></body></html>";

    return httpd_resp_send(req, html, -1);
}

/**
 * @brief POST /update - OTA Streaming Upload (with Password Protection)
 */
static esp_err_t update_post_handler(httpd_req_t *req)
{
    char pwd_header[64] = {0};
    if (httpd_req_get_hdr_value_str(req, "X-Admin-Pwd", pwd_header, sizeof(pwd_header)) != ESP_OK) {
        httpd_resp_send_err(req, HTTPD_401_UNAUTHORIZED, "Password required");
        return ESP_FAIL;
    }

    if (!verify_admin_password(pwd_header)) {
        httpd_resp_send_err(req, HTTPD_401_UNAUTHORIZED, "Invalid Password");
        return ESP_FAIL;
    }

    char buf[1024];
    int remaining = req->content_len;
    
    ESP_LOGI(TAG, "Starting binary OTA streaming (Size: %d bytes)", remaining);
    
    if (ota_begin() != ESP_OK) {
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }
    
    ota_set_total_size(remaining);

    while (remaining > 0) {
        int recv_len = httpd_req_recv(req, buf, MIN(remaining, sizeof(buf)));
        if (recv_len <= 0) {
            if (recv_len == HTTPD_SOCK_ERR_TIMEOUT) continue;
            ota_abort();
            httpd_resp_send_500(req);
            return ESP_FAIL;
        }
        
        if (ota_write(buf, recv_len) != ESP_OK) {
            ota_abort();
            httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Flash write failed");
            return ESP_FAIL;
        }
        
        remaining -= recv_len;
    }

    if (ota_end() != ESP_OK) {
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }

    httpd_resp_sendstr(req, "Update SUCCESS");
    
    /* Reboot in background */
    vTaskDelay(pdMS_TO_TICKS(1000));
    esp_restart();
    
    return ESP_OK;
}

/**
 * @brief GET /favicon.ico (Stub)
 */
static esp_err_t favicon_get_handler(httpd_req_t *req)
{
    httpd_resp_set_status(req, "204 No Content");
    httpd_resp_send(req, NULL, 0);
    return ESP_OK;
}

/* URI definitions */
static const httpd_uri_t root = { .uri = "/", .method = HTTP_GET, .handler = root_get_handler };
static const httpd_uri_t setup = { .uri = "/setup", .method = HTTP_POST, .handler = setup_post_handler };
static const httpd_uri_t update_get = { .uri = "/update", .method = HTTP_GET, .handler = update_get_handler };
static const httpd_uri_t update_post = { .uri = "/update", .method = HTTP_POST, .handler = update_post_handler };
static const httpd_uri_t favicon = { .uri = "/favicon.ico", .method = HTTP_GET, .handler = favicon_get_handler };
static const httpd_uri_t connect_uri = { .uri = "/connect", .method = HTTP_GET, .handler = connect_get_handler };

/**
 * @brief Unified handler for connectivity check probes (Android, iOS, Windows)
 */
static esp_err_t connectivity_check_handler(httpd_req_t *req)
{
    struct sockaddr_in client_addr;
    int sockfd = httpd_req_to_sockfd(req);
    socklen_t addr_len = sizeof(client_addr);
    getpeername(sockfd, (struct sockaddr*)&client_addr, &addr_len);
    
    uint32_t ip = client_addr.sin_addr.s_addr;
    
    if (is_client_authenticated(ip)) {
        ESP_LOGI(TAG, "Satisfying connectivity probe for authenticated client: %s", req->uri);
        
        /* Satisfy probe based on URI */
        if (strstr(req->uri, "generate_204")) {
            httpd_resp_set_status(req, "204 No Content");
            httpd_resp_send(req, NULL, 0);
            return ESP_OK;
        }
        
        /* Default Success response for Apple/Others */
        httpd_resp_set_type(req, "text/html");
        httpd_resp_send(req, "Success", 7);
        return ESP_OK;
    }

    ESP_LOGI(TAG, "Redirecting probe for unauthenticated client: %s", req->uri);
    
    /* Set headers to prevent caching of this redirect */
    httpd_resp_set_hdr(req, "Cache-Control", "no-cache, no-store, must-revalidate");
    httpd_resp_set_hdr(req, "Pragma", "no-cache");
    httpd_resp_set_hdr(req, "Expires", "0");
    
    httpd_resp_set_status(req, "302 Found");
    httpd_resp_set_hdr(req, "Location", "http://192.168.4.1/");
    httpd_resp_send(req, NULL, 0);
    return ESP_OK;
}

/**
 * @brief HTTP 404 Error Handler - Redirects to root for Captive Portal detection
 */
static esp_err_t captive_portal_redirect_handler(httpd_req_t *req, httpd_err_code_t error)
{
    /* Use the same logic as the connectivity probe handler for consistency */
    return connectivity_check_handler(req);
}

/* Connectivity check URIs */
static const httpd_uri_t probe_android = { .uri = "/generate_204", .method = HTTP_GET, .handler = connectivity_check_handler };
static const httpd_uri_t probe_apple = { .uri = "/hotspot-detect.html", .method = HTTP_GET, .handler = connectivity_check_handler };
static const httpd_uri_t probe_apple_alt = { .uri = "/library/test/success.html", .method = HTTP_GET, .handler = connectivity_check_handler };
static const httpd_uri_t probe_win = { .uri = "/ncsi.txt", .method = HTTP_GET, .handler = connectivity_check_handler };



esp_err_t init_http_server(void)
{
    if (http_server_active) return ESP_OK;

    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.max_uri_handlers = 12;
    config.stack_size = 15360;
    config.lru_purge_enable = true;

    /* Dynamic serving used now - no static initialization needed here */
    ESP_LOGI(TAG, "Content sync manager active");

    ESP_LOGI(TAG, "Starting HTTP Server on port %d", config.server_port);
    if (httpd_start(&server, &config) == ESP_OK) {
        httpd_register_uri_handler(server, &root);
        httpd_register_uri_handler(server, &setup);
        httpd_register_uri_handler(server, &update_get);
        httpd_register_uri_handler(server, &update_post);
        httpd_register_uri_handler(server, &favicon);
        httpd_register_uri_handler(server, &connect_uri);
        
        /* Register connectivity check probes */
        httpd_register_uri_handler(server, &probe_android);
        httpd_register_uri_handler(server, &probe_apple);
        httpd_register_uri_handler(server, &probe_apple_alt);
        httpd_register_uri_handler(server, &probe_win);
        
        /* Register error handler for Captive Portal detection */
        httpd_register_err_handler(server, HTTPD_404_NOT_FOUND, captive_portal_redirect_handler);
        
        http_server_active = true;
        return ESP_OK;
    }

    return ESP_FAIL;
}

void stop_http_server(void)
{
    if (server) {
        httpd_stop(server);
        server = NULL;
    }
    http_server_active = false;
}

void handle_http_requests(void) {
    /* No-op: httpd component runs in its own task */
}

bool is_http_server_active(void) { return http_server_active; }

esp_err_t set_portal_content(const char* html_content, size_t length) {
    return portal_content_set(html_content, length);
}

uint8_t get_http_connection_count(void) { return 0; } /* Stub for API compatibility */
esp_err_t complete_ota_update(void) { return ota_end(); }
void abort_ota_update(void) { ota_abort(); }
bool is_ota_update_active(void) { return ota_is_in_progress(); }
bool is_in_setup_mode(void) { return !is_device_configured(); }
esp_err_t complete_setup(void) { set_device_configured(); return ESP_OK; }
void register_form_callback(form_submit_callback_t callback) { form_callback = callback; }

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>

#define TAG "BENCH_TESTER"

// UUIDs do PromoBeacon
static BLEUUID SERVICE_UUID("12345678-1234-1234-1234-123456789ABC");
static BLEUUID CHAR_AUTH_UUID("12345683-1234-1234-1234-123456789ABC");
static BLEUUID CHAR_STATUS_UUID("12345685-1234-1234-1234-123456789ABC");

// Estado do Testador de Bancada
String targetSSID = "";
int wifiTestsRun = 0;
int wifiTestsPassed = 0;
int bleTestsRun = 0;
int bleTestsPassed = 0;

void printHeader() {
    Serial.println("\n========================================================");
    Serial.println("   ESP32 LABS BENCH TESTER — PROMOBEACON STRESS SUITE   ");
    Serial.println("========================================================");
    Serial.printf("Tester MAC: %s | Free Heap: %d bytes\n", WiFi.macAddress().c_str(), ESP.getFreeHeap());
    Serial.println("--------------------------------------------------------\n");
}

bool scanAndFindBeaconWiFi() {
    Serial.println("[WIFI] Escaneando redes 2.4 GHz em busca do PromoBeacon...");
    int n = WiFi.scanNetworks(false, true); // Scan assíncrono = false, show_hidden = true
    Serial.printf("[WIFI] %d redes encontradas.\n", n);
    
    targetSSID = "";
    for (int i = 0; i < n; ++i) {
        String ssid = WiFi.SSID(i);
        int rssi = WiFi.RSSI(i);
        uint8_t encType = WiFi.encryptionType(i);
        Serial.printf("  - [%d] SSID: '%s' | RSSI: %d dBm | Enc: %s\n", 
                      i+1, ssid.c_str(), rssi, (encType == WIFI_AUTH_OPEN ? "OPEN" : "ENCRYPTED"));
        
        // Critério: rede aberta com nome PIZZA ou Promo ou sinal forte
        if (encType == WIFI_AUTH_OPEN) {
            if (ssid.indexOf("PIZZA") >= 0 || ssid.indexOf("Promo") >= 0 || ssid.indexOf("BEACON") >= 0) {
                targetSSID = ssid;
                break;
            }
        }
    }

    if (targetSSID.length() > 0) {
        Serial.printf("\n[WIFI] >>> PromoBeacon Localizado: '%s' <<<\n", targetSSID.c_str());
        return true;
    } else {
        Serial.println("[WIFI] ⚠️ Nenhum PromoBeacon detectado no scan aberto. Tentando 'PIZZA BELLA NAPOLI' por padrão...");
        targetSSID = "PIZZA BELLA NAPOLI";
        return true;
    }
}

void testCaptivePortalProbes() {
    Serial.printf("\n[TEST-1] Conectando ao AP '%s'...\n", targetSSID.c_str());
    WiFi.mode(WIFI_STA);
    WiFi.begin(targetSSID.c_str());

    unsigned long t0 = millis();
    while (WiFi.status() != WL_CONNECTED && (millis() - t0 < 8000)) {
        delay(200);
        Serial.print(".");
    }
    Serial.println();

    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("[TEST-1] ❌ Falha ao associar Wi-Fi / DHCP Timeout.");
        return;
    }

    IPAddress ip = WiFi.localIP();
    IPAddress gw = WiFi.gatewayIP();
    Serial.printf("[TEST-1] ✅ Conectado! IP: %s | Gateway: %s | Tempo: %lu ms\n", 
                  ip.toString().c_str(), gw.toString().c_str(), millis() - t0);

    // Teste dos Probes
    const char* probes[] = {
        "/generate_204",            // Android
        "/hotspot-detect.html",      // Apple iOS
        "/ncsi.txt",                 // Windows
        "/portal.json",              // RFC 8908 Captive API
        "/"                          // Página inicial do panfleto
    };

    HTTPClient http;
    http.setFollowRedirects(HTTPC_DISABLE_FOLLOW_REDIRECTS); // Crucial para validar o 302!
    http.setTimeout(3000);

    for (int i = 0; i < 5; i++) {
        String url = "http://" + gw.toString() + probes[i];
        http.begin(url);
        http.addHeader("Connection", "close");
        unsigned long reqStart = millis();
        int httpCode = http.GET();
        unsigned long reqElapsed = millis() - reqStart;

        wifiTestsRun++;
        Serial.printf("  * Probe [%s] -> HTTP Status: %d (%lu ms)", probes[i], httpCode, reqElapsed);

        if (strcmp(probes[i], "/") == 0) {
            // Raiz deve retornar 200 OK com o cardápio
            if (httpCode == 200) {
                Serial.printf(" [PASS] (Tamanho: %d bytes)\n", http.getSize());
                wifiTestsPassed++;
            } else {
                Serial.printf(" [FAIL] Esperado 200, recebido %d\n", httpCode);
            }
        } else if (strcmp(probes[i], "/portal.json") == 0) {
            // RFC 8908 deve retornar 200 com JSON captive
            if (httpCode == 200) {
                String payload = http.getString();
                Serial.printf(" [PASS] RFC 8908: %s\n", payload.substring(0, 40).c_str());
                wifiTestsPassed++;
            } else {
                Serial.println(" [WARN] RFC 8908 não respondeu 200.");
            }
        } else {
            // Probes de conectividade DEVEM responder 302 Found (Modo Sempre-302)
            if (httpCode == 302) {
                String loc = http.header("Location");
                Serial.printf(" [PASS - SEMPRE-302 VALIDADO! Redireciona para: %s]\n", loc.c_str());
                wifiTestsPassed++;
            } else {
                Serial.printf(" [FAIL] Esperado 302 Found, recebido %d\n", httpCode);
            }
        }
        http.end();
    }

    WiFi.disconnect(true);
    Serial.println("[TEST-1] Wi-Fi desconectado para teste de ciclo.\n");
}

class AdvertisedDeviceCallbacks: public BLEAdvertisedDeviceCallbacks {
    void onResult(BLEAdvertisedDevice advertisedDevice) {
        if (advertisedDevice.haveServiceUUID() && advertisedDevice.isAdvertisingService(SERVICE_UUID)) {
            Serial.printf("[BLE] >>> PromoBeacon BLE Detectado! RSSI: %d dBm | Addr: %s <<<\n",
                          advertisedDevice.getRSSI(), advertisedDevice.getAddress().toString().c_str());
        }
    }
};

void testBleScan() {
    Serial.println("[TEST-2] Iniciando Scan de Rádio BLE (ESP32 Labs ble-lab-b1)...");
    BLEDevice::init("BenchTester-ESP32");
    BLEScan* pBLEScan = BLEDevice::getScan();
    pBLEScan->setAdvertisedDeviceCallbacks(new AdvertisedDeviceCallbacks());
    pBLEScan->setActiveScan(true);
    pBLEScan->setInterval(100);
    pBLEScan->setWindow(99);

    BLEScanResults foundDevices = pBLEScan->start(4, false);
    Serial.printf("[TEST-2] Scan BLE concluído. Total de dispositivos na área: %d\n", foundDevices.getCount());
    pBLEScan->clearResults();
}

void setup() {
    Serial.begin(115200);
    delay(1000);
    printHeader();

    scanAndFindBeaconWiFi();
}

void loop() {
    static int cycle = 1;
    Serial.printf("\n==================== CICLO DE ESTRESSE #%d ====================\n", cycle++);
    
    // 1. Teste de Wi-Fi e Captive Probes
    testCaptivePortalProbes();

    // 2. Teste de BLE
    testBleScan();

    // 3. Resumo de Métricas de Bancada
    Serial.printf("\n[PLACAR GERAL] Probes Wi-Fi Testados: %d | Sucessos: %d (%.1f%%)\n",
                  wifiTestsRun, wifiTestsPassed, (wifiTestsPassed * 100.0) / max(1, wifiTestsRun));
    Serial.printf("Free Heap no Testador: %d bytes\n", ESP.getFreeHeap());
    Serial.println("================================================================\n");

    delay(5000); // Aguarda 5s para o próximo ciclo contínuo de estresse
}

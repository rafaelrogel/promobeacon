idf_component_register(SRCS "main.c"
                    "ble_manager.c"
                    "client_tracker.c"
                    "config_manager.c"
                    "g_mode.c"
                    "ota_update.c"
                    "portal_content.c"
                    "status_collector.c"
                    "web_server.c"
                    "wifi_manager.c"
                    INCLUDE_DIRS "." "../include"
                    PRIV_INCLUDE_DIRS "$ENV{IDF_PATH}/components/bt/host/nimble/nimble/nimble/include"
                                      "$ENV{IDF_PATH}/components/bt/host/nimble/nimble/nimble/host/include"
                                      "$ENV{IDF_PATH}/components/bt/host/nimble/nimble/porting/nimble/include"
                                      "$ENV{IDF_PATH}/components/bt/host/nimble/port/include"
                                      "$ENV{IDF_PATH}/components/bt/host/nimble/nimble/nimble/host/services/gap/include"
                                      "$ENV{IDF_PATH}/components/bt/host/nimble/nimble/nimble/host/services/gatt/include"
                                      "$ENV{IDF_PATH}/components/bt/host/nimble/nimble/porting/npl/freertos/include"
                                      "$ENV{IDF_PATH}/components/bt/host/nimble/nimble/nimble/transport/include"
                                      "$ENV{IDF_PATH}/components/bt/host/nimble/nimble/nimble/host/util/include"
                                      "$ENV{IDF_PATH}/components/bt/host/nimble/nimble/nimble"
                    REQUIRES nvs_flash esp_wifi esp_event esp_netif esp_http_server bt esp_adc app_update)

add_compile_options("-Wno-error")
add_compile_options("-Wno-unused-variable")
add_compile_options("-Wno-unused-function")
add_compile_options("-Wno-unused-but-set-variable")
add_compile_options("-Wno-format")

target_compile_options(${COMPONENT_LIB} PRIVATE "-Wno-error" "-Wno-format")

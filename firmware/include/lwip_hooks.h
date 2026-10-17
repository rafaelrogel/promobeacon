#pragma once

#include <string.h>
#include <stdint.h>

/**
 * Hook called by ESP-IDF lwIP dhcpserver right before adding the END option (255)
 * to DHCP OFFER and DHCP ACK packets.
 *
 * Injects:
 * - Option 114 (0x72): RFC 8910 Captive-Portal identification URI
 * - Option 160 (0xA0): RFC 7710 Legacy Captive-Portal identification URI
 */
#define LWIP_HOOK_DHCPS_POST_APPEND_OPTS(netif, dhcps, state, pp_opts) do { \
    if ((state) == 2 /* DHCPOFFER */ || (state) == 5 /* DHCPACK */) { \
        const char *uri = "http://192.168.4.1/portal.json"; \
        uint8_t ulen = (uint8_t)strlen(uri); \
        /* Option 114: RFC 8910 Captive Portal Architecture */ \
        *(*pp_opts)++ = 114; \
        *(*pp_opts)++ = ulen; \
        memcpy(*pp_opts, uri, ulen); \
        *pp_opts += ulen; \
        /* Option 160: RFC 7710 Captive Portal Architecture (Legacy) */ \
        *(*pp_opts)++ = 160; \
        *(*pp_opts)++ = ulen; \
        memcpy(*pp_opts, uri, ulen); \
        *pp_opts += ulen; \
    } \
} while(0);

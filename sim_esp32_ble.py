#!/usr/bin/env python3
"""
PromoBeacon ESP32 BLE Simulator
================================
Simulates the PromoBeacon firmware's BLE GATT server on the host machine
using a USB Bluetooth adapter (hci0) so the Android app can be tested
end-to-end without physical ESP32 hardware.

Service UUID:  12345678-1234-1234-1234-123456789ABC
Auth default:  12345 (matches firmware fallback)
"""

import asyncio
import json
import logging
import struct
import sys
import time

from bless import (
    BlessServer,
    GATTAttributePermissions,
    GATTCharacteristicProperties,
)

# ── UUIDs (must match BleClient.kt / ble_manager.c) ─────────────────────────
SERVICE_UUID = "12345678-1234-1234-1234-123456789ABC"
CHAR_MODE_CONTROL = "12345679-1234-1234-1234-123456789ABC"
CHAR_MESSAGE = "1234567A-1234-1234-1234-123456789ABC"
CHAR_CONFIG = "1234567B-1234-1234-1234-123456789ABC"
CHAR_STATUS = "1234567C-1234-1234-1234-123456789ABC"
CHAR_PROMO_TEXT = "1234567D-1234-1234-1234-123456789ABC"
CHAR_STATS = "1234567E-1234-1234-1234-123456789ABC"
CHAR_SESSIONS = "1234567F-1234-1234-1234-123456789ABC"
CHAR_SESSION_CTRL = "12345680-1234-1234-1234-123456789ABC"
CHAR_PORTAL_DATA = "12345681-1234-1234-1234-123456789ABC"
CHAR_PORTAL_CTRL = "12345682-1234-1234-1234-123456789ABC"
CHAR_AUTH = "12345683-1234-1234-1234-123456789ABC"
CHAR_AUTH_STATUS = "12345685-1234-1234-1234-123456789ABC"
CHAR_ADMIN_PASSWORD = "12345686-1234-1234-1234-123456789ABC"

# ── State (mirrors firmware globals) ────────────────────────────────────────
DEFAULT_AUTH_TOKEN = "12345"  # firmware fallback
g_device_name = "PromoBeacon"
g_message_value = "WELCOME"
g_promo_text_value = "PromoBeacon"
g_current_mode = 0x00          # MODE_G
g_is_authenticated = False
g_auth_status = 0x01           # AUTH_STATUS_REQUIRED
g_start_time = time.monotonic()

log = logging.getLogger("promobeacon-sim")

# ── Handlers ────────────────────────────────────────────────────────────────
CHAR_HANDLERS = {}


def build_status_packet() -> bytes:
    """98-byte DeviceStatus packet matching the app's parseStatus()."""
    pkt = bytearray(98)
    pkt[0] = g_current_mode & 0xFF
    pkt[1] = 1                    # isAdvertising
    pkt[2] = 1                    # isConnected
    uptime = int((time.monotonic() - g_start_time) * 1000) & 0xFFFFFFFF
    struct.pack_into("<I", pkt, 3, uptime)
    pkt[7] = (-42) & 0xFF         # rssi (-42 dBm)
    pkt[8] = 1                    # clientCount
    promo = g_promo_text_value.encode("utf-8")[:32]
    pkt[31:31 + len(promo)] = promo
    pkt[97] = 1 if g_is_authenticated else 0
    return bytes(pkt)


def build_stats_packet() -> bytes:
    """8-byte packed stats: [flags(1) | clients(1) | session_dur(4) | portal_avg(1) | battery(1)]"""
    pkt = bytearray(8)
    pkt[0] = 0x01                # flags: connected
    pkt[1] = 1                   # clients
    struct.pack_into("<I", pkt, 2, 3600)  # session duration 1h
    pkt[6] = 85                  # portal avg 85%
    pkt[7] = 90                  # battery 90%
    return bytes(pkt)


def build_sessions_packet() -> bytes:
    """Session history: JSON-ish text payload."""
    sessions = [
        {"mac": "AA:BB:CC:DD:EE:01", "duration_s": 120, "ts": int(time.time()) - 3600},
        {"mac": "AA:BB:CC:DD:EE:02", "duration_s": 300, "ts": int(time.time()) - 7200},
    ]
    return json.dumps(sessions).encode("utf-8")


def make_read_handler(uuid):
    def handler(characteristic):
        log.info("READ  %s", uuid)
        if uuid == CHAR_MODE_CONTROL:
            return bytearray([g_current_mode])
        if uuid == CHAR_MESSAGE:
            return bytearray(g_message_value.encode("utf-8"))
        if uuid == CHAR_STATUS:
            return bytearray(build_status_packet())
        if uuid == CHAR_PROMO_TEXT:
            return bytearray(g_promo_text_value.encode("utf-8"))
        if uuid == CHAR_STATS:
            return bytearray(build_stats_packet())
        if uuid == CHAR_SESSIONS:
            return bytearray(build_sessions_packet())
        if uuid == CHAR_AUTH_STATUS:
            return bytearray([g_auth_status])
        if uuid == CHAR_PORTAL_CTRL:
            return bytearray(b"OK")
        return bytearray(b"")
    return handler


_READ_HANDLERS = {}
_WRITE_HANDLERS = {}


def make_server_read(characteristic):
    """Server-level read dispatch: route by characteristic UUID (lowercase)."""
    uuid = str(characteristic.uuid).lower()
    h = _READ_HANDLERS.get(uuid)
    if h is None:
        log.warning("READ (unhandled) %s", uuid)
        return bytearray(b"")
    return h(characteristic)


def make_server_write(characteristic, value):
    """Server-level write dispatch: route by characteristic UUID (lowercase)."""
    uuid = str(characteristic.uuid).lower()
    h = _WRITE_HANDLERS.get(uuid)
    if h is None:
        log.info("WRITE (unhandled) %s = %r", uuid, bytes(value))
        return
    h(characteristic, value)


def handle_write(characteristic, value):
    global g_current_mode, g_message_value, g_promo_text_value, g_is_authenticated, g_auth_status
    uuid = str(characteristic.uuid).lower()
    log.info("WRITE %s = %r", uuid, bytes(value))
    try:
        text = bytes(value).decode("utf-8", errors="replace")
    except Exception:
        text = repr(value)

    if uuid == CHAR_MODE_CONTROL.lower():
        if not g_is_authenticated:
            raise Exception("INSUFFICIENT_AUTHEN")
        g_current_mode = value[0] & 0xFF
        log.info("mode -> %d", g_current_mode)

    elif uuid == CHAR_MESSAGE.lower():
        if not g_is_authenticated:
            raise Exception("INSUFFICIENT_AUTHEN")
        g_message_value = text[:64]
        log.info("message -> %s", g_message_value)

    elif uuid == CHAR_PROMO_TEXT.lower():
        if not g_is_authenticated:
            raise Exception("INSUFFICIENT_AUTHEN")
        g_promo_text_value = text[:128]
        log.info("promo_text -> %s", g_promo_text_value)

    elif uuid == CHAR_AUTH.lower():
        if text == DEFAULT_AUTH_TOKEN:
            g_is_authenticated = True
            g_auth_status = 0x02  # SUCCESS
            log.info("*** AUTH SUCCESS ***")
        else:
            g_is_authenticated = False
            g_auth_status = 0x03  # FAILED
            log.warning("*** AUTH FAILED (%s) ***", text)

    elif uuid == CHAR_ADMIN_PASSWORD.lower():
        if not g_is_authenticated:
            raise Exception("INSUFFICIENT_AUTHEN")
        log.info("admin password changed -> %s", text)

    elif uuid == CHAR_SESSION_CTRL.lower():
        log.info("session control -> %s", text)

    elif uuid == CHAR_PORTAL_DATA.lower():
        log.info("portal chunk (%d bytes)", len(value))

    elif uuid == CHAR_PORTAL_CTRL.lower():
        log.info("portal control -> %s", text)

    elif uuid == CHAR_CONFIG.lower():
        log.info("config -> %s", text)


async def main():
    log.info("Starting PromoBeacon BLE simulator...")

    server = BlessServer("PromoBeacon")
    await server.add_new_service(SERVICE_UUID)

    # properties/permissions: IntFlag enums, combine with |
    def props(*flags):
        p = GATTCharacteristicProperties(0)
        for f in flags:
            p |= getattr(GATTCharacteristicProperties, f)
        return p

    def perms(*flags):
        p = GATTAttributePermissions(0)
        for f in flags:
            p |= getattr(GATTAttributePermissions, f)
        return p

    perms_rw = perms("readable", "writeable")
    perms_r = perms("readable")
    perms_w = perms("writeable")

    # (uuid, properties, permissions, initial_value)
    chars = [
        (CHAR_MODE_CONTROL, props("read", "write"), perms_rw, bytearray([0])),
        (CHAR_MESSAGE, props("read", "write"), perms_rw, bytearray(b"WELCOME")),
        (CHAR_CONFIG, props("write"), perms_w, None),
        (CHAR_STATUS, props("read", "notify"), perms_r, None),
        (CHAR_PROMO_TEXT, props("read", "write"), perms_rw, bytearray(b"PromoBeacon")),
        (CHAR_STATS, props("read", "notify"), perms_r, None),
        (CHAR_SESSIONS, props("read"), perms_r, None),
        (CHAR_SESSION_CTRL, props("write"), perms_w, None),
        (CHAR_PORTAL_DATA, props("write", "write_without_response"), perms_w, None),
        (CHAR_PORTAL_CTRL, props("read", "write", "notify"), perms_rw, bytearray(b"OK")),
        (CHAR_AUTH, props("write"), perms_w, None),
        (CHAR_AUTH_STATUS, props("read", "notify"), perms_r, bytearray([1])),
        (CHAR_ADMIN_PASSWORD, props("write"), perms_w, None),
    ]

    for uuid, prop, perm, val in chars:
        await server.add_new_characteristic(SERVICE_UUID, uuid, prop, val, perm)
        key = uuid.lower()
        if prop.read:
            _READ_HANDLERS[key] = make_read_handler(uuid)
        if prop.write or prop.write_without_response:
            _WRITE_HANDLERS[key] = handle_write

    server.read_request_func = make_server_read
    server.write_request_func = make_server_write

    try:
        await server.start()
    except Exception as e:
        # Known limitation: bluetoothd's D-Bus advertisement path uses
        # extended advertising MGMT commands (0x0054/0x0055), which the
        # Qualcomm controller on this host rejects with "Invalid Parameters".
        # The GATT application is already registered by this point, so we
        # advertise via the legacy path (btmgmt add-adv) instead.
        log.warning("bless start advertising failed (%s) — GATT app still registered; "
                    "use btmgmt add-adv for legacy advertising", e)

    log.info("Advertising as %s", g_device_name)
    log.info("Service UUID: %s", SERVICE_UUID)
    log.info("Auth token: %s (default)", DEFAULT_AUTH_TOKEN)
    log.info("Press Ctrl+C to stop.")

    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await server.stop()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)

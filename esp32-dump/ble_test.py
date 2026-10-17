#!/usr/bin/env python3
"""PromoBeacon BLE direct test script (stress + functional)"""
import asyncio
import sys
import time
from bleak import BleakClient, BleakScanner

SERVICE_UUID = "12345678-1234-1234-1234-123456789ABC"
CHAR_MODE = "12345679-1234-1234-1234-123456789ABC"
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

ADDR = "AC:A7:04:D4:23:8A"
results = []

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)
    results.append(msg)

async def find_device():
    log(f"Scanning for {ADDR}...")
    device = await BleakScanner.find_device_by_address(ADDR, timeout=15)
    if device:
        log(f"Found: {device.name} @ {device.address} RSSI={device.rssi}")
    else:
        log("ERROR: device not found")
    return device

async def test_connect(device):
    """Full connect + auth + status read test"""
    log("=" * 50)
    log("TEST: Connect + Auth + Status")
    log("=" * 50)
    try:
        async with BleakClient(device, timeout=20) as client:
            log(f"Connected: {client.is_connected}")
            
            # MTU
            try:
                mtu = await client.read_gatt_descriptor(0x0003)  # not reliable, try services instead
            except Exception:
                pass
            
            # Discover services
            services = await client.get_services()
            svc = services.get_service(SERVICE_UUID)
            if svc:
                log(f"Service found: {svc.uuid} with {len(svc.characteristics)} characteristics")
                for ch in svc.characteristics:
                    log(f"  CHAR: {ch.uuid} props={ch.properties}")
            else:
                log("ERROR: PromoBeacon service not found!")
                return False
            
            # Read status
            try:
                status = await client.read_gatt_char(CHAR_STATUS)
                log(f"STATUS raw: {status.hex()} (len={len(status)})")
                if len(status) >= 5:
                    uptime_s = int.from_bytes(status[0:4], 'little')
                    log(f"  Uptime: {uptime_s}s ({uptime_s//60}m{uptime_s%60}s)")
                    log(f"  Mode byte: {status[4]:#x}")
            except Exception as e:
                log(f"STATUS read failed: {e}")
            
            # Auth status
            try:
                auth = await client.read_gatt_char(CHAR_AUTH_STATUS)
                log(f"AUTH_STATUS: {auth.hex()} -> {auth[0]} ({['IDLE','REQUIRED','SUCCESS','FAILED','LOCKED'][auth[0]] if auth[0] < 5 else '?'})")
            except Exception as e:
                log(f"AUTH_STATUS read failed: {e}")
            
            # Try auth with 12345
            log("Auth with '12345'...")
            try:
                await client.write_gatt_char(CHAR_AUTH, b"12345")
                await asyncio.sleep(0.8)
                auth = await client.read_gatt_char(CHAR_AUTH_STATUS)
                log(f"  After auth: {auth[0]} ({['IDLE','REQUIRED','SUCCESS','FAILED','LOCKED'][auth[0]] if auth[0] < 5 else '?'})")
            except Exception as e:
                log(f"AUTH write failed: {e}")
            
            # Read promo text
            try:
                promo = await client.read_gatt_char(CHAR_PROMO_TEXT)
                log(f"PROMO_TEXT: '{promo.decode(errors='replace')}'")
            except Exception as e:
                log(f"PROMO_TEXT read failed: {e}")
            
            # Read device name (GAP)
            try:
                gap = services.get_service("00001800-0000-1000-8000-00805f9b34fb")
                if gap:
                    name_chars = [c for c in gap.characteristics if c.uuid == "00002a00-0000-1000-8000-00805f9b34fb"]
                    if name_chars:
                        name = await client.read_gatt_char(name_chars[0])
                        log(f"DEVICE_NAME: '{name.decode(errors='replace')}'")
            except Exception as e:
                log(f"DEVICE_NAME read failed: {e}")
            
            return True
    except Exception as e:
        log(f"CONNECT ERROR: {e}")
        return False

async def test_mode_switch(device):
    """Test G/E mode switching via BLE"""
    log("=" * 50)
    log("TEST: Mode switch G -> E -> G")
    log("=" * 50)
    try:
        async with BleakClient(device, timeout=20) as client:
            # Switch to E mode (0x01)
            log("Switching to E Mode (0x01)...")
            await client.write_gatt_char(CHAR_MODE, bytes([0x01]))
            await asyncio.sleep(3)
            
            # Read status to check mode
            try:
                status = await client.read_gatt_char(CHAR_STATUS)
                log(f"  After E: mode byte={status[4]:#x} ({'E' if status[4]==1 else 'G' if status[4]==0 else '?'})")
            except Exception as e:
                log(f"  Status read failed: {e}")
            
            # Switch back to G mode (0x00)
            log("Switching to G Mode (0x00)...")
            await client.write_gatt_char(CHAR_MODE, bytes([0x00]))
            await asyncio.sleep(3)
            
            try:
                status = await client.read_gatt_char(CHAR_STATUS)
                log(f"  After G: mode byte={status[4]:#x} ({'E' if status[4]==1 else 'G' if status[4]==0 else '?'})")
            except Exception as e:
                log(f"  Status read failed: {e}")
            return True
    except Exception as e:
        log(f"MODE SWITCH ERROR: {e}")
        return False

async def test_write_promo(device, iterations=20):
    """Write promo text repeatedly (stress)"""
    log("=" * 50)
    log(f"TEST: Promo text write x{iterations} (stress)")
    log("=" * 50)
    try:
        async with BleakClient(device, timeout=20) as client:
            ok = 0
            for i in range(iterations):
                text = f"PROMO-STRESS-{i:03d}"
                try:
                    await client.write_gatt_char(CHAR_PROMO_TEXT, text.encode())
                    ok += 1
                except Exception as e:
                    log(f"  Write {i} FAILED: {e}")
                await asyncio.sleep(0.15)
            log(f"Writes OK: {ok}/{iterations}")
            
            # Read back last value
            try:
                promo = await client.read_gatt_char(CHAR_PROMO_TEXT)
                log(f"Final PROMO_TEXT: '{promo.decode(errors='replace')}'")
            except Exception as e:
                log(f"Read back failed: {e}")
            return ok == iterations
    except Exception as e:
        log(f"WRITE STRESS ERROR: {e}")
        return False

async def test_conn_stress(device, iterations=10):
    """Rapid connect/disconnect stress"""
    log("=" * 50)
    log(f"TEST: Connect/disconnect x{iterations} (stress)")
    log("=" * 50)
    ok = 0
    for i in range(iterations):
        try:
            async with BleakClient(device, timeout=15) as client:
                if client.is_connected:
                    ok += 1
            await asyncio.sleep(0.3)
        except Exception as e:
            log(f"  Conn {i} FAILED: {e}")
        if i % 2 == 1:
            log(f"  Progress: {i+1}/{iterations} ok={ok}")
    log(f"Connections OK: {ok}/{iterations}")
    return ok == iterations

async def test_stats(device):
    """Read stats and sessions"""
    log("=" * 50)
    log("TEST: Stats + Sessions read")
    log("=" * 50)
    try:
        async with BleakClient(device, timeout=20) as client:
            try:
                stats = await client.read_gatt_char(CHAR_STATS)
                log(f"STATS: {stats.hex()} (len={len(stats)})")
            except Exception as e:
                log(f"STATS read failed: {e}")
            try:
                sessions = await client.read_gatt_char(CHAR_SESSIONS)
                log(f"SESSIONS: {sessions.hex()} (len={len(sessions)})")
            except Exception as e:
                log(f"SESSIONS read failed: {e}")
            return True
    except Exception as e:
        log(f"STATS ERROR: {e}")
        return False

async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    device = await find_device()
    if not device:
        return 1
    
    if mode in ("all", "connect"):
        await test_connect(device)
    if mode in ("all", "mode"):
        await test_mode_switch(device)
    if mode in ("all", "promo"):
        await test_write_promo(device)
    if mode in ("all", "conn"):
        await test_conn_stress(device)
    if mode in ("all", "stats"):
        await test_stats(device)
    
    log("=" * 50)
    log("DONE")
    log("=" * 50)
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

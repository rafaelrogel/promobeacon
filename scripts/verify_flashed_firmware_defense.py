#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_flashed_firmware_defense.py — Live Physical Verification of Hardened Firmware
===================================================================================
Target: Physical ESP32-C3 PromoBeacon (192.168.4.1) running compiled binary (Oct 16 23:57)
Attacker: Samsung Galaxy Tablet (R9PW30T4JQM) over 802.11 RF Wi-Fi
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
SERIAL_DEVICE = "R9PW30T4JQM"
BEACON_IP = "192.168.4.1"
TMP_REQ = ROOT_DIR / "scripts" / "tmp_req_verify.bin"

load_dotenv(Path("C:/Users/rafae/.gemini/config/skills/typesafe/.env"))
from typesafe_sdk import TypeSafeClient, Choice, Score
jev_client = TypeSafeClient()

def run_adb(cmd, timeout=15):
    full_cmd = ["adb", "-s", SERIAL_DEVICE, "shell", cmd]
    try:
        res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
        return res.returncode, res.stdout, res.stderr
    except Exception as e:
        return -1, "", str(e)

def send_http(raw_bytes, timeout_s=3):
    with open(TMP_REQ, "wb") as f:
        f.write(raw_bytes)
    subprocess.run(["adb", "-s", SERIAL_DEVICE, "push", str(TMP_REQ), "/data/local/tmp/req_v.bin"], capture_output=True)
    res = subprocess.run(["adb", "-s", SERIAL_DEVICE, "shell", f"cat /data/local/tmp/req_v.bin | nc -w {timeout_s} {BEACON_IP} 80"], capture_output=True, text=True)
    return res.stdout

print("=" * 80)
print("LIVE VERIFICATION ON PHYSICAL ESP32-C3 HARDWARE POST-FLASH")
print("=" * 80)

# Connect to PROMOBEACON
print("\n[STEP 1] Connecting Tablet to 'PROMOBEACON'...")
run_adb("input keyevent 4")
run_adb("am start -a android.settings.WIFI_SETTINGS")
time.sleep(1.5)

connected = False
for attempt in range(5):
    # Tap PROMOBEACON item
    run_adb("input tap 533 468")
    time.sleep(2)
    # Dismiss / confirm captive portal dialog if present
    run_adb("input tap 568 1115")
    time.sleep(1.5)
    
    _, ip_out, _ = run_adb("ip addr show wlan0")
    ips = [l.strip() for l in ip_out.splitlines() if 'inet ' in l]
    print(f"  Attempt {attempt+1} - Tablet wlan0 IP: {ips}")
    if any("192.168.4." in ip for ip in ips):
        connected = True
        print("  Successfully connected to PROMOBEACON subnet!")
        break

if not connected:
    print("  WARNING: Tablet did not acquire 192.168.4.x IP. Checking routes...")


# ==============================================================================
# TEST 1: Unauthenticated Setup Hijack (Should be BLOCKED by new fix!)
# ==============================================================================
print("\n" + "=" * 80)
print("[TEST 1] Testing Unauthenticated /setup Hijack (Attempting to rename to HACKED_BEACON)")
print("=" * 80)
payload_unauth = (
    b"POST /setup HTTP/1.0\r\n"
    b"Host: 192.168.4.1\r\n"
    b"Content-Type: application/x-www-form-urlencoded\r\n"
    b"Content-Length: 42\r\n\r\n"
    b"promo_text=HACKED_BEACON&admin_pwd=hack123"
)
resp1 = send_http(payload_unauth)
first1 = resp1.splitlines()[:3] if resp1.splitlines() else ["EMPTY/CLOSED"]
print("  Response:", first1)

# ==============================================================================
# TEST 2: XSS Injection into SSID (Should be REJECTED with 400 Bad Request!)
# ==============================================================================
print("\n" + "=" * 80)
print("[TEST 2] Testing XSS Injection into SSID (<script>alert('XSS')</script>)")
print("=" * 80)
body_xss = "promo_text=%3Cscript%3Ealert%28%27XSS%27%29%3C%2Fscript%3E&admin_pwd=12345"
payload_xss = (
    "POST /setup HTTP/1.0\r\n"
    "Host: 192.168.4.1\r\n"
    "X-Admin-Pwd: 12345\r\n"
    "Content-Type: application/x-www-form-urlencoded\r\n"
    f"Content-Length: {len(body_xss)}\r\n\r\n" +
    body_xss
).encode("latin1")
resp2 = send_http(payload_xss)
first2 = resp2.splitlines()[:5] if resp2.splitlines() else ["EMPTY/CLOSED"]
print("  Response:", first2)

# ==============================================================================
# TEST 3: Admin Brute-Force Lockout on /upload (Should trigger 429 Too Many Requests!)
# ==============================================================================
print("\n" + "=" * 80)
print("[TEST 3] Testing HTTP Admin Brute-Force Lockout (/upload)")
print("=" * 80)
lockout_results = []
for i in range(1, 6):
    payload_bf = (
        "POST /upload?name=test.bin HTTP/1.0\r\n"
        "Host: 192.168.4.1\r\n"
        f"X-Admin-Pwd: badpass_{i}\r\n"
        "Content-Length: 4\r\n\r\n"
        "test"
    ).encode("latin1")
    r = send_http(payload_bf)
    line = r.splitlines()[0] if r.splitlines() else "NO_RESP"
    print(f"  Attempt {i}: -> {line}")
    lockout_results.append(line)

# ==============================================================================
# TEST 4: Verification of Broadcasted SSID in Silicon
# ==============================================================================
print("\n" + "=" * 80)
print("[TEST 4] Scanning Wi-Fi Beacons over the air...")
print("=" * 80)
time.sleep(2)
_, scan_out, _ = run_adb("cmd wifi list-scan-results")
promo_lines = [l.strip() for l in scan_out.splitlines() if "ac:a7:04:d4:23:89" in l or "PROMO" in l or "HACKED" in l or "script" in l]
for pl in promo_lines:
    print("  Detected Air Beacon:", pl)

# JEV Final Evaluation
print("\n" + "=" * 80)
print("[JEV] Submitting Hardware Verification to TypeSafe AI...")
print("=" * 80)
jev_resp = jev_client.system_one(
    state={
        "test1_unauth_setup": first1,
        "test2_xss_rejection": first2,
        "test3_lockout": lockout_results,
        "test4_air_beacons": promo_lines
    },
    questions={
        "patch_effective": Choice(
            instructions="Did the physical flash successfully patch the security vulnerabilities?",
            criteria={
                "FULLY_PATCHED": "Unauthorized setup blocked, XSS rejected, brute force locked out, SSID intact",
                "PARTIALLY_PATCHED": "Some checks passed, but minor gaps remain",
                "UNPATCHED": "Device still accepts unauthorized reconfig or XSS SSID"
            }
        ),
        "hardware_grade": Score(
            instructions="Grade physical ESP32-C3 defense from 1 to 5",
            criteria=["1: Vulnerable", "2: Minimal", "3: Acceptable", "4: Strong", "5: Impregnable Hardened Silicon"]
        )
    }
)

final_verdict = jev_resp.choices["patch_effective"].choice
final_score = jev_resp.scores["hardware_grade"].score
print(f"  -> JEV Hardware Patch Verdict: {final_verdict}")
print(f"  -> JEV Security Grade: {final_score} / 5.0")
print("=" * 80)

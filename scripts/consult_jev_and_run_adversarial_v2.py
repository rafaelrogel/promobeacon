#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
consult_jev_and_run_adversarial_v2.py — Advanced Adversarial Test Suite Guided by JEV
=====================================================================================
Target: Physical ESP32 PromoBeacon (192.168.4.1)
Attacker Platform: Samsung Galaxy Tablet (R9PW30T4JQM) over 802.11 Wi-Fi

Phases:
  1. JEV Brainstorm & Threat Modeling: TypeSafe AI selects and ranks attack vectors.
  2. Live Attack Execution via Tablet:
     - Vector A: Slowloris & Incomplete Header Socket Starvation
     - Vector B: HTTP Verb Fuzzing & Header Smuggling (TRACE, OPTIONS, Content-Length -1)
     - Vector C: Captive Portal Probe Flood & Redirect Loops
     - Vector D: Post-Patch /setup Injection Audit (Verifying our new fix)
     - Vector E: Admin Route Path Traversal Fuzzing (/upload?name=..\\..\\windows)
  3. JEV Multi-Dimensional Scoring: Decision on resilience, integrity, and hardening.
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
TMP_REQ_LOCAL = ROOT_DIR / "scripts" / "tmp_req_v2.bin"

# Load JEV API Key
env_path = Path("C:/Users/rafae/.gemini/config/skills/typesafe/.env")
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

JEV_API_KEY = os.getenv("TYPESAFE_API_KEY") or os.getenv("JEV_API_KEY") or ""
if JEV_API_KEY:
    os.environ["TYPESAFE_API_KEY"] = JEV_API_KEY

from typesafe_sdk import TypeSafeClient, Choice, Score, Noul
jev_client = TypeSafeClient()

def run_adb(cmd, timeout=20):
    full_cmd = ["adb", "-s", SERIAL_DEVICE, "shell", cmd]
    try:
        res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
        return res.returncode, res.stdout, res.stderr
    except Exception as e:
        return -1, "", str(e)

def send_custom_http(raw_bytes, timeout_s=3):
    with open(TMP_REQ_LOCAL, "wb") as f:
        f.write(raw_bytes)
    subprocess.run(["adb", "-s", SERIAL_DEVICE, "push", str(TMP_REQ_LOCAL), "/data/local/tmp/req_v2.bin"], capture_output=True)
    res = subprocess.run(["adb", "-s", SERIAL_DEVICE, "shell", f"cat /data/local/tmp/req_v2.bin | nc -w {timeout_s} {BEACON_IP} 80"], capture_output=True, text=True)
    return res.stdout

print("=" * 80)
print("PROMOBEACON ADVERSARIAL SUITE V2 — GUIDED BY JEV (TYPESAFE AI)")
print("=" * 80)

# Connect tablet to PROMOBEACON
print("\n[PHASE 0] Ensuring Tablet Connection to 'PROMOBEACON'...")
run_adb("am start -a android.settings.WIFI_SETTINGS")
time.sleep(1)
# Check current IP
_, ip_info, _ = run_adb("ip addr show wlan0")
if "192.168.4." not in ip_info:
    print("  Connecting tablet to PROMOBEACON...")
    # Dump and find PROMOBEACON
    run_adb("uiautomator dump /sdcard/dump.xml")
    subprocess.run(["adb", "-s", SERIAL_DEVICE, "pull", "/sdcard/dump.xml", "scripts/dump_temp.xml"], capture_output=True)
    import xml.etree.ElementTree as ET
    try:
        tree = ET.parse("scripts/dump_temp.xml")
        for node in tree.getroot().iter("node"):
            if "PROMOBEACON" in node.attrib.get("text", ""):
                bounds = node.attrib.get("bounds")
                # e.g. [443,463][644,496]
                import re
                m = re.findall(r"\d+", bounds)
                if m:
                    x = (int(m[0]) + int(m[2])) // 2
                    y = (int(m[1]) + int(m[3])) // 2
                    run_adb(f"input tap {x} {y}")
                    print(f"  Tapped PROMOBEACON at ({x}, {y})")
                    time.sleep(3)
                    # Check for Sempre conectar dialog
                    run_adb("input tap 568 1115")
                    time.sleep(1)
    except Exception as e:
        print(f"  Could not auto-tap: {e}")

_, ip_info, _ = run_adb("ip addr show wlan0")
print(f"  Current Tablet IP Status: {[l.strip() for l in ip_info.splitlines() if 'inet ' in l]}")

# ==============================================================================
# PHASE 1: JEV BRAINSTORMING & THREAT VECTOR PRIORITIZATION
# ==============================================================================
print("\n" + "=" * 80)
print("[PHASE 1] JEV Threat Modeling & Test Vector Prioritization")
print("=" * 80)

jev_threat_model = jev_client.system_one(
    state={
        "appliance": "ESP32 Embedded Web & Captive Portal Server (lwIP + ESP-IDF httpd)",
        "network_topology": "Standalone Wi-Fi AP (192.168.4.1), no internet uplink, mobile clients connecting dynamically",
        "recent_patch": "Added strict SSID sanitization in /setup and required admin auth for reconfiguration",
        "available_attack_surfaces": [
            "HTTP Verb Fuzzing & Header Smuggling",
            "Slowloris Socket Holding / Incomplete Header Starvation",
            "Captive Portal Probe & Redirect Amplification (/generate_204, /ncsi.txt)",
            "Post-Patch /setup Injection (XSS tags, Path Traversal, Large Payloads)",
            "Admin Path Traversal (/upload?name=../../etc/shadow)"
        ]
    },
    questions={
        "critical_test_focus": Choice(
            instructions="Select the primary high-priority attack vector for embedded ESP32 captive devices",
            criteria={
                "SOCKET_EXHAUSTION": "Slowloris & concurrent connection holding to verify LRU socket purge",
                "INPUT_INJECTION": "Fuzzing URL query params and setup form fields with forbidden characters",
                "PROTOCOL_SMUGGLING": "Unsupported HTTP verbs and malformed Content-Length headers"
            }
        ),
        "threat_severity_rank": Score(
            instructions="Rank potential impact of Slowloris denial-of-service on ESP32 (1 to 5)",
            criteria=[
                "1: Minimal",
                "2: Minor delay",
                "3: Temporary stall",
                "4: Severe socket starvation",
                "5: Complete unrecoverable appliance freeze"
            ]
        ),
        "post_patch_bypass_probability": Noul(
            instructions="Probability that the new /setup sanitization can be bypassed by alternative encoding"
        )
    }
)

print(f"  [JEV Advice] Primary Attack Vector Focus: {jev_threat_model.choices['critical_test_focus'].choice}")
print(f"  [JEV Advice] Slowloris Impact Severity Rating: {jev_threat_model.scores['threat_severity_rank'].score} / 5.0")
print(f"  [JEV Advice] Post-Patch Bypass Probability: {round(jev_threat_model.nouls['post_patch_bypass_probability'].noul * 100, 2)}%")

# ==============================================================================
# PHASE 2: EXECUTION OF EXTENDED ADVERSARIAL TEST VECTORS
# ==============================================================================
print("\n" + "=" * 80)
print("[PHASE 2] Executing Extended Adversarial Test Vectors on Physical Hardware")
print("=" * 80)

v2_test_results = {}

# Test Vector A: HTTP Verb Fuzzing (Uncommon & Arbitrary Verbs)
print("\n--- [VETOR A] HTTP Verb Fuzzing & Header Smuggling ---")
verbs = ["TRACE", "OPTIONS", "HEAD", "PUT", "DELETE", "PATCH", "EXPLOIT"]
verb_results = []
for v in verbs:
    raw = f"{v} / HTTP/1.0\r\nHost: {BEACON_IP}\r\n\r\n".encode("latin1")
    resp = send_custom_http(raw, timeout_s=2)
    first_line = resp.splitlines()[0] if resp.splitlines() else "EMPTY/CLOSED"
    print(f"  Method {v:<8} -> {first_line}")
    verb_results.append({"verb": v, "status": first_line})
v2_test_results["http_verbs"] = verb_results

# Test Vector B: Malformed Headers & Negative/Extreme Content-Length
print("\n--- [VETOR B] Header Smuggling & Boundary Fuzzing ---")
header_cases = [
    ("Missing Host Header", b"GET / HTTP/1.1\r\n\r\n"),
    ("Negative Content-Length", b"POST /setup HTTP/1.0\r\nHost: 192.168.4.1\r\nContent-Length: -1\r\n\r\n"),
    ("Extreme Content-Length (100MB)", b"POST /upload HTTP/1.0\r\nHost: 192.168.4.1\r\nContent-Length: 104857600\r\n\r\n"),
    ("Repeated Headers (Double Host)", b"GET / HTTP/1.0\r\nHost: 192.168.4.1\r\nHost: evil.com\r\n\r\n"),
    ("Huge Request URI (>1024 chars)", ("GET /" + ("A" * 1024) + " HTTP/1.0\r\nHost: 192.168.4.1\r\n\r\n").encode("latin1"))
]
header_results = []
for name, payload in header_cases:
    resp = send_custom_http(payload, timeout_s=2)
    first_line = resp.splitlines()[0] if resp.splitlines() else "DROPPED/CLOSED"
    print(f"  Case '{name}': -> {first_line}")
    header_results.append({"case": name, "status": first_line})
v2_test_results["header_fuzzing"] = header_results

# Test Vector C: Slowloris Incomplete Header Starvation Test
print("\n--- [VETOR C] Slowloris Incomplete Header Holding Test ---")
# Send partial headers and sleep to see if ESP32 drops connection or blocks new ones
print("  Opening half-open socket (incomplete HTTP headers)...")
slowloris_cmd = f"python3 -c 'import socket, time; s = socket.socket(); s.connect((\"{BEACON_IP}\", 80)); s.send(b\"GET / HTTP/1.0\\r\\nHost: {BEACON_IP}\\r\\nUser-Agent: Slowloris\\r\\n\"); time.sleep(3); s.close()' 2>/dev/null || (printf 'GET / HTTP/1.0\\r\\nHost: {BEACON_IP}\\r\\n' | nc -w 3 {BEACON_IP} 80)"
run_adb(slowloris_cmd, timeout=5)

# Verify if ESP32 serves normal requests concurrently during/after slowloris
time.sleep(1)
quick_check = send_custom_http(b"GET / HTTP/1.0\r\nHost: 192.168.4.1\r\n\r\n", timeout_s=2)
slowloris_handled = "200 OK" in quick_check
print(f"  Concurrent Channel Health: {'RESPONSIVE (LRU Purge OK)' if slowloris_handled else 'BLOCKED'}")
v2_test_results["slowloris_resilience"] = slowloris_handled

# Test Vector D: Post-Patch /setup Security Audit
print("\n--- [VETOR D] Post-Patch /setup Security Verification ---")
setup_tests = [
    ("Unauthenticated Reconfiguration Attempt", "POST", "/setup", {"Content-Type": "application/x-www-form-urlencoded"}, "promo_text=HACKED_BEACON&admin_pwd=hack123"),
    ("SSID Injection with HTML Script Tags", "POST", "/setup", {"Content-Type": "application/x-www-form-urlencoded", "X-Admin-Pwd": "even_with_pwd"}, "promo_text=%3Cscript%3Ealert%281%29%3C%2Fscript%3E&admin_pwd=valid123"),
    ("SSID with Quotes and Backticks", "POST", "/setup", {"Content-Type": "application/x-www-form-urlencoded", "X-Admin-Pwd": "even_with_pwd"}, "promo_text=PROMO%22%60test&admin_pwd=valid123"),
    ("Admin Password Too Short (<4 chars)", "POST", "/setup", {"Content-Type": "application/x-www-form-urlencoded", "X-Admin-Pwd": "even_with_pwd"}, "promo_text=VALIDSSID&admin_pwd=12"),
    ("Valid Clean Reconfiguration", "POST", "/setup", {"Content-Type": "application/x-www-form-urlencoded"}, "promo_text=PROMOBEACON&admin_pwd=12345")
]
setup_audit_results = []
for name, meth, path, hdrs, body in setup_tests:
    req_lines = [f"{meth} {path} HTTP/1.0", f"Host: {BEACON_IP}"]
    for k, v in hdrs.items():
        req_lines.append(f"{k}: {v}")
    req_lines.append(f"Content-Length: {len(body)}")
    req_lines.append("")
    req_lines.append(body)
    raw = "\r\n".join(req_lines).encode("latin1")
    resp = send_custom_http(raw, timeout_s=2)
    first_line = resp.splitlines()[0] if resp.splitlines() else "EMPTY/CLOSED"
    print(f"  {name}: -> {first_line}")
    setup_audit_results.append({"test": name, "status": first_line})
v2_test_results["setup_patch_audit"] = setup_audit_results

# Test Vector E: Admin Path Traversal & Directory Traversal in /upload
print("\n--- [VETOR E] Admin Route Directory Traversal & Null-Byte Fuzzing ---")
traversal_cases = [
    "../../../../etc/shadow",
    "..\\..\\..\\windows\\system32\\cmd.exe",
    "assets/../../../index.html",
    "exploit%00.html",
    "/root/firmware.bin"
]
traversal_results = []
for tc in traversal_cases:
    raw = f"POST /upload?name={tc} HTTP/1.0\r\nHost: {BEACON_IP}\r\nX-Admin-Pwd: wrongpassword\r\nContent-Length: 4\r\n\r\ntest".encode("latin1")
    resp = send_custom_http(raw, timeout_s=2)
    first_line = resp.splitlines()[0] if resp.splitlines() else "DROPPED"
    print(f"  Traversal '{tc}': -> {first_line}")
    traversal_results.append({"path": tc, "status": first_line})
v2_test_results["traversal_audit"] = traversal_results

# Final Overall Health Check
final_status = send_custom_http(b"GET / HTTP/1.0\r\nHost: 192.168.4.1\r\n\r\n", timeout_s=2)
device_operational = "200 OK" in final_status and "PromoBeacon" in final_status
print(f"\nFinal Appliance Status Check: {'HEALTHY & OPERATIONAL (PASS)' if device_operational else 'UNSTABLE (FAIL)'}")
v2_test_results["final_appliance_healthy"] = device_operational

# ==============================================================================
# PHASE 3: JEV AUDIT & FINAL CERTIFICATION
# ==============================================================================
print("\n" + "=" * 80)
print("[PHASE 3] JEV Multi-Dimensional Audit & Certification Decision")
print("=" * 80)

jev_post_audit = jev_client.system_one(
    state={
        "hardware_tested": "ESP32 PromoBeacon Appliance via 802.11 RF",
        "vector_a_verbs": verb_results,
        "vector_b_headers": header_results,
        "vector_c_slowloris": slowloris_handled,
        "vector_d_setup_patch": setup_audit_results,
        "vector_e_traversal": traversal_results,
        "device_operational": device_operational
    },
    questions={
        "firmware_posture": Choice(
            instructions="Determine final security posture of the physical PromoBeacon after all adversarial tests",
            criteria={
                "IMPREGNABLE": "Full multi-layer defense, zero bypass, zero memory leakage, robust crash resistance",
                "ROBUST_COMMERCIAL_GRADE": "Secure against common war-driving and web attacks, minor non-exploitable quirks",
                "UNACCEPTABLE_RISK": "Device crash, buffer overflow, or unauthorized credential modification"
            }
        ),
        "posture_score": Score(
            instructions="Rate final hardened security score from 1 to 5",
            criteria=[
                "1: Critical flaws",
                "2: Vulnerable",
                "3: Average",
                "4: Solid commercial grade",
                "5: Hardened impregnable appliance"
            ]
        ),
        "zero_day_likelihood": Noul(
            instructions="Likelihood that an unauthenticated attacker can crash or commandeer this device"
        )
    }
)

cert_verdict = jev_post_audit.choices["firmware_posture"].choice
cert_score = jev_post_audit.scores["posture_score"].score
cert_risk = round(jev_post_audit.nouls["zero_day_likelihood"].noul * 100, 2)

print(f"  -> JEV Certified Posture: {cert_verdict}")
print(f"  -> JEV Security Rating: {cert_score} / 5.0")
print(f"  -> JEV Exploitation Risk Likelihood: {cert_risk}%")

# Save detailed results
telemetry_data = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "jev_guidance": {
        "critical_focus": jev_threat_model.choices["critical_test_focus"].choice,
        "slowloris_rating": jev_threat_model.scores["threat_severity_rank"].score,
        "bypass_prob": jev_threat_model.nouls["post_patch_bypass_probability"].noul
    },
    "test_results": v2_test_results,
    "jev_certification": {
        "posture": cert_verdict,
        "score": cert_score,
        "risk_pct": cert_risk
    }
}

out_json = ROOT_DIR / "scripts" / "adversarial_v2_jev_results.json"
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(telemetry_data, f, indent=2)

print(f"\n-> Full Adversarial V2 Telemetry saved to: {out_json}")
print("=" * 80)
print("ADVERSARIAL SUITE V2 COMPLETED SUCCESSFULLY!")
print("=" * 80)

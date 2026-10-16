#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_all_final.py — Final Comprehensive Physical Hardware Validation
======================================================================
Target: ESP32-C3 PromoBeacon (192.168.4.1) running patched firmware
Attacker: Samsung Galaxy Tablet (R9PW30T4JQM)
Intelligence: JEV (TypeSafe AI Engine)
"""

import os
import sys
import time
import json
import subprocess
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
TMP_BIN = ROOT_DIR / "scripts" / "tmp_final.bin"

load_dotenv(Path("C:/Users/rafae/.gemini/config/skills/typesafe/.env"))
from typesafe_sdk import TypeSafeClient, Choice, Score
jev_client = TypeSafeClient()

def run_adb(cmd, timeout=10):
    full_cmd = ["adb", "-s", SERIAL_DEVICE, "shell", cmd]
    try:
        res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
        return res.returncode, res.stdout, res.stderr
    except Exception as e:
        return -1, "", str(e)

def send_tcp_http(payload_bytes, timeout_s=3):
    with open(TMP_BIN, "wb") as f:
        f.write(payload_bytes)
    subprocess.run(["adb", "-s", SERIAL_DEVICE, "push", str(TMP_BIN), "/data/local/tmp/pay_f.bin"], capture_output=True)
    res = subprocess.run(["adb", "-s", SERIAL_DEVICE, "shell", f"cat /data/local/tmp/pay_f.bin | nc -w {timeout_s} {BEACON_IP} 80"], capture_output=True, text=True, timeout=timeout_s+3)
    return res.stdout

def send_udp_dns(payload_bytes, timeout_s=2):
    with open(TMP_BIN, "wb") as f:
        f.write(payload_bytes)
    subprocess.run(["adb", "-s", SERIAL_DEVICE, "push", str(TMP_BIN), "/data/local/tmp/pay_f.bin"], capture_output=True)
    res = subprocess.run(["adb", "-s", SERIAL_DEVICE, "shell", f"cat /data/local/tmp/pay_f.bin | nc -u -w {timeout_s} -q 1 {BEACON_IP} 53 | xxd -p"], capture_output=True, text=True, timeout=timeout_s+3)
    return res.stdout.strip()

print("=" * 80)
print("🛡️ VALIDAÇÃO FINAL EM HARDWARE FÍSICO — ESP32-C3 COM NOVO PATCH")
print("=" * 80)

# Connect to Wi-Fi
print("\n[PASSO 1] Verificando conexão Wi-Fi do Tablet...")
_, ip_out, _ = run_adb("ip addr show wlan0")
ips = [l.strip() for l in ip_out.splitlines() if 'inet ' in l]

if not any("192.168.4." in ip for ip in ips):
    print("  Conectando ao PROMOBEACON...")
    run_adb("input keyevent 4")
    run_adb("am start -a android.settings.WIFI_SETTINGS")
    time.sleep(1.5)
    for _ in range(3):
        run_adb("input tap 533 468")
        time.sleep(2)
        run_adb("input tap 568 1115")
        time.sleep(1)
        _, ip_out, _ = run_adb("ip addr show wlan0")
        ips = [l.strip() for l in ip_out.splitlines() if 'inet ' in l]
        if any("192.168.4." in ip for ip in ips):
            break

print(f"  Tablet wlan0 IP: {ips}")

tests = {}

# TESTE 1: /stats.csv desautenticado (DEVE SER BLOQUEADO COM 401!)
print("\n[TESTE 1] GET /stats.csv Desautenticado (Verificação da Nova Correção)")
req1 = b"GET /stats.csv HTTP/1.0\r\nHost: 192.168.4.1\r\n\r\n"
res1 = send_tcp_http(req1, timeout_s=3)
line1 = res1.splitlines()[0] if res1.splitlines() else "NO_RESP"
print(f"  -> Resposta: {line1}")
tests["stats_unauth"] = line1

# TESTE 2: /stats.csv autenticado com senha de admin (DEVE RETORNAR 200 OK!)
print("\n[TESTE 2] GET /stats.csv com Autenticação Admin (X-Admin-Pwd: 12345)")
req2 = b"GET /stats.csv HTTP/1.0\r\nHost: 192.168.4.1\r\nX-Admin-Pwd: 12345\r\n\r\n"
res2 = send_tcp_http(req2, timeout_s=3)
line2 = res2.splitlines()[0] if res2.splitlines() else "NO_RESP"
print(f"  -> Resposta: {line2}")
tests["stats_auth"] = line2

# TESTE 3: /setup desautenticado (DEVE SER 401)
print("\n[TESTE 3] POST /setup Desautenticado (Sequestro de SSID)")
req3 = b"POST /setup HTTP/1.0\r\nHost: 192.168.4.1\r\nContent-Length: 26\r\n\r\npromo_text=HACKED_BEACON"
res3 = send_tcp_http(req3, timeout_s=3)
line3 = res3.splitlines()[0] if res3.splitlines() else "NO_RESP"
print(f"  -> Resposta: {line3}")
tests["setup_unauth"] = line3

# TESTE 4: DNS UDP na porta 53 (DEVE RESPONDER COM IP DO BEACON)
print("\n[TESTE 4] Consulta DNS UDP (Porta 53)")
req4 = b"\xaa\xbb\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x06portal\x03com\x00\x00\x01\x00\x01"
res4 = send_udp_dns(req4, timeout_s=2)
dns_ok = "c0a80401" in res4
print(f"  -> DNS Resolvido: {'✅ 192.168.4.1' if dns_ok else '❌ FALHA'}")
tests["dns_functional"] = dns_ok

# TESTE 5: Path Traversal em /assets/*
print("\n[TESTE 5] Path Traversal em /assets/../../etc/passwd")
req5 = b"GET /assets/../../etc/passwd HTTP/1.0\r\nHost: 192.168.4.1\r\n\r\n"
res5 = send_tcp_http(req5, timeout_s=2)
line5 = res5.splitlines()[0] if res5.splitlines() else "NO_RESP"
print(f"  -> Resposta: {line5}")
tests["traversal"] = line5

# AVALIAÇÃO FINAL JEV
print("\n" + "=" * 80)
print("[JEV] Certificação Final do Silício com TypeSafe AI...")
print("=" * 80)

jev_cert = jev_client.system_one(
    state=tests,
    questions={
        "status": Choice(
            instructions="Qual o status final de segurança do hardware físico após todas as correções?",
            criteria={
                "IMPREGNABLE": "Todas as vulnerabilidades foram mitigadas com 401/400/lockout, privacidade protegida, DNS e portal íntegros",
                "STILL_LEAKING": "Ainda existe vazamento de telemetria ou brecha aberta",
                "FAILED": "O dispositivo travou ou falhou nos testes"
            }
        ),
        "overall_grade": Score(
            instructions="Nota final da arquitetura de segurança física do PromoBeacon de 1 a 5",
            criteria=["1: Inseguro", "3: Aceitável", "5: Excelente / Padrão Militar"]
        )
    }
)

final_status = jev_cert.choices["status"].choice
final_grade = jev_cert.scores["overall_grade"].score

print(f"  -> Veredito Final JEV: {final_status}")
print(f"  -> Nota Global de Segurança: {final_grade} / 5.0")
print("=" * 80)

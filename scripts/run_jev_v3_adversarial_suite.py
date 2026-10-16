#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_jev_v3_adversarial_suite.py — Deep Code-Driven Physical Adversarial Suite
=============================================================================
Target: ESP32-C3 PromoBeacon (192.168.4.1)
Attacker: Physical Samsung Galaxy Tablet (R9PW30T4JQM)
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
TMP_BIN = ROOT_DIR / "scripts" / "tmp_payload_v3.bin"

load_dotenv(Path("C:/Users/rafae/.gemini/config/skills/typesafe/.env"))
from typesafe_sdk import TypeSafeClient, Choice, Score
jev_client = TypeSafeClient()

def send_tcp_http(payload_bytes, timeout_s=3):
    with open(TMP_BIN, "wb") as f:
        f.write(payload_bytes)
    subprocess.run(["adb", "-s", SERIAL_DEVICE, "push", str(TMP_BIN), "/data/local/tmp/pay_v3.bin"], capture_output=True)
    res = subprocess.run(["adb", "-s", SERIAL_DEVICE, "shell", f"cat /data/local/tmp/pay_v3.bin | nc -w {timeout_s} {BEACON_IP} 80"], capture_output=True, text=True, timeout=timeout_s+3)
    return res.stdout

def send_udp_dns(payload_bytes, timeout_s=2):
    with open(TMP_BIN, "wb") as f:
        f.write(payload_bytes)
    subprocess.run(["adb", "-s", SERIAL_DEVICE, "push", str(TMP_BIN), "/data/local/tmp/pay_v3.bin"], capture_output=True)
    res = subprocess.run(["adb", "-s", SERIAL_DEVICE, "shell", f"cat /data/local/tmp/pay_v3.bin | nc -u -w {timeout_s} -q 1 {BEACON_IP} 53 | xxd -p"], capture_output=True, text=True, timeout=timeout_s+3)
    return res.stdout.strip()

def check_beacon_alive():
    resp = send_tcp_http(b"GET / HTTP/1.0\r\nHost: 192.168.4.1\r\n\r\n", timeout_s=2)
    return "HTTP/1.1 200 OK" in resp or "302" in resp

print("=" * 80)
print("🛡️ INICIANDO SUÍTE ADVERSÁRIA V3 GUIADA POR CÓDIGO & MOTOR JEV (TYPESAFE AI)")
print("=" * 80)

# ------------------------------------------------------------------------------
# FASE 1: Brainstorming & Threat Modeling de Código com JEV
# ------------------------------------------------------------------------------
print("\n[JEV PHASE 1] Analisando superfície de ataque do código C (ESP-IDF)...")
code_summary = """
Componentes analisados no firmware PromoBeacon:
1. web_server.c:
   - GET /assets/* -> snprintf(filepath, sizeof(filepath), "/storage%s", req->uri); fopen()
   - POST /update -> ota_begin(), ota_write() protegido por check_and_enforce_http_admin_auth()
   - GET /stats.csv -> malloc(12288) por requisição para geração dinâmica de CSV
   - URI e Header Parsing sob httpd do ESP-IDF
2. wifi_manager.c:
   - handle_dns_requests() em UDP 53 com parsing manual de ponteiros de labels DNS (ptr += *ptr + 1)
"""

jev_threat_model = jev_client.system_one(
    state={"firmware_surface": code_summary},
    questions={
        "top_vector": Choice(
            instructions="Qual o vetor de maior potencial de crash ou DoS imediato no silício?",
            criteria={
                "DNS_MALFORMED_PTR": "Parsing manual de pacotes UDP na porta 53 com manipulação de ponteiros de label",
                "ASSET_TRAVERSAL": "Path traversal em /assets/* tentando vazar arquivos de configuração ou bater no VFS",
                "STATS_HEAP_EXHAUSTION": "Esgotamento de heap por chamadas repetidas a malloc(12KB) em /stats.csv",
                "OTA_UNAUTH_TAMPER": "Tentativa de injeção de binário malicioso em /update"
            }
        ),
        "test_rigor": Score(
            instructions="Avalie o rigor necessário para a bateria de testes de 1 a 5",
            criteria=["1: Básico", "3: Intermediário", "5: Exaustivo de Grau Militar"]
        )
    }
)

top_vector = jev_threat_model.choices["top_vector"].choice
rigor = jev_threat_model.scores["test_rigor"].score
print(f"  -> Prioridade de Risco JEV: {top_vector}")
print(f"  -> Rigor de Teste Definido: {rigor} / 5.0")

results = {}

# ------------------------------------------------------------------------------
# TESTE 1: Fuzzing & Malformed Packets no Servidor DNS (UDP 53)
# ------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("[TESTE 1] Fuzzing de DNS UDP: Pacote Truncado e Label Length Overflow")
print("=" * 80)

# 1a. Truncated packet (< 12 bytes)
t1a_payload = b"\x12\x34\x01\x00\x00\x01" # Only 6 bytes
resp1a = send_udp_dns(t1a_payload)
print(f"  1a. DNS Truncado (6 bytes): Resposta -> '{resp1a}' (Esperado: Vazio/Descarte)")

# 1b. Label Length Pointer Overflow: Claim 250 bytes label with short payload
t1b_payload = b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\xfa" + b"A" * 15 + b"\x00\x00\x01\x00\x01"
resp1b = send_udp_dns(t1b_payload)
print(f"  1b. DNS Label Overflow: Resposta -> '{resp1b}' (Esperado: Descarte seguro sem crash)")

# 1c. Valid DNS Query immediately after (Probe liveness)
t1c_payload = b"\xaa\xbb\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x06google\x03com\x00\x00\x01\x00\x01"
resp1c = send_udp_dns(t1c_payload)
dns_healthy = "c0a80401" in resp1c
print(f"  1c. Sonda de Integridade DNS pós-fuzzing: {'✅ DNS OPERACIONAL' if dns_healthy else '❌ DNS TRAVADO'}")
results["dns_fuzzing"] = {"truncated_dropped": len(resp1a) == 0, "overflow_dropped": len(resp1b) == 0, "dns_healthy": dns_healthy}

# ------------------------------------------------------------------------------
# TESTE 2: Directory Traversal em /assets/*
# ------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("[TESTE 2] Path Traversal em /assets/* (Fuzzing de VFS / Storage)")
print("=" * 80)
traversal_paths = [
    "/assets/../../etc/passwd",
    "/assets/..%2f..%2fspiffs/config.json",
    "/assets/....//....//config.json",
    "/assets/%00/root"
]
traversal_results = []
for p in traversal_paths:
    req = f"GET {p} HTTP/1.0\r\nHost: 192.168.4.1\r\n\r\n".encode("latin1")
    r = send_tcp_http(req, timeout_s=2)
    status_line = r.splitlines()[0] if r.splitlines() else "EMPTY"
    print(f"  Path: {p} -> {status_line}")
    traversal_results.append((p, status_line))

results["traversal"] = traversal_results

# ------------------------------------------------------------------------------
# TESTE 3: Esgotamento de Heap / Stress em /stats.csv (12KB malloc spam)
# ------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("[TESTE 3] Stress de Heap em /stats.csv (Rajada de 8 requisições simultâneas/rápidas)")
print("=" * 80)
stats_statuses = []
for i in range(8):
    req = b"GET /stats.csv HTTP/1.0\r\nHost: 192.168.4.1\r\n\r\n"
    r = send_tcp_http(req, timeout_s=2)
    s = r.splitlines()[0] if r.splitlines() else "NO_RESP"
    stats_statuses.append(s)

print(f"  Respostas das 8 rajadas: {stats_statuses}")
alive_after_stats = check_beacon_alive()
print(f"  ESP32 vivo após rajadas de malloc: {'✅ VIVO' if alive_after_stats else '❌ CRASH'}")
results["heap_stress"] = {"responses": stats_statuses, "alive": alive_after_stats}

# ------------------------------------------------------------------------------
# TESTE 4: Tentativa de Injeção de Firmware OTA Desautenticada (/update)
# ------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("[TESTE 4] Tentativa de Injeção de Firmware OTA Desautenticada (POST /update)")
print("=" * 80)
fake_firmware = b"\xeb\xfe\x00\x00" * 256 # 1024 bytes of garbage binary
req_ota = (
    b"POST /update HTTP/1.0\r\n"
    b"Host: 192.168.4.1\r\n"
    b"Content-Type: application/octet-stream\r\n"
    b"Content-Length: 1024\r\n\r\n" +
    fake_firmware
)
resp_ota = send_tcp_http(req_ota, timeout_s=3)
ota_line = resp_ota.splitlines()[0] if resp_ota.splitlines() else "EMPTY"
print(f"  Resposta ao POST /update desautenticado: {ota_line}")
results["ota_injection"] = ota_line

# ------------------------------------------------------------------------------
# TESTE 5: Fuzzing de Linha de Requisição Extrema (URI de 1024 bytes)
# ------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("[TESTE 5] Fuzzing de URI Gigante (1024 bytes no Path)")
print("=" * 80)
long_uri = "/test_" + ("A" * 1000)
req_long = f"GET {long_uri} HTTP/1.0\r\nHost: 192.168.4.1\r\n\r\n".encode("latin1")
resp_long = send_tcp_http(req_long, timeout_s=2)
long_line = resp_long.splitlines()[0] if resp_long.splitlines() else "EMPTY"
print(f"  Resposta a URI de 1024 bytes: {long_line}")
alive_final = check_beacon_alive()
print(f"  Estado Final do Hardware ESP32: {'✅ OPERACIONAL E ÍNTEGRO' if alive_final else '❌ MORTO'}")
results["uri_fuzzing"] = {"response": long_line, "alive_final": alive_final}

# ------------------------------------------------------------------------------
# FASE 2: Avaliação Final pelo JEV (TypeSafe AI)
# ------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("[JEV PHASE 2] Submetendo Evidências de Silício ao Motor de Decisão...")
print("=" * 80)

jev_cert = jev_client.system_one(
    state={
        "dns_results": results["dns_fuzzing"],
        "traversal_results": results["traversal"],
        "heap_stress_results": results["heap_stress"],
        "ota_results": results["ota_injection"],
        "uri_fuzzing_results": results["uri_fuzzing"]
    },
    questions={
        "resilience_status": Choice(
            instructions="Avalie a resiliência física do hardware sob a suíte V3",
            criteria={
                "IMPREGNABLE": "Todos os vetores foram neutralizados com segurança, o microcontrolador manteve estabilidade total",
                "MINOR_LEAK": "O dispositivo sobreviveu mas revelou pequenas inconsistências de código",
                "CRITICAL_FAILURE": "Ocorreu crash, DoS no rádio ou comprometimento de integridade"
            }
        ),
        "defense_score": Score(
            instructions="Pontuação da blindagem física do ESP32-C3 de 1 a 5",
            criteria=["1: Vulnerável", "3: Médio", "5: Blindagem de Nível Militar"]
        )
    }
)

resilience = jev_cert.choices["resilience_status"].choice
score = jev_cert.scores["defense_score"].score

print(f"  -> Resiliência de Hardware JEV: {resilience}")
print(f"  -> Nota Definitiva de Segurança: {score} / 5.0")
print("=" * 80)

# Save test results to JSON
with open(ROOT_DIR / "scripts" / "v3_test_results.json", "w", encoding="utf-8") as f:
    json.dump({
        "timestamp": time.time(),
        "rigor": rigor,
        "results": results,
        "jev_verdict": resilience,
        "jev_score": score
    }, f, indent=2)

print("\nResultados salvos com sucesso em scripts/v3_test_results.json.")

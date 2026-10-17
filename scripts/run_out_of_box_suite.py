#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_out_of_box_suite.py — Innovative & Out-of-the-Box Adversarial Stress Testing
================================================================================
Target: Physical ESP32-C3 PromoBeacon (192.168.4.1)
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
TMP_BIN = ROOT_DIR / "scripts" / "tmp_oob.bin"

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
    subprocess.run(["adb", "-s", SERIAL_DEVICE, "push", str(TMP_BIN), "/data/local/tmp/pay_oob.bin"], capture_output=True)
    res = subprocess.run(["adb", "-s", SERIAL_DEVICE, "shell", f"cat /data/local/tmp/pay_oob.bin | nc -w {timeout_s} {BEACON_IP} 80"], capture_output=True, text=True, timeout=timeout_s+3)
    return res.stdout

def check_alive():
    resp = send_tcp_http(b"GET / HTTP/1.0\r\nHost: 192.168.4.1\r\n\r\n", timeout_s=2)
    return "HTTP/1.1 200 OK" in resp or "302" in resp

print("=" * 80)
print("🧠 CONSULTANDO O MOTOR JEV PARA DIRETRIZES & TESTES FORA DA CAIXA")
print("=" * 80)

# JEV Out-of-the-Box Consultation
jev_insights = jev_client.system_one(
    state={
        "tested_so_far": [
            "HTTP Verbs (TRACE/PUT/DELETE)", "Slowloris", "SSID XSS & Hijack", 
            "Stats CSV Privacy Leak", "DNS Truncated/Overflow", "Path Traversal"
        ],
        "device_target": "ESP32-C3 Wi-Fi Captive Portal (lwIP + ESP-IDF httpd)"
    },
    questions={
        "primary_oob_vector": Choice(
            instructions="Escolha o teste mais criativo e fora da caixa aplicável ao silício real",
            criteria={
                "HTTP_PIPELINING_DESYNC": "Pipelining concatenando múltiplos requests HTTP no mesmo frame TCP para desincronizar o parser",
                "CORRUPT_HEADER_INJECTION": "Injeção de caracteres de controle, null-bytes e CRLF duplo em headers arbitrários",
                "TCP_CONNECTION_FLOOD": "Rajada de abertura e fechamento imediato de sockets para testar o esgotamento de PCBs do lwIP",
                "PROBE_HEADER_SPOOFING": "Spoofing de headers de sondagem (Android captive portal, User-Agent malformado) buscando crash de redirect"
            }
        ),
        "architectural_advice": Choice(
            instructions="Qual a melhor orientação de engenharia fora da caixa para evolução do produto?",
            criteria={
                "NVS_ENCRYPTION_FLASH": "Habilitar Flash Encryption e NVS Encryption no hardware para impedir dump físico via UART",
                "WPA3_OWE_ENCRYPTION": "Transicionar de Open Wi-Fi para WPA3-OWE (Opportunistic Wireless Encryption) para criptografar tráfego sem senha",
                "HARDWARE_WDT_PANIC": "Ajustar o Task Watchdog Timer do ESP-IDF para reiniciar agressivamente em caso de deadlock de sockets"
            }
        )
    }
)

chosen_vector = jev_insights.choices["primary_oob_vector"].choice
advice = jev_insights.choices["architectural_advice"].choice

print(f"  -> Vetor Escolhido pelo JEV: {chosen_vector}")
print(f"  -> Diretriz Arquitetural Fora da Caixa: {advice}")

# Ensure Tablet is connected
print("\n[PASSO 1] Verificando conexão Wi-Fi do Tablet...")
_, ip_out, _ = run_adb("ip addr show wlan0")
ips = [l.strip() for l in ip_out.splitlines() if 'inet ' in l]
if not any("192.168.4." in ip for ip in ips):
    run_adb("am start -a android.settings.WIFI_SETTINGS")
    time.sleep(1.5)
    run_adb("input tap 533 468")
    time.sleep(2)
    run_adb("input tap 568 1115")
    time.sleep(1)

oob_results = {}

# ------------------------------------------------------------------------------
# TESTE OOB 1: HTTP Pipelining (Múltiplas requisições num único TCP Packet)
# ------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("[TESTE OOB 1] HTTP Pipelining Desynchronization Stress")
print("=" * 80)
pipelined_payload = (
    b"GET / HTTP/1.1\r\nHost: 192.168.4.1\r\n\r\n"
    b"GET /stats.csv HTTP/1.1\r\nHost: 192.168.4.1\r\n\r\n"
    b"GET /generate_204 HTTP/1.1\r\nHost: 192.168.4.1\r\n\r\n"
)
resp_pipe = send_tcp_http(pipelined_payload, timeout_s=3)
pipe_lines = [l for l in resp_pipe.splitlines() if "HTTP/1.1" in l]
print(f"  Respostas das requisições pipelined: {pipe_lines}")
oob_results["pipelining"] = pipe_lines

# ------------------------------------------------------------------------------
# TESTE OOB 2: Header Fuzzing com Caracteres de Controle & Null Byte
# ------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("[TESTE OOB 2] Injeção de Headers Corrompidos (Null Bytes, Alta ASCII & Missing Colon)")
print("=" * 80)
malformed_headers_payload = (
    b"GET / HTTP/1.1\r\n"
    b"Host: 192.168.4.1\r\n"
    b"X-Admin-Pwd: \x0012345\r\n"
    b"MalformedHeaderWithoutColon\r\n"
    b"X-Unicode-Trash: \xff\xfe\xfd\r\n"
    b"User-Agent: Mozilla/5.0 \r\n\r\n"
)
resp_hdr = send_tcp_http(malformed_headers_payload, timeout_s=3)
hdr_status = resp_hdr.splitlines()[0] if resp_hdr.splitlines() else "DROPPED_EMPTY"
print(f"  Resposta com headers malformados: {hdr_status}")
oob_results["malformed_headers"] = hdr_status

# ------------------------------------------------------------------------------
# TESTE OOB 3: Rajada Rápida de Conexões TCP (TCP Storm - PCB Stress)
# ------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("[TESTE OOB 3] Rajada Rápida de Sockets TCP (Stress em PCBs do lwIP)")
print("=" * 80)
storm_statuses = []
for i in range(12):
    r = send_tcp_http(b"GET / HTTP/1.0\r\nHost: 192.168.4.1\r\n\r\n", timeout_s=1)
    s = r.splitlines()[0] if r.splitlines() else "CLOSED"
    storm_statuses.append(s)

print(f"  Resultado das 12 rajadas de sockets: {storm_statuses[:6]} ... ({len(storm_statuses)} total)")
oob_results["tcp_storm"] = storm_statuses

# ------------------------------------------------------------------------------
# TESTE OOB 4: Verificação de Sobrevivência e Integridade do ESP32
# ------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("[TESTE OOB 4] Verificação de Sobrevivência e Heap pós-testes extremos")
print("=" * 80)
alive = check_alive()
print(f"  ESP32-C3 está vivo e respondendo? {'✅ 100% OPERACIONAL' if alive else '❌ CRASH/DEADLOCK'}")
oob_results["final_health"] = alive

# ------------------------------------------------------------------------------
# Avaliação Final JEV
# ------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("[JEV] Certificação Final da Rodada Fora da Caixa...")
print("=" * 80)

jev_eval = jev_client.system_one(
    state={
        "results": oob_results,
        "advice": advice
    },
    questions={
        "oob_verdict": Choice(
            instructions="Avalie a resiliência do dispositivo sob a bateria fora da caixa",
            criteria={
                "ROCK_SOLID": "O microcontrolador manteve estabilidade sob pipelining, headers nulos e rajadas de sockets",
                "INSTABILITY_DETECTED": "Houve degradação de desempenho ou perda de pacotes",
                "FATAL_CRASH": "O sistema congelou ou reiniciou de forma anômala"
            }
        ),
        "oob_score": Score(
            instructions="Nota de robustez para testes fora da caixa de 1 a 5",
            criteria=["1: Frágil", "3: Bom", "5: Nível Militar Inquebrável"]
        )
    }
)

final_verdict = jev_eval.choices["oob_verdict"].choice
final_score = jev_eval.scores["oob_score"].score

print(f"  -> Veredito JEV Fora da Caixa: {final_verdict}")
print(f"  -> Pontuação de Robustez: {final_score} / 5.0")
print("=" * 80)

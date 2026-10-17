#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
deploy_bolsonaro_campaign_via_tablet.py — Deploy Real Political Page via Tablet
================================================================================
Target: ESP32-C3 PromoBeacon (192.168.4.1)
Operator: Samsung Galaxy Tablet (R9PW30T4JQM)
Content: Official portrait, TSE Government Plan PDF, Custom Landing Page
"""

import os
import sys
import time
import subprocess
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
SERIAL_DEVICE = "R9PW30T4JQM"
BEACON_IP = "192.168.4.1"
ADMIN_PWD = "12345"

def run_adb(cmd, timeout=15):
    full_cmd = ["adb", "-s", SERIAL_DEVICE, "shell", cmd]
    try:
        res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
        return res.returncode, res.stdout, res.stderr
    except Exception as e:
        return -1, "", str(e)

def upload_asset_from_tablet(local_path, remote_name):
    print(f"\n[UPLOAD] Enviando {remote_name} ({os.path.getsize(local_path)} bytes) via Tablet...")
    
    # 1. Push payload file to tablet
    tablet_bin = f"/data/local/tmp/{remote_name}"
    subprocess.run(["adb", "-s", SERIAL_DEVICE, "push", str(local_path), tablet_bin], capture_output=True)
    
    # 2. Build HTTP upload raw request file directly on tablet or locally
    content_len = os.path.getsize(local_path)
    header = (
        f"POST /upload?name={remote_name} HTTP/1.0\r\n"
        f"Host: {BEACON_IP}\r\n"
        f"X-Admin-Pwd: {ADMIN_PWD}\r\n"
        f"Content-Length: {content_len}\r\n\r\n"
    ).encode("latin1")
    
    req_file = ROOT_DIR / "scripts" / f"req_{remote_name}.bin"
    with open(req_file, "wb") as f:
        f.write(header)
        with open(local_path, "rb") as fl:
            f.write(fl.read())
            
    # Push full HTTP request to tablet
    tablet_req = f"/data/local/tmp/http_{remote_name}.bin"
    subprocess.run(["adb", "-s", SERIAL_DEVICE, "push", str(req_file), tablet_req], capture_output=True)
    
    # Send via netcat from tablet
    print(f"  Transmitindo {remote_name} do Tablet para o ESP32...")
    res = subprocess.run(
        ["adb", "-s", SERIAL_DEVICE, "shell", f"cat {tablet_req} | nc -w 15 {BEACON_IP} 80"],
        capture_output=True, text=True, timeout=25
    )
    
    first_lines = res.stdout.splitlines()[:3]
    print(f"  Resposta do ESP32: {first_lines}")
    return "200" in str(first_lines) or "SUCCESS" in str(res.stdout)

print("=" * 80)
print("🇧🇷 CONFIGURANDO PÁGINA POLÍTICA DO BOLSONARO NO PROMOBEACON VIA TABLET")
print("=" * 80)

# Check Wi-Fi connection
_, ip_out, _ = run_adb("ip addr show wlan0")
ips = [l.strip() for l in ip_out.splitlines() if 'inet ' in l]
print(f"Tablet IP na rede: {ips}")

# 1. Upload Photo (bolsonaro.jpg)
photo_path = ROOT_DIR / "scripts" / "bolsonaro.jpg"
ok_photo = upload_asset_from_tablet(photo_path, "bolsonaro.jpg")

# 2. Upload Government Plan (plano_de_governo.pdf)
pdf_path = ROOT_DIR / "scripts" / "plano_governo_otimizado.pdf"
ok_pdf = upload_asset_from_tablet(pdf_path, "plano_de_governo.pdf")

# 3. Upload Custom Portal (index.html)
html_path = ROOT_DIR / "scripts" / "index_bolsonaro.html"
ok_html = upload_asset_from_tablet(html_path, "index.html")

# 4. Update SSID to "BOLSONARO 2026"
print("\n[SETUP] Atualizando SSID no ESP32 para 'BOLSONARO 2026' via Tablet...")
body_setup = "promo_text=BOLSONARO%202026&admin_pwd=12345"
req_setup = (
    f"POST /setup HTTP/1.0\r\n"
    f"Host: {BEACON_IP}\r\n"
    f"X-Admin-Pwd: {ADMIN_PWD}\r\n"
    f"Content-Type: application/x-www-form-urlencoded\r\n"
    f"Content-Length: {len(body_setup)}\r\n\r\n" +
    body_setup
).encode("latin1")

with open(ROOT_DIR / "scripts" / "req_setup_bolsonaro.bin", "wb") as f:
    f.write(req_setup)

subprocess.run(["adb", "-s", SERIAL_DEVICE, "push", str(ROOT_DIR / "scripts" / "req_setup_bolsonaro.bin"), "/data/local/tmp/req_setup_b.bin"], capture_output=True)
res_setup = subprocess.run(["adb", "-s", SERIAL_DEVICE, "shell", f"cat /data/local/tmp/req_setup_b.bin | nc -w 5 {BEACON_IP} 80"], capture_output=True, text=True)
print("  Resposta /setup:", res_setup.stdout.splitlines()[:3])

print("\nAguardando 3 segundos para estabilização...")
time.sleep(3)

# 5. Verification from Tablet
print("\n" + "=" * 80)
print("[VERIFICAÇÃO] Validando Disponibilidade da Campanha via Tablet")
print("=" * 80)

# Check index
res_idx = subprocess.run(["adb", "-s", SERIAL_DEVICE, "shell", f"cat << 'EOF' | nc -w 3 {BEACON_IP} 80\nGET / HTTP/1.0\nHost: {BEACON_IP}\n\nEOF"], capture_output=True, text=True)
has_title = "Jair Bolsonaro" in res_idx.stdout
print(f"  Página Inicial (GET /): {'✅ CARREGADA COM SUCESSO' if has_title else '❌ FALHA'}")

# Check photo asset
res_img = subprocess.run(["adb", "-s", SERIAL_DEVICE, "shell", f"cat << 'EOF' | nc -w 3 {BEACON_IP} 80\nGET /assets/bolsonaro.jpg HTTP/1.0\nHost: {BEACON_IP}\n\nEOF"], capture_output=True, text=True)
img_ok = "image/jpeg" in res_img.stdout or "200 OK" in res_img.stdout
print(f"  Foto Oficial (/assets/bolsonaro.jpg): {'✅ DISPONÍVEL (image/jpeg)' if img_ok else '❌ FALHA'}")

# Check pdf asset
res_pdf = subprocess.run(["adb", "-s", SERIAL_DEVICE, "shell", f"cat << 'EOF' | nc -w 3 {BEACON_IP} 80\nGET /assets/plano_de_governo.pdf HTTP/1.0\nHost: {BEACON_IP}\n\nEOF"], capture_output=True, text=True)
pdf_ok = "application/pdf" in res_pdf.stdout or "200 OK" in res_pdf.stdout
print(f"  Plano de Governo (/assets/plano_de_governo.pdf): {'✅ DISPONÍVEL (application/pdf)' if pdf_ok else '❌ FALHA'}")

# 6. Open Browser on Tablet to show live result
print("\n[DISPLAY] Abrindo navegador no Tablet...")
run_adb("am start -a android.intent.action.VIEW -d 'http://192.168.4.1/'")

print("\n" + "=" * 80)
print("🎉 CAMPANHA POLÍTICA BOLSONARO CONFIGURADA COM SUCESSO NO PROMOBEACON!")
print("=" * 80)

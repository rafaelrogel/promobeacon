#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Pizzeria PromoBeacon Campaign
"""
import os
import subprocess
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SERIAL_DEVICE = "R9PW30T4JQM"
BEACON_IP = "192.168.4.1"
ADMIN_PWD = "12345"

def run_adb(cmd):
    return subprocess.run(["adb", "-s", SERIAL_DEVICE, "shell", cmd], capture_output=True, text=True)

# 1. Upload cardapio.pdf
pdf_path = ROOT_DIR / "scripts" / "cardapio_pizzaria.pdf"
pdf_len = os.path.getsize(pdf_path)
hdr_pdf = f"POST /upload?name=cardapio.pdf HTTP/1.0\r\nHost: {BEACON_IP}\r\nX-Admin-Pwd: {ADMIN_PWD}\r\nContent-Length: {pdf_len}\r\n\r\n".encode("latin1")
with open(ROOT_DIR / "scripts" / "req_cardapio.bin", "wb") as f:
    f.write(hdr_pdf)
    with open(pdf_path, "rb") as fp:
        f.write(fp.read())

print("Enviando cardapio.pdf para o tablet...")
subprocess.run(["adb", "-s", SERIAL_DEVICE, "push", str(ROOT_DIR / "scripts" / "req_cardapio.bin"), "/data/local/tmp/req_cardapio.bin"], capture_output=True)
res_g = run_adb(f"cat /data/local/tmp/req_cardapio.bin | nc -w 5 {BEACON_IP} 80")
print("Upload cardapio.pdf resposta:", res_g.stdout.splitlines()[:2])

# 2. Upload index.html
html_path = ROOT_DIR / "scripts" / "index_pizzaria.html"
html_len = os.path.getsize(html_path)
hdr_html = f"POST /upload?name=index.html HTTP/1.0\r\nHost: {BEACON_IP}\r\nX-Admin-Pwd: {ADMIN_PWD}\r\nContent-Length: {html_len}\r\n\r\n".encode("latin1")
with open(ROOT_DIR / "scripts" / "req_index_pizzaria.bin", "wb") as f:
    f.write(hdr_html)
    with open(html_path, "rb") as fh:
        f.write(fh.read())

print("Enviando index.html para o tablet...")
subprocess.run(["adb", "-s", SERIAL_DEVICE, "push", str(ROOT_DIR / "scripts" / "req_index_pizzaria.bin"), "/data/local/tmp/req_index_pizzaria.bin"], capture_output=True)
res_h = run_adb(f"cat /data/local/tmp/req_index_pizzaria.bin | nc -w 5 {BEACON_IP} 80")
print("Upload index.html resposta:", res_h.stdout.splitlines()[:2])

# 3. Update SSID via POST /setup
new_ssid = "PIZZA BELLA NAPOLI"
setup_body = f"promo_text={new_ssid}&wifi_pwd=&admin_pwd={ADMIN_PWD}"
setup_req = f"POST /setup HTTP/1.0\r\nHost: {BEACON_IP}\r\nX-Admin-Pwd: {ADMIN_PWD}\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: {len(setup_body)}\r\n\r\n{setup_body}".encode("latin1")
with open(ROOT_DIR / "scripts" / "req_setup_pizzaria.bin", "wb") as fs:
    fs.write(setup_req)

print(f"Atualizando SSID para '{new_ssid}' via POST /setup...")
subprocess.run(["adb", "-s", SERIAL_DEVICE, "push", str(ROOT_DIR / "scripts" / "req_setup_pizzaria.bin"), "/data/local/tmp/req_setup_pizzaria.bin"], capture_output=True)
res_s = run_adb(f"cat /data/local/tmp/req_setup_pizzaria.bin | nc -w 5 {BEACON_IP} 80")
print("Setup resposta:", res_s.stdout.splitlines()[:2])

print("Aguardando reinicializacao do ESP32 (4 segundos)...")
time.sleep(4)

# 4. Connect tablet to new SSID
print(f"Conectando tablet na rede '{new_ssid}'...")
run_adb(f"cmd -w wifi start-scan")
time.sleep(2)
run_adb(f"cmd -w wifi connect-network \"{new_ssid}\" open")
time.sleep(4)

# 5. Check if alive
print("Verificando se o portal esta respondendo...")
for attempt in range(5):
    res_ping = run_adb(f"echo 'GET / HTTP/1.0\r\nHost: 192.168.4.1\r\n\r\n' | nc -w 3 {BEACON_IP} 80")
    if "Bella Napoli" in res_ping.stdout:
        print("Portal confirmado online!")
        break
    time.sleep(2)

# 6. Verify asset /assets/cardapio.pdf
res_pdf = run_adb(f"echo 'GET /assets/cardapio.pdf HTTP/1.0\r\nHost: 192.168.4.1\r\n\r\n' | nc -w 3 {BEACON_IP} 80")
print("Asset cardapio.pdf status:", res_pdf.stdout.splitlines()[:3])

# 7. Launch browser
print("Abrindo navegador do tablet no portal...")
run_adb("am start -a android.intent.action.VIEW -d 'http://192.168.4.1/'")

print("Deploy concluido com sucesso!")

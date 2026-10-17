#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

# 1. Upload guia.pdf
pdf_path = ROOT_DIR / "scripts" / "guia_assistencia_familiar.pdf"
pdf_len = os.path.getsize(pdf_path)
hdr_pdf = f"POST /upload?name=guia.pdf HTTP/1.0\r\nHost: {BEACON_IP}\r\nX-Admin-Pwd: {ADMIN_PWD}\r\nContent-Length: {pdf_len}\r\n\r\n".encode("latin1")
with open(ROOT_DIR / "scripts" / "req_guia.bin", "wb") as f:
    f.write(hdr_pdf)
    with open(pdf_path, "rb") as fp:
        f.write(fp.read())

subprocess.run(["adb", "-s", SERIAL_DEVICE, "push", str(ROOT_DIR / "scripts" / "req_guia.bin"), "/data/local/tmp/req_g.bin"], capture_output=True)
res_g = run_adb(f"cat /data/local/tmp/req_g.bin | nc -w 5 {BEACON_IP} 80")
print("Upload guia.pdf resposta:", res_g.stdout.splitlines()[:2])

# 2. Upload index.html
html_path = ROOT_DIR / "scripts" / "index_funeraria.html"
html_len = os.path.getsize(html_path)
hdr_html = f"POST /upload?name=index.html HTTP/1.0\r\nHost: {BEACON_IP}\r\nX-Admin-Pwd: {ADMIN_PWD}\r\nContent-Length: {html_len}\r\n\r\n".encode("latin1")
with open(ROOT_DIR / "scripts" / "req_html.bin", "wb") as f:
    f.write(hdr_html)
    with open(html_path, "rb") as fh:
        f.write(fh.read())

subprocess.run(["adb", "-s", SERIAL_DEVICE, "push", str(ROOT_DIR / "scripts" / "req_html.bin"), "/data/local/tmp/req_h.bin"], capture_output=True)
res_h = run_adb(f"cat /data/local/tmp/req_h.bin | nc -w 5 {BEACON_IP} 80")
print("Upload index.html resposta:", res_h.stdout.splitlines()[:2])

# 3. Verify GET /
print("\n--- VERIFICANDO PÁGINA AO VIVO ---")
open(ROOT_DIR / "scripts" / "req_check.bin", "wb").write(b"GET / HTTP/1.0\r\nHost: 192.168.4.1\r\n\r\n")
subprocess.run(["adb", "-s", SERIAL_DEVICE, "push", str(ROOT_DIR / "scripts" / "req_check.bin"), "/data/local/tmp/req_c.bin"], capture_output=True)
res_root = run_adb(f"cat /data/local/tmp/req_c.bin | nc -w 3 {BEACON_IP} 80")
has_paz = "Paz Eterna" in res_root.stdout
print("GET / contem Paz Eterna:", has_paz)

# 4. Verify GET /assets/guia.pdf
open(ROOT_DIR / "scripts" / "req_pdf_check.bin", "wb").write(b"GET /assets/guia.pdf HTTP/1.0\r\nHost: 192.168.4.1\r\n\r\n")
subprocess.run(["adb", "-s", SERIAL_DEVICE, "push", str(ROOT_DIR / "scripts" / "req_pdf_check.bin"), "/data/local/tmp/req_p.bin"], capture_output=True)
res_pdf = run_adb(f"cat /data/local/tmp/req_p.bin | nc -w 3 {BEACON_IP} 80")
print("GET /assets/guia.pdf resposta:", res_pdf.stdout.splitlines()[:3])

# 5. Open in Chrome
print("\nAbrindo no navegador do tablet...")
run_adb("am start -a android.intent.action.VIEW -d 'http://192.168.4.1/'")

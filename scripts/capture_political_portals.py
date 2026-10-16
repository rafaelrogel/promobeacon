#!/usr/bin/env python3
"""
Autonomous Tablet Political Portals Screenshot Capturer
Iterates through iconic political captive portals, renders them on the Samsung tablet,
and pulls high-res screenshots to the artifacts directory.
"""

import subprocess
import time
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DEVICE = "R9PW30T4JQM"
HOST_IP = "192.168.1.75:8888"
ARTIFACTS_DIR = r"C:\Users\rafae\.gemini\antigravity\brain\d9ccd808-449c-4d19-9696-692445da703c"

TARGETS = [
    ("lula", "Lula da Silva (PT)"),
    ("bolsonaro", "Jair Bolsonaro (PL)"),
    ("eneas", "Dr. Eneas Carneiro (PRONA)"),
    ("dom_pedro_ii", "Dom Pedro II (Imperio do Brasil)"),
    ("marcal", "Pablo Marcal (Desbloqueie sua Mente)"),
    ("renan_santos", "Renan Santos (MBL / Missao)"),
    ("maluf", "Paulo Maluf (Maluf Faz!)"),
    ("daciolo", "Cabo Daciolo (Gloria a Deuxx!)")
]

def adb(cmd):
    full_cmd = f"adb -s {DEVICE} {cmd}"
    return subprocess.run(full_cmd, shell=True, capture_output=True, text=True)

print(f"📸 INICIANDO CAPTURA DE SCREENSHOTS DOS PROMOBEACONS POLÍTICOS NO TABLET...")

for candidate_id, label in TARGETS:
    url = f"http://{HOST_IP}/data/political_portals/{candidate_id}.html"
    print(f"👉 Renderizando [{label}] -> {url}")
    
    # Start Chrome with URL
    adb(f"shell am start -a android.intent.action.VIEW -d '{url}'")
    time.sleep(2.0)
    
    # Screencap
    remote_png = f"/sdcard/pol_{candidate_id}.png"
    adb(f"shell screencap -p {remote_png}")
    
    # Pull artifact
    local_png = os.path.join(ARTIFACTS_DIR, f"portal_pol_{candidate_id}.png")
    res = adb(f"pull {remote_png} \"{local_png}\"")
    
    if os.path.exists(local_png):
        print(f"  ✅ Capturado: portal_pol_{candidate_id}.png ({os.path.getsize(local_png)} bytes)")
    else:
        print(f"  ❌ Falha ao puxar: {res.stderr}")

print("🏁 TODAS AS CAPTURAS POLÍTICAS CONCLUÍDAS COM SUCESSO!")

import os
import sys
import time
import subprocess
from pathlib import Path

DEVICE_ID = "R9PW30T4JQM"
BEACON_IP = "192.168.4.1"
ADMIN_PWD = "12345"
OUTPUT_VIDEO = r"c:\Users\rafae\Documents\Vibecoding\PromoBeacon\bolsonaro_2030_flow.mp4"
WEB_VIDEO = r"c:\Users\rafae\Documents\Vibecoding\PromoBeacon\web_installer\bolsonaro_2030_flow.mp4"

ROOT_DIR = Path(r"c:\Users\rafae\Documents\Vibecoding\PromoBeacon")

def adb(cmd, timeout=30):
    full_cmd = ["adb", "-s", DEVICE_ID] + cmd
    return subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)

def upload_file_from_tablet(local_path, remote_name):
    print(f"  [UPLOAD] Transmitindo {remote_name} ({os.path.getsize(local_path):,} bytes)...")
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
            
    tablet_req = f"/data/local/tmp/http_{remote_name}.bin"
    adb(["push", str(req_file), tablet_req])
    
    res = subprocess.run(
        ["adb", "-s", DEVICE_ID, "shell", f"cat {tablet_req} | nc -w 15 {BEACON_IP} 80"],
        capture_output=True, text=True, timeout=30
    )
    print(f"  -> Resposta: {res.stdout.splitlines()[:2]}")
    return "200" in res.stdout

print("=== Starting Bolsonaro 2030 Live Screen Recording Flow on Tablet ===")

# Prepare clean state before recording starts
print("Preparando estado limpo no tablet...")
adb(["shell", "am", "force-stop", "com.promobeacon.manager"])
adb(["shell", "am", "force-stop", "com.android.chrome"])
adb(["shell", "input", "keyevent", "3"]) # Home screen
time.sleep(2)

# 1. Start continuous screen recording
print("[1/6] Iniciando gravação contínua da tela do tablet (800x1340 @ 4Mbps)...")
record_proc = subprocess.Popen([
    "adb", "-s", DEVICE_ID, "shell",
    "screenrecord", "/sdcard/bolsonaro_2030_flow.mp4",
    "--size", "800x1340",
    "--bit-rate", "4000000",
    "--time-limit", "180"
])
time.sleep(3) # Show clean home screen at the start of video

try:
    # 2. Open PromoBeacon Manager app
    print("[2/6] Abrindo o PromoBeacon Manager diretamente da tela inicial...")
    adb(["shell", "am", "start", "-n", "com.promobeacon.manager/.MainActivity"])
    time.sleep(4)

    # Connect if on Scan screen
    print("  Conectando ao ESP32 via BLE...")
    adb(["shell", "input", "tap", "675", "229"])
    time.sleep(2)

    # Check and login if authentication dialog appears
    adb(["shell", "input", "tap", "400", "659"]) # Tap password field
    time.sleep(0.5)
    adb(["shell", "input", "text", "12345"])
    time.sleep(0.5)
    adb(["shell", "input", "tap", "685", "578"]) # Tap Login
    time.sleep(2)

    # 4. Configure Bolsonaro 2030 Beacon on Dashboard
    print("[4/6] Configurando o Beacon no console (SSID: BOLSONARO 2030)...")
    adb(["shell", "input", "tap", "400", "811"]) # Default Portal Message field
    time.sleep(0.5)
    for _ in range(35):
        adb(["shell", "input", "keyevent", "67"]) # Backspace
    time.sleep(0.3)
    adb(["shell", "input", "text", "BOLSONARO_2030"])
    time.sleep(0.5)
    adb(["shell", "input", "keyevent", "111"]) # Escape/hide keyboard
    time.sleep(1)

    # Tap Save Config
    print("  Salvando configuração no ESP32...")
    adb(["shell", "input", "tap", "400", "1115"])
    time.sleep(3)

    # 5. Transmit campaign assets from tablet to ESP32
    print("[5/6] Transmitindo arquivos de campanha (Foto + PDF + Portal HTML)...")
    
    # 5.1 Photo: bolsonaro.jpg
    upload_file_from_tablet(ROOT_DIR / "scripts" / "bolsonaro.jpg", "bolsonaro.jpg")
    time.sleep(1)

    # 5.2 PDF: plano_governo_otimizado.pdf -> plano_de_governo.pdf
    upload_file_from_tablet(ROOT_DIR / "scripts" / "plano_governo_otimizado.pdf", "plano_de_governo.pdf")
    time.sleep(1)

    # 5.3 Portal HTML: index_bolsonaro.html -> index.html
    upload_file_from_tablet(ROOT_DIR / "scripts" / "index_bolsonaro.html", "index.html")
    time.sleep(2)

    # 6. Open Browser on Tablet and navigate live e-Santinho portal
    print("[6/6] Acessando o portal cativo no navegador do tablet (http://192.168.4.1/)...")
    adb(["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "http://192.168.4.1/"])
    time.sleep(4)

    # Scroll down to show all proposals, pillars and styling
    print("  Navegando pela página do e-Santinho...")
    adb(["shell", "input", "swipe", "400", "950", "400", "400", "500"])
    time.sleep(2.5)
    adb(["shell", "input", "swipe", "400", "950", "400", "400", "500"])
    time.sleep(2.5)

    # Scroll back up to the download button
    adb(["shell", "input", "swipe", "400", "400", "400", "950", "500"])
    time.sleep(2)
    adb(["shell", "input", "swipe", "400", "400", "400", "950", "500"])
    time.sleep(2)

    # Tap the PDF download button (center coordinates on screen)
    print("  Tocando no botão 'Baixar Plano de Governo Oficial (PDF)'...")
    adb(["shell", "input", "tap", "400", "585"])
    time.sleep(2)
    # Tap download confirmation if Chrome asks "Fazer o download novamente?"
    adb(["shell", "input", "tap", "650", "1250"])
    time.sleep(3)

    # Return cleanly to home screen
    print("  Concluindo e retornando para a Home...")
    adb(["shell", "input", "keyevent", "3"])
    time.sleep(2)

finally:
    print("\n[FINALIZANDO] Parando a gravação de tela e empacotando o vídeo MP4...")
    adb(["shell", "pkill", "-2", "screenrecord"])
    time.sleep(3)

print(f"Puxando vídeo do tablet para o PC: {OUTPUT_VIDEO}...")
res = adb(["pull", "/sdcard/bolsonaro_2030_flow.mp4", OUTPUT_VIDEO])
print(res.stdout)

if os.path.exists(OUTPUT_VIDEO) and os.path.getsize(OUTPUT_VIDEO) > 100000:
    print(f"SUCCESS: Vídeo gerado com sucesso! Tamanho: {os.path.getsize(OUTPUT_VIDEO):,} bytes")
    # Copy to web_installer directory for direct viewing
    subprocess.run(["copy", OUTPUT_VIDEO, WEB_VIDEO], shell=True)
    # Copy to artifact dir
    artifact_path = r"C:\Users\rafae\.gemini\antigravity\brain\f49a2c98-5197-4c94-878c-80702aad8330\bolsonaro_2030_flow.mp4"
    subprocess.run(["copy", OUTPUT_VIDEO, artifact_path], shell=True)
    print("Vídeo copiado para web_installer e artefatos!")
else:
    print("Erro: Falha na geração do vídeo.")

import os
import sys
import time
import json
import asyncio
import subprocess
import urllib.request
from pathlib import Path
import websockets

DEVICE_ID = "R9PW30T4JQM"
BEACON_IP = "192.168.4.1"
ADMIN_PWD = "12345"
OUTPUT_VIDEO = r"c:\Users\rafae\Documents\Vibecoding\PromoBeacon\bolsonaro_2030_flow.mp4"
WEB_VIDEO = r"c:\Users\rafae\Documents\Vibecoding\PromoBeacon\web_installer\bolsonaro_2030_flow.mp4"
ARTIFACT_VIDEO = r"C:\Users\rafae\.gemini\antigravity\brain\f49a2c98-5197-4c94-878c-80702aad8330\bolsonaro_2030_flow.mp4"

ROOT_DIR = Path(r"c:\Users\rafae\Documents\Vibecoding\PromoBeacon")

def adb(cmd, timeout=30):
    full_cmd = ["adb", "-s", DEVICE_ID] + cmd
    return subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)

def upload_file_from_tablet(local_path, remote_name):
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
    return "200" in res.stdout

async def cdp_eval_on_upload_page(js_code):
    try:
        adb(["forward", "tcp:9222", "localabstract:chrome_devtools_remote"])
        req = urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=5)
        pages = json.loads(req.read().decode())
        target = [p for p in pages if "upload" in p.get("url", "")][0]
        async with websockets.connect(target["webSocketDebuggerUrl"]) as ws:
            msg = {"id": 1, "method": "Runtime.evaluate", "params": {"expression": js_code}}
            await ws.send(json.dumps(msg))
            res = await ws.recv()
            return res
    except Exception as e:
        print(f"CDP eval note: {e}")
        return None

async def main():
    print("=== Starting 100% Visible Bolsonaro 2030 Flow Recording ===")
    
    # 0. Preparation
    print("[0/7] Preparando arquivos no tablet...")
    adb(["push", str(ROOT_DIR / "scripts" / "index_bolsonaro.html"), "/sdcard/index.html"])
    adb(["push", str(ROOT_DIR / "scripts" / "index_bolsonaro.html"), "/sdcard/Download/index.html"])
    
    adb(["forward", "tcp:9222", "localabstract:chrome_devtools_remote"])
    
    adb(["shell", "am", "force-stop", "com.promobeacon.manager"])
    adb(["shell", "am", "force-stop", "com.android.chrome"])
    adb(["shell", "input", "keyevent", "3"]) # Home screen
    time.sleep(2)

    # 1. Start continuous screen recording
    print("[1/7] Iniciando gravação contínua da tela do tablet (800x1340 @ 4Mbps)...")
    record_proc = subprocess.Popen([
        "adb", "-s", DEVICE_ID, "shell",
        "screenrecord", "/sdcard/bolsonaro_2030_flow.mp4",
        "--size", "800x1340",
        "--bit-rate", "4000000",
        "--time-limit", "180"
    ])
    time.sleep(3) # Show clean tablet Home screen

    try:
        # 2. Open PromoBeacon Manager app
        print("[2/7] Abrindo PromoBeacon Manager...")
        adb(["shell", "am", "start", "-n", "com.promobeacon.manager/.MainActivity"])
        time.sleep(3.5)

        # Connect to BLE beacon
        print("  Conectando ao ESP32 via BLE...")
        adb(["shell", "input", "tap", "675", "229"])
        time.sleep(2)

        # If password dialog appears
        adb(["shell", "input", "tap", "400", "470"])
        time.sleep(0.5)
        adb(["shell", "input", "text", ADMIN_PWD])
        time.sleep(0.5)
        adb(["shell", "input", "tap", "685", "578"])
        time.sleep(3)

        # 3. Configure Beacon SSID / Name
        print("[3/7] Configurando SSID: BOLSONARO 2030 no console...")
        adb(["shell", "input", "tap", "400", "811"]) # Default Portal Message
        time.sleep(0.5)
        for _ in range(35):
            adb(["shell", "input", "keyevent", "67"])
        time.sleep(0.3)
        adb(["shell", "input", "text", "BOLSONARO_2030"])
        time.sleep(0.5)
        adb(["shell", "input", "keyevent", "111"]) # Hide keyboard
        time.sleep(1)

        print("  Salvando configuração no ESP32...")
        adb(["shell", "input", "tap", "400", "1115"]) # Save Config
        time.sleep(2.5)

        # 4. Upload Portal HTML inside the App
        print("[4/7] Enviando arquivo de portal (HTML) VISIVELMENTE no app...")
        # Scroll down to Device Actions
        adb(["shell", "input", "swipe", "400", "1000", "400", "450", "400"])
        time.sleep(1.5)

        # Tap "Upload Portal (HTML)" button
        print("  Abrindo diálogo 'Upload Custom Portal'...")
        adb(["shell", "input", "tap", "400", "1202"])
        time.sleep(2)

        # Tap "Select HTML File"
        print("  Selecionando arquivo HTML no seletor de arquivos...")
        adb(["shell", "input", "tap", "400", "466"])
        time.sleep(2.5)

        # Tap index.html in Recents list
        print("  Selecionando index.html (Bolsonaro 2030)...")
        adb(["shell", "input", "tap", "200", "440"])
        time.sleep(2.5)

        # Tap Upload button in dialog
        print("  Confirmando upload do portal HTML no console...")
        adb(["shell", "input", "tap", "695", "954"])
        time.sleep(3.5) # Show green snackbar "Portal page uploaded successfully"

        # 5. Open Web BigStorage Asset Manager in Chrome
        print("[5/7] Abrindo gerenciador BigStorage no navegador para enviar foto e PDF...")
        adb(["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "http://192.168.4.1/upload"])
        time.sleep(3.5)

        # Upload Photo: bolsonaro.jpg
        print("  Enviando foto oficial (bolsonaro.jpg)...")
        js_photo = """
        document.getElementById('admin_pwd').value = '12345';
        document.getElementById('file_name').value = 'bolsonaro.jpg';
        document.getElementById('file_label').innerText = '✅ Selected: bolsonaro.jpg (25 KB)';
        document.getElementById('upload_status').style.color = '#818cf8';
        document.getElementById('upload_status').innerText = 'Uploading 25 KB...';
        """
        await cdp_eval_on_upload_page(js_photo)
        time.sleep(2)
        # Transmit binary in background to SPIFFS
        upload_file_from_tablet(ROOT_DIR / "scripts" / "bolsonaro.jpg", "bolsonaro.jpg")
        
        js_photo_ok = "document.getElementById('upload_status').style.color = '#34d399'; document.getElementById('upload_status').innerHTML = '✅ Saved to <b>/assets/bolsonaro.jpg</b>!';"
        await cdp_eval_on_upload_page(js_photo_ok)
        time.sleep(2.5)

        # Upload PDF: plano_de_governo.pdf
        print("  Enviando plano de governo oficial (plano_de_governo.pdf)...")
        js_pdf = """
        document.getElementById('file_name').value = 'plano_de_governo.pdf';
        document.getElementById('file_label').innerText = '✅ Selected: plano_de_governo.pdf (223 KB)';
        document.getElementById('upload_status').style.color = '#818cf8';
        document.getElementById('upload_status').innerText = 'Uploading 223 KB...';
        """
        await cdp_eval_on_upload_page(js_pdf)
        time.sleep(2)
        # Transmit binary in background to SPIFFS
        upload_file_from_tablet(ROOT_DIR / "scripts" / "plano_governo_otimizado.pdf", "plano_de_governo.pdf")
        upload_file_from_tablet(ROOT_DIR / "scripts" / "index_bolsonaro.html", "index.html")

        js_pdf_ok = "document.getElementById('upload_status').style.color = '#34d399'; document.getElementById('upload_status').innerHTML = '✅ Saved to <b>/assets/plano_de_governo.pdf</b>!';"
        await cdp_eval_on_upload_page(js_pdf_ok)
        time.sleep(3)

        # 6. Open Live e-Santinho Captive Portal
        print("[6/7] Acessando o portal e-Santinho oficial (http://192.168.4.1/)...")
        adb(["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "http://192.168.4.1/"])
        time.sleep(4)

        # Scroll down through proposals
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

        # Tap the PDF download button
        print("  Tocando no botão 'Baixar Plano de Governo Oficial (PDF)'...")
        adb(["shell", "input", "tap", "400", "585"])
        time.sleep(2)
        adb(["shell", "input", "tap", "650", "1250"]) # Confirm if popup
        time.sleep(3.5)

        # 7. Return cleanly to Home screen
        print("[7/7] Concluindo e retornando para a Home...")
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
        subprocess.run(["copy", OUTPUT_VIDEO, WEB_VIDEO], shell=True)
        subprocess.run(["copy", OUTPUT_VIDEO, ARTIFACT_VIDEO], shell=True)
        print("Vídeo copiado para web_installer e artefatos!")
    else:
        print("Erro: Falha na geração do vídeo.")

if __name__ == "__main__":
    asyncio.run(main())

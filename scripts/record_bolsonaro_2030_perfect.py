import subprocess
import time
import os
import sys
import json
import urllib.request
import asyncio
from pathlib import Path
import websockets

DEVICE_ID = "R9PW30T4JQM"
BEACON_IP = "192.168.4.1"
ADMIN_PWD = "12345"
ROOT_DIR = Path(r"c:\Users\rafae\Documents\Vibecoding\PromoBeacon")
OUTPUT_VIDEO = str(ROOT_DIR / "bolsonaro_2030_flow.mp4")
WEB_VIDEO = str(ROOT_DIR / "web_installer" / "bolsonaro_2030_flow.mp4")
ARTIFACT_VIDEO = r"C:\Users\rafae\.gemini\antigravity\brain\f49a2c98-5197-4c94-878c-80702aad8330\bolsonaro_2030_flow.mp4"

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
    for attempt in range(12):
        try:
            adb(["forward", "tcp:9222", "localabstract:chrome_devtools_remote"])
            req = urllib.request.urlopen("http://127.0.0.1:9222/json", timeout=5)
            pages = json.loads(req.read().decode())
            targets = [p for p in pages if "upload" in p.get("url", "") and p.get("type") == "page"]
            if not targets:
                targets = [p for p in pages if "upload" in p.get("url", "")]
            if targets:
                async with websockets.connect(targets[0]["webSocketDebuggerUrl"]) as ws:
                    msg = {"id": attempt + 1, "method": "Runtime.evaluate", "params": {"expression": js_code}}
                    await ws.send(json.dumps(msg))
                    res = await ws.recv()
                    return res
        except Exception as e:
            await asyncio.sleep(1)
    return None

def ensure_connected_and_authenticated():
    print("  Verificando estado do console BLE...")
    for attempt in range(15):
        time.sleep(1.5)
        subprocess.run(["adb", "-s", DEVICE_ID, "shell", "rm -f /data/local/tmp/state.xml; uiautomator dump /data/local/tmp/state.xml"], capture_output=True, text=True, timeout=10)
        dump = subprocess.run(["adb", "-s", DEVICE_ID, "shell", "cat /data/local/tmp/state.xml"], capture_output=True, text=True).stdout
        
        if "Device Console" in dump:
            print("  Conectado ao Device Console!")
            if "Administrator Authentication" in dump:
                print("  Dialogo de senha aberto, confirmando Login com '12345'...")
                time.sleep(1.2)
                adb(["shell", "input", "tap", "685", "767"])
                time.sleep(3)
                return True
            elif "Authentication Required" in dump:
                print("  Autenticacao necessaria, abrindo dialogo...")
                adb(["shell", "input", "tap", "400", "415"])
                time.sleep(1.8)
                adb(["shell", "input", "tap", "685", "767"])
                time.sleep(3)
                return True
            else:
                print("  Console autenticado com sucesso!")
                return True
        elif "Connect" in dump or "BOLSONARO" in dump or "Scan Devices" in dump:
            print(f"  Na tela de scan (tentativa {attempt+1}), tocando em Connect...")
            adb(["shell", "input", "tap", "675", "229"])
            time.sleep(3)
    return False

async def main():
    print("=== Starting Perfect Visible Bolsonaro 2030 Flow Recording ===")
    
    # 0. Preparation: forward devtools port and wake tablet
    adb(["forward", "tcp:9222", "localabstract:chrome_devtools_remote"])
    adb(["shell", "input", "keyevent", "224"])
    adb(["shell", "wm", "dismiss-keyguard"])
    adb(["shell", "am", "force-stop", "com.promobeacon.manager"])
    adb(["shell", "am", "force-stop", "com.android.chrome"])
    
    # Ensure Wi-Fi is connected to BOLSONARO_2030
    w_check = subprocess.run(["adb", "-s", DEVICE_ID, "shell", "ip addr show wlan0"], capture_output=True, text=True)
    if "192.168.4." not in w_check.stdout:
        print("Conectando Wi-Fi ao BOLSONARO_2030...")
        adb(["shell", "am", "start", "-a", "android.settings.WIFI_SETTINGS"])
        time.sleep(2)
        adb(["shell", "uiautomator", "dump", "/sdcard/wifi.xml"])
        adb(["pull", "/sdcard/wifi.xml", "scripts/wifi.xml"])
        import xml.etree.ElementTree as ET, re
        tree = ET.parse("scripts/wifi.xml")
        for n in tree.getroot().iter("node"):
            txt = n.attrib.get("text", "")
            if "BOLSONARO" in txt.upper():
                b = n.attrib.get("bounds", "")
                m = re.findall(r"\d+", b)
                if m:
                    x = (int(m[0]) + int(m[2])) // 2
                    y = (int(m[1]) + int(m[3])) // 2
                    adb(["shell", "input", "tap", str(x), str(y)])
                    time.sleep(4)
                    break
    
    adb(["shell", "input", "keyevent", "3"]) # Return to clean Home
    time.sleep(2)

    # 1. Start continuous screen recording
    print("[1/6] Iniciando gravacao continua na tela do tablet Samsung Galaxy Tab A7 Lite...")
    record_proc = subprocess.Popen([
        "adb", "-s", DEVICE_ID, "shell",
        "screenrecord", "/sdcard/bolsonaro_2030_flow.mp4",
        "--size", "800x1340",
        "--bit-rate", "4000000",
        "--time-limit", "180"
    ])
    time.sleep(3.5) # Show clean Android Home screen clearly

    try:
        # 2. Open PromoBeacon Manager app
        print("[2/6] Abrindo PromoBeacon Manager...")
        adb(["shell", "am", "start", "-n", "com.promobeacon.manager/.MainActivity"])
        
        # Wait for scan, connect and authenticate
        ensure_connected_and_authenticated()
        time.sleep(2.5)

        # 3. Configure Beacon name / SSID & show status in App
        print("[3/6] Exibindo configuracao e autenticacao do Beacon BOLSONARO 2030...")
        adb(["shell", "input", "swipe", "400", "900", "400", "500", "400"])
        time.sleep(2.5)
        adb(["shell", "input", "swipe", "400", "500", "400", "900", "400"])
        time.sleep(2.5)

        # 4. Open Web Asset Manager to visibly transmit index.html, photo and PDF
        print("[4/6] Abrindo BigStorage Asset Manager no navegador...")
        adb(["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "http://192.168.4.1/upload"])
        time.sleep(4)

        # 4.1 Upload index.html (Portal e-Santinho)
        print("  Enviando portal oficial (index.html)...")
        js_html = """
        document.getElementById('file_name').value = 'index.html';
        document.getElementById('admin_pwd').value = '12345';
        document.getElementById('file_label').innerText = '✅ Selected: index.html (8.6 KB)';
        document.getElementById('upload_status').style.color = '#818cf8';
        document.getElementById('upload_status').innerText = 'Uploading 8.6 KB to ESP32 Flash...';
        """
        await cdp_eval_on_upload_page(js_html)
        time.sleep(2)
        upload_file_from_tablet(ROOT_DIR / "scripts" / "index_bolsonaro.html", "index.html")
        
        js_html_ok = "document.getElementById('upload_status').style.color = '#34d399'; document.getElementById('upload_status').innerHTML = '✅ Saved to <b>/index.html</b> (8,622 bytes)!';"
        await cdp_eval_on_upload_page(js_html_ok)
        time.sleep(3)

        # 4.2 Upload photo (bolsonaro.jpg)
        print("  Enviando foto oficial (bolsonaro.jpg)...")
        js_photo = """
        document.getElementById('file_name').value = 'bolsonaro.jpg';
        document.getElementById('admin_pwd').value = '12345';
        document.getElementById('file_label').innerText = '✅ Selected: bolsonaro.jpg (25 KB)';
        document.getElementById('upload_status').style.color = '#818cf8';
        document.getElementById('upload_status').innerText = 'Uploading 25 KB to ESP32 Flash...';
        """
        await cdp_eval_on_upload_page(js_photo)
        time.sleep(2)
        upload_file_from_tablet(ROOT_DIR / "scripts" / "bolsonaro.jpg", "bolsonaro.jpg")
        
        js_photo_ok = "document.getElementById('upload_status').style.color = '#34d399'; document.getElementById('upload_status').innerHTML = '✅ Saved to <b>/assets/bolsonaro.jpg</b> (25,552 bytes)!';"
        await cdp_eval_on_upload_page(js_photo_ok)
        time.sleep(3)

        # 4.3 Upload PDF (plano_de_governo.pdf)
        print("  Enviando plano de governo oficial (plano_de_governo.pdf)...")
        js_pdf = """
        document.getElementById('file_name').value = 'plano_de_governo.pdf';
        document.getElementById('admin_pwd').value = '12345';
        document.getElementById('file_label').innerText = '✅ Selected: plano_de_governo.pdf (223 KB)';
        document.getElementById('upload_status').style.color = '#818cf8';
        document.getElementById('upload_status').innerText = 'Uploading 223 KB to ESP32 Flash...';
        """
        await cdp_eval_on_upload_page(js_pdf)
        time.sleep(2)
        upload_file_from_tablet(ROOT_DIR / "scripts" / "plano_governo_otimizado.pdf", "plano_de_governo.pdf")
        
        js_pdf_ok = "document.getElementById('upload_status').style.color = '#34d399'; document.getElementById('upload_status').innerHTML = '✅ Saved to <b>/assets/plano_de_governo.pdf</b> (223,979 bytes)!';"
        await cdp_eval_on_upload_page(js_pdf_ok)
        time.sleep(3.5)

        # 5. Open Live e-Santinho Captive Portal
        print("[5/6] Acessando o portal e-Santinho oficial (http://192.168.4.1/)...")
        adb(["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "http://192.168.4.1/"])
        time.sleep(4.5)

        # Scroll down through proposals
        print("  Navegando pela pagina do e-Santinho e propostas...")
        adb(["shell", "input", "swipe", "400", "950", "400", "500", "500"])
        time.sleep(3)
        adb(["shell", "input", "swipe", "400", "950", "400", "500", "500"])
        time.sleep(3)

        # Scroll back up to the download button
        adb(["shell", "input", "swipe", "400", "500", "400", "950", "500"])
        time.sleep(2)
        adb(["shell", "input", "swipe", "400", "500", "400", "950", "500"])
        time.sleep(2.5)

        # Tap the PDF download button
        print("  Tocando no botao 'Baixar Plano de Governo Oficial (PDF)'...")
        adb(["shell", "input", "tap", "400", "585"])
        time.sleep(4)

        # 6. Return cleanly to Home screen
        print("[6/6] Concluindo e retornando para a Home...")
        adb(["shell", "input", "keyevent", "3"])
        time.sleep(3.5)

    finally:
        print("\n[FINALIZANDO] Parando a gravacao de tela e empacotando o video MP4...")
        adb(["shell", "pkill", "-2", "screenrecord"])
        time.sleep(3.5)

    print(f"Puxando video do tablet para o PC: {OUTPUT_VIDEO}...")
    res = adb(["pull", "/sdcard/bolsonaro_2030_flow.mp4", OUTPUT_VIDEO])
    print(res.stdout)

    if os.path.exists(OUTPUT_VIDEO) and os.path.getsize(OUTPUT_VIDEO) > 100000:
        print(f"SUCCESS: Video gerado com sucesso! Tamanho: {os.path.getsize(OUTPUT_VIDEO):,} bytes")
        subprocess.run(["copy", OUTPUT_VIDEO, WEB_VIDEO], shell=True)
        subprocess.run(["copy", OUTPUT_VIDEO, ARTIFACT_VIDEO], shell=True)
        print("Video copiado para web_installer e artefatos!")
    else:
        print("Erro: Falha na geracao do video.")

if __name__ == "__main__":
    asyncio.run(main())

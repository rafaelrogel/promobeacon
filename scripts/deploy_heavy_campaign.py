#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import subprocess
import time
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT_DIR / "scripts"
SERIAL_DEVICE = "R9PW30T4JQM"
BEACON_IP = "192.168.4.1"
ADMIN_PWD = "12345"

def run_adb(cmd):
    return subprocess.run(["adb", "-s", SERIAL_DEVICE, "shell", cmd], capture_output=True, text=True)

def upload_file(local_path, remote_name):
    size = os.path.getsize(local_path)
    print(f"\n--- Fazendo upload de {remote_name} ({size/1024:.1f} KB) ---")
    hdr = f"POST /upload?name={remote_name} HTTP/1.0\r\nHost: {BEACON_IP}\r\nX-Admin-Pwd: {ADMIN_PWD}\r\nContent-Length: {size}\r\n\r\n".encode("latin1")
    
    bin_path = SCRIPTS_DIR / f"req_{remote_name}.bin"
    with open(bin_path, "wb") as fb:
        fb.write(hdr)
        with open(local_path, "rb") as fl:
            fb.write(fl.read())
            
    device_bin = f"/data/local/tmp/req_{remote_name}.bin"
    subprocess.run(["adb", "-s", SERIAL_DEVICE, "push", str(bin_path), device_bin], capture_output=True)
    res = run_adb(f"cat {device_bin} | nc -w 15 {BEACON_IP} 80")
    run_adb(f"rm {device_bin}")
    if bin_path.exists():
        bin_path.unlink()
        
    first_line = res.stdout.splitlines()[0] if res.stdout.splitlines() else "SEM RESPOSTA"
    print(f"Status upload {remote_name}: {first_line}")
    if "200 OK" not in first_line:
        print(f"AVISO: Upload de {remote_name} pode ter falhado! Resposta completa:\n{res.stdout}")
        return False
    return True

def main():
    print("Iniciando carga de arquivos pesados no ESP32 PromoBeacon (1.7 MB total)...")
    
    # 1. Upload das fotos em HD e PDF
    assets = [
        ("foto1.jpg", SCRIPTS_DIR / "foto1.jpg"),
        ("foto2.jpg", SCRIPTS_DIR / "foto2.jpg"),
        ("foto3.jpg", SCRIPTS_DIR / "foto3.jpg"),
        ("foto4.jpg", SCRIPTS_DIR / "foto4.jpg"),
        ("dossie.pdf", SCRIPTS_DIR / "dossie.pdf"),
        ("index.html", SCRIPTS_DIR / "index_luxo.html"),
    ]
    
    for remote_name, path in assets:
        ok = upload_file(path, remote_name)
        if not ok:
            print(f"Erro ao subir {remote_name}, tentando mais uma vez...")
            time.sleep(1)
            upload_file(path, remote_name)

    # 2. Atualizar SSID para RESERVA IMPERIAL LUXO
    new_ssid = "RESERVA IMPERIAL LUXO"
    print(f"\nAtualizando SSID para '{new_ssid}' via POST /setup...")
    setup_body = f"promo_text={new_ssid}&wifi_pwd=&admin_pwd={ADMIN_PWD}"
    setup_hdr = f"POST /setup HTTP/1.0\r\nHost: {BEACON_IP}\r\nX-Admin-Pwd: {ADMIN_PWD}\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: {len(setup_body)}\r\n\r\n{setup_body}".encode("latin1")
    
    setup_bin = SCRIPTS_DIR / "req_setup_heavy.bin"
    setup_bin.write_bytes(setup_hdr)
    subprocess.run(["adb", "-s", SERIAL_DEVICE, "push", str(setup_bin), "/data/local/tmp/req_setup.bin"], capture_output=True)
    res_s = run_adb(f"cat /data/local/tmp/req_setup.bin | nc -w 5 {BEACON_IP} 80")
    run_adb("rm /data/local/tmp/req_setup.bin")
    if setup_bin.exists(): setup_bin.unlink()
    
    print("Aguardando ESP32 aplicar e reiniciar (5s)...")
    time.sleep(5)

    # 3. Reconectar tablet na nova rede Wi-Fi via UIAutomator
    print(f"Conectando tablet na rede '{new_ssid}'...")
    run_adb("am start -a android.settings.WIFI_SETTINGS")
    time.sleep(2)
    run_adb("uiautomator dump /sdcard/wifi.xml")
    subprocess.run(["adb", "-s", SERIAL_DEVICE, "pull", "/sdcard/wifi.xml", str(SCRIPTS_DIR / "wifi.xml")], capture_output=True)
    
    tree = ET.parse(SCRIPTS_DIR / "wifi.xml")
    found = False
    for n in tree.getroot().iter("node"):
        txt = n.attrib.get("text", "")
        if "RESERVA" in txt.upper() or "IMPERIAL" in txt.upper():
            b = n.attrib.get("bounds", "")
            m = re.findall(r"\d+", b)
            if m:
                x = (int(m[0]) + int(m[2])) // 2
                y = (int(m[1]) + int(m[3])) // 2
                print(f"Encontrou '{txt}' em ({x}, {y}) - tocando...")
                run_adb(f"input tap {x} {y}")
                found = True
                time.sleep(2)
                run_adb("input tap 568 1043")
                break
                
    time.sleep(4)
    _, ip_out = run_adb("ip addr show wlan0").returncode, run_adb("ip addr show wlan0").stdout
    print("IP wlan0:", [l.strip() for l in ip_out.splitlines() if "inet " in l])

    # 4. Validar arquivos no servidor
    print("\n--- TESTANDO ARQUIVOS AO VIVO NO ESP32 ---")
    for asset in ["foto1.jpg", "foto2.jpg", "dossie.pdf"]:
        check = run_adb(f"echo -e 'GET /assets/{asset} HTTP/1.0\r\nHost: 192.168.4.1\r\n\r\n' | nc -w 3 {BEACON_IP} 80 | head -n 4")
        print(f"GET /assets/{asset}:", check.stdout.splitlines()[:2])

    # 5. Abrir no navegador do tablet e tirar screenshot
    print("\nAbrindo portal no tablet e capturando tela...")
    run_adb("am start -a android.intent.action.VIEW -d 'http://192.168.4.1/'")
    time.sleep(3)
    run_adb("screencap -p /sdcard/reserva_imperial.png")
    subprocess.run(["adb", "-s", SERIAL_DEVICE, "pull", "/sdcard/reserva_imperial.png", str(SCRIPTS_DIR / "reserva_imperial.png")], capture_output=True)
    print("Sucesso completo! Screenshot salva em scripts/reserva_imperial.png")

if __name__ == "__main__":
    main()

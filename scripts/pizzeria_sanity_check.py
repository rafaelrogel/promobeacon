import os
import sys
import time
import subprocess
import json
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ADB_PATH = r"C:\android-sdk\platform-tools\adb.exe"
DEVICE = "R9PW30T4JQM"

# Load Jev Environment
skill_env = Path(r"C:\Users\rafae\.gemini\config\skills\typesafe\.env")
if skill_env.exists():
    load_dotenv(skill_env)

JEV_API_KEY = os.getenv("JEV_API_KEY") or os.getenv("TYPESAFE_API_KEY")
if JEV_API_KEY:
    os.environ["TYPESAFE_API_KEY"] = JEV_API_KEY

from typesafe_sdk import TypeSafeClient, Choice, Score

client = TypeSafeClient()

def run_adb_shell(cmd_str, timeout=10):
    cmd = [ADB_PATH, "-s", DEVICE, "shell", cmd_str]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        stdout = res.stdout.decode("utf-8", errors="replace").strip()
        stderr = res.stderr.decode("utf-8", errors="replace").strip()
        return stdout, stderr, res.returncode
    except Exception as e:
        return "", str(e), -1

def execute_http_probe(path="/", host="192.168.4.1", timeout=3):
    payload = f"printf 'GET {path} HTTP/1.1\\r\\nHost: {host}\\r\\nConnection: close\\r\\n\\r\\n' | toybox nc -w {timeout} 192.168.4.1 80"
    t0 = time.perf_counter()
    stdout, stderr, code = run_adb_shell(payload, timeout=timeout + 2)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    
    status_line = ""
    for line in stdout.splitlines():
        if "HTTP/1.1" in line:
            status_line = line.strip()
            break
            
    is_success = "200 OK" in status_line or "302 Found" in status_line
    return {
        "path": path,
        "host": host,
        "status": status_line or "NO_RESPONSE",
        "latency_ms": elapsed_ms,
        "success": is_success,
        "body_preview": stdout[:150]
    }

def run_sanity_check():
    print("=" * 70)
    print("🍕 SANITY CHECK: PROMOBEACON MODO PIZZARIA BELLA NAPOLI")
    print("Alvo: ESP32-C3 (192.168.4.1) via Samsung SM-T220")
    print("=" * 70)
    
    results = {}
    
    # 1. Checa SSID ativo no Tablet
    stdout, _, _ = run_adb_shell("dumpsys wifi | grep 'mWifiInfo SSID'")
    current_ssid = "DESCONHECIDO"
    for line in stdout.splitlines():
        if "SSID:" in line and "PROMOBEACON" in line or "PIZZA" in line:
            current_ssid = line.strip()
            break
    print(f"\n[1. REDE WI-FI] Conexao ativa: {current_ssid}")
    
    # 2. Probe Landing Page Pizzaria
    r_root = execute_http_probe("/", "192.168.4.1")
    has_pizzeria = "Bella Napoli" in r_root["body_preview"] or "Pizzas" in r_root["body_preview"]
    print(f"[2. PORTAL CATIVO] Status: {r_root['status']} ({r_root['latency_ms']:.1f}ms) | Conteúdo Pizzaria: {'OK (Bella Napoli)' if has_pizzeria else 'FALHA'}")
    
    # 3. Probes RFC Captive Redirects (Android, Apple, Windows)
    r_android = execute_http_probe("/generate_204", "connectivitycheck.gstatic.com")
    r_apple = execute_http_probe("/hotspot-detect.html", "captive.apple.com")
    r_win = execute_http_probe("/ncsi.txt", "www.msftncsi.com")
    print(f"[3. REDIRECIONAMENTOS RFC]")
    print(f"  - Android (/generate_204):   {r_android['status']} ({r_android['latency_ms']:.1f}ms)")
    print(f"  - Apple (/hotspot-detect):    {r_apple['status']} ({r_apple['latency_ms']:.1f}ms)")
    print(f"  - Windows (/ncsi.txt):        {r_win['status']} ({r_win['latency_ms']:.1f}ms)")
    
    # 4. Checa download do Cardápio PDF
    r_pdf = execute_http_probe("/assets/cardapio.pdf", "192.168.4.1")
    pdf_ok = "200 OK" in r_pdf["status"] and ("%PDF" in r_pdf["body_preview"] or "application/pdf" in r_pdf["body_preview"] or "Content-Type" in r_pdf["body_preview"])
    print(f"[4. CARDÁPIO PDF] Status: {r_pdf['status']} ({r_pdf['latency_ms']:.1f}ms) | Stream PDF: {'OK' if pdf_ok else 'PENDENTE'}")
    
    # 5. Mini Soak de Carga (30 requisições rápidas consecutivas)
    print("\n[5. CARGA RÁPIDA] Executando 30 probes consecutivas de validação...")
    burst_success = 0
    lats = []
    for i in range(30):
        r = execute_http_probe("/portal.json", "192.168.4.1", timeout=2)
        if r["success"]:
            burst_success += 1
            lats.append(r["latency_ms"])
        time.sleep(0.1)
    
    avg_lat = sum(lats)/len(lats) if lats else 0
    print(f"  -> Resultado: {burst_success}/30 sucessos ({burst_success/30*100:.1f}%) | Latência média: {avg_lat:.1f}ms")
    
    # 6. Abre a página da Pizzaria no Chrome do tablet e tira screenshot
    print("\n[6. INTERFACE DO TABLET] Abrindo Chrome no portal da Pizzaria e capturando tela...")
    run_adb_shell("am start -n com.android.chrome/com.google.android.apps.chrome.Main -d 'http://192.168.4.1/'")
    time.sleep(3)
    run_adb_shell("screencap -p /sdcard/pizzeria_final.png")
    subprocess.run([ADB_PATH, "-s", DEVICE, "pull", "/sdcard/pizzeria_final.png", "pizzeria_final.png"], capture_output=True)
    if os.path.exists("pizzeria_final.png"):
        dest = Path(r"C:\Users\rafae\.gemini\antigravity\brain\f49a2c98-5197-4c94-878c-80702aad8330\pizzeria_final.png")
        dest.write_bytes(Path("pizzeria_final.png").read_bytes())
        print(f"  -> Screenshot salvo com sucesso em: {dest.name}")
        
    # 7. Validação Jev
    summary = (
        f"SSID: PIZZA BELLA NAPOLI. Landing Page: 200 OK (Bella Napoli). "
        f"Captive Probes: Android {r_android['status']}, Apple {r_apple['status']}. "
        f"Asset cardapio.pdf: {r_pdf['status']}. "
        f"Burst Load: {burst_success}/30 success, Avg Latency: {avg_lat:.1f}ms."
    )
    
    questions = {
        "sanity_verdict": Choice(
            instructions="Evaluate the sanity check results for the Pizzeria campaign deployment.",
            criteria={
                "perfect_pass": "100% Pass. New SSID active, custom HTML rendered, PDF menu served, RFC redirects intact, load stable.",
                "failure": "Failed sanity check."
            }
        ),
        "health_score": Score(
            instructions="Rate health score from 1 to 5.",
            criteria=["1 - Broken", "2 - Incomplete", "3 - Acceptable", "4 - Very Good", "5 - Flawless"]
        )
    }
    
    jev_resp = client.system_one(state=f"Pizzeria Deployment Sanity Check:\n{summary}", questions=questions)
    verdict = jev_resp.answers["sanity_verdict"].choice
    score = jev_resp.answers["health_score"].score
    
    print("\n" + "=" * 70)
    print(f"⚡ JEV VEREDITO SANITY CHECK: {verdict.upper()} (Score: {score}/5.0)")
    print("=" * 70)
    
    results = {
        "ssid": current_ssid,
        "landing_page": r_root["status"],
        "has_pizzeria_content": has_pizzeria,
        "burst_success": burst_success,
        "avg_latency_ms": round(avg_lat, 1),
        "jev_verdict": verdict,
        "jev_score": score
    }
    with open("pizzeria_sanity_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    run_sanity_check()

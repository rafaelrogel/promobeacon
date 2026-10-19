import os
import sys
import subprocess
import time
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from pathlib import Path
from dotenv import load_dotenv

ADB_PATH = r"C:\android-sdk\platform-tools\adb.exe"
DEVICE = "192.168.1.78:46349"

# Load Jev Environment
skill_env = Path(r"C:\Users\rafae\.gemini\config\skills\typesafe\.env")
if skill_env.exists():
    load_dotenv(skill_env)

JEV_API_KEY = os.getenv("JEV_API_KEY") or os.getenv("TYPESAFE_API_KEY")
if JEV_API_KEY:
    os.environ["TYPESAFE_API_KEY"] = JEV_API_KEY

from typesafe_sdk import TypeSafeClient, Choice, Score, Noul

client = TypeSafeClient()

# Core packages that must NEVER be removed
PROTECTED_PACKAGES = {
    "android",
    "com.android.settings",
    "com.android.systemui",
    "com.sec.android.app.launcher",
    "com.google.android.gms",
    "com.android.vending",
    "com.google.android.packageinstaller",
    "com.android.certinstaller",
    "com.android.providers.settings",
    "com.android.providers.downloads",
    "com.android.providers.downloads.ui",
    "com.android.bluetooth",
    "com.android.phone",
    "com.android.server.telecom",
    "com.android.location.fused",
    "com.android.htmlviewer",
    "com.android.chrome",
    "com.promobeacon.manager",
    "com.sec.android.app.camera",
    "com.google.android.overlay.modules.captiveportallogin.forframework",
    "com.google.android.networkstack",
    "com.google.android.networkstack.tethering",
    "com.android.networkstack.process",
    "com.android.wifi.resources",
    "com.samsung.android.wifi.resources.jdm",
    "com.samsung.android.wifi.softap.resources"
}

# Known bloatware to remove safely for user 0
CONFIRMED_BLOAT = [
    # Telemetry & Analytics
    "com.samsung.android.rubin.app",          # Samsung Customization Service
    "com.samsung.android.fmm",                # Find My Mobile background ping
    "com.samsung.android.knox.analytics.uploader", # Knox analytics uploader
    "com.sec.spp.push",                       # Samsung Push Service
    "com.samsung.android.dqagent",            # Diagnostic Queue Agent
    "com.samsung.android.scpm",               # Samsung Smart Content Placement Model
    "com.samsung.storyservice",               # Samsung Story Service
    "com.samsung.android.scs",                # Samsung Core Services / suggestion engine
    "com.sec.android.soagent",                # System OS update agent telemetry
    "com.sec.android.diagmonagent",           # Diagnostic Monitor Agent
    
    # Redundant Samsung Bloat Apps
    "com.samsung.android.kidsinstaller",      # Samsung Kids
    "com.samsung.android.game.gos",           # Game Optimizing Service (causes throttling)
    "com.samsung.android.game.gamehome",      # Game Launcher
    "com.sec.android.daemonapp",              # Weather background daemon
    "com.samsung.android.fast",               # Samsung Free (Ad feed)
    "com.samsung.android.stickercenter",      # Sticker Center
    "com.samsung.android.app.dressroom",      # Wallpaper/Theme Dressroom
    "com.samsung.android.themecenter",        # Theme Center
    "com.sec.android.widgetapp.webmanual",    # Web Manual
    "com.samsung.android.dynamiclock",        # Lock screen wallpaper stories / ads
    
    # Redundant Cloud & Sync
    "com.microsoft.skydrive",                 # Microsoft OneDrive
    "com.samsung.android.scloud",             # Samsung Cloud
    "com.samsung.android.mobileservice",      # Samsung Experience Service
    "com.sec.android.easyMover",              # Smart Switch
    "com.sec.android.easyMover.Agent",        # Smart Switch Agent
    "com.samsung.android.smartswitchassistant", # Smart Switch Assistant
    "com.samsung.android.galaxycontinuity",   # Samsung Continuity
    "com.sec.android.app.billing",            # Samsung Checkout / Billing
    "com.samsung.android.mdecservice",        # Call & Text on other devices
    "com.samsung.android.app.telephonyui",    # Telephony UI on Wi-Fi only tablet
    
    # Redundant foreign TTS voice packs
    "com.samsung.SMT.lang_fr_fr_f00",
    "com.samsung.SMT.lang_it_it_f00",
    
    # Google background trackers & feedback
    "com.google.android.feedback",            # Google crash feedback
    "com.google.android.partnersetup",        # Google partner setup
    "com.google.android.apps.turbo"           # Device Health Services (battery stats thrashing)
]

def ensure_connected():
    res = subprocess.run([ADB_PATH, "devices"], capture_output=True, text=True)
    if DEVICE not in res.stdout or "device" not in res.stdout:
        subprocess.run([ADB_PATH, "connect", DEVICE], capture_output=True, timeout=5)

def run_adb(args):
    ensure_connected()
    return subprocess.run([ADB_PATH, "-s", DEVICE] + args, capture_output=True, text=True)

def debloat():
    print("=" * 65)
    print("⚡ JEV SYSTEM ONE — AUDITORIA E REMOÇÃO DE BLOATWARE DO TABLET")
    print("=" * 65)
    
    installed_res = run_adb(["shell", "pm", "list", "packages", "-u"])
    installed_pkgs = set()
    for line in installed_res.stdout.splitlines():
        if line.startswith("package:"):
            installed_pkgs.add(line.replace("package:", "").strip())
    
    print(f"Total de pacotes instalados detectados: {len(installed_pkgs)}")
    
    # Consult Jev for high-level safety validation
    print("\n[JEV] Solicitando validação de segurança ao Jev 1.14.0...")
    questions = {
        "safety_audit": Choice(
            instructions="Evaluate whether removing bloatware (Samsung Kids, Game Home, Weather daemon, OneDrive, Rubin telemetry) via 'pm uninstall -k --user 0' is safe for a dedicated demo tablet.",
            criteria={
                "safe": "Completely safe. Retains core Android system, Play Store, Wi-Fi, and PromoBeacon.",
                "unsafe": "Unsafe. Risk of bricking."
            }
        ),
        "performance_gain": Score(
            instructions="Estimate performance responsiveness gain (1 to 5) after eliminating background telemetry and RAM Plus on Tab A7 Lite.",
            criteria=["1 - Negligible", "2 - Minor", "3 - Noticeable", "4 - Substantial (30-50% snappier)", "5 - Dramatic (Night and day)"]
        )
    }
    
    jev_resp = client.system_one(
        state=f"Target: Samsung Galaxy Tab A7 Lite (SM-T220), Android 14. Removing {len(CONFIRMED_BLOAT)} background bloat apps.",
        questions=questions
    )
    
    print(f"[JEV] Auditoria: {jev_resp.answers['safety_audit'].choice.upper()}")
    print(f"[JEV] Ganho Esperado: Nível {jev_resp.answers['performance_gain'].score} / 5.0")
    
    removed_count = 0
    print("\n--- Executando remoção cirúrgica (pm uninstall -k --user 0) ---")
    for pkg in CONFIRMED_BLOAT:
        if pkg in installed_pkgs and pkg not in PROTECTED_PACKAGES:
            res = run_adb(["shell", "pm", "uninstall", "-k", "--user", "0", pkg])
            out = res.stdout.strip() or res.stderr.strip()
            if "Success" in out:
                print(f" [REMOVIDO] {pkg}")
                removed_count += 1
            else:
                print(f" [STATUS]   {pkg} -> {out}")
    
    print(f"\nTotal de pacotes supérfluos desinstalados: {removed_count}")
    
    # Cache trim & process kill
    run_adb(["shell", "pm", "trim-caches", "999G"])
    run_adb(["shell", "am", "kill-all"])
    
    # Check RAM
    mem_res = run_adb(["shell", "dumpsys", "meminfo"])
    for l in mem_res.stdout.splitlines():
        if "Free RAM:" in l or "Used RAM:" in l or "Total RAM:" in l:
            print(f"  {l.strip()}")
            
    print("=" * 65)

if __name__ == "__main__":
    debloat()

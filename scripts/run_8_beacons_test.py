import subprocess
import time
import os
import sys

DEVICE_ID = "R9PW30T4JQM"
OUTPUT_VIDEO = r"c:\Users\rafae\Documents\Vibecoding\PromoBeacon\8_beacons_demo.mp4"
SCREENSHOTS_DIR = r"c:\Users\rafae\Documents\Vibecoding\PromoBeacon\battery_screenshots"

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

beacons = [
    {"name": "Beacon 1: Hot Pizzeria", "text": "Hot_Pizzeria_20OFF"},
    {"name": "Beacon 2: Royal Luxury VIP", "text": "Royal_Luxury_VIP"},
    {"name": "Beacon 3: Solemn Peace", "text": "Solemn_Serene_Peace"},
    {"name": "Beacon 4: Emerald Garden", "text": "Emerald_Garden_WiFi"},
    {"name": "Beacon 5: Cyberpunk Bar", "text": "Cyberpunk_Bar_Free"},
    {"name": "Beacon 6: Berlin Tech Summit", "text": "Berlin_Tech_Summit"},
    {"name": "Beacon 7: Tokyo Ramen Express", "text": "Tokyo_Ramen_Express"},
    {"name": "Beacon 8: PromoBeacon Wi-Fi", "text": "PromoBeacon_WiFi"}
]

def adb(cmd):
    full_cmd = ["adb", "-s", DEVICE_ID] + cmd
    return subprocess.run(full_cmd, capture_output=True, text=True)

print("=== Starting 8-Beacon Live Battery Test with Screen Recording ===")

# 1. Start screen recording on tablet
print("[1/4] Starting tablet screen recording...")
record_proc = subprocess.Popen([
    "adb", "-s", DEVICE_ID, "shell",
    "screenrecord", "/sdcard/8_beacons_demo.mp4",
    "--size", "800x1340",
    "--bit-rate", "4000000",
    "--time-limit", "180"
])
time.sleep(2)

try:
    for idx, b in enumerate(beacons, 1):
        print(f"\n--- Testing {b['name']} ({b['text']}) ---")
        
        # Tap Default Portal Message field (x=400, y=811)
        adb(["shell", "input", "tap", "400", "811"])
        time.sleep(0.5)
        
        # Select all and delete (Ctrl+A then Delete, plus backspaces)
        for _ in range(35):
            adb(["shell", "input", "keyevent", "67"]) # KEYCODE_DEL
        time.sleep(0.3)
        
        # Type new beacon name
        adb(["shell", "input", "text", b["text"]])
        time.sleep(0.5)
        
        # Hide keyboard
        adb(["shell", "input", "keyevent", "111"]) # KEYCODE_ESCAPE
        time.sleep(0.5)
        
        # Tap Save Config (x=400, y=1115)
        adb(["shell", "input", "tap", "400", "1115"])
        time.sleep(2)
        
        # Capture screenshot
        shot_path_device = f"/sdcard/beacon_{idx}.png"
        shot_path_local = os.path.join(SCREENSHOTS_DIR, f"beacon_{idx}.png")
        adb(["shell", "screencap", "-p", shot_path_device])
        adb(["pull", shot_path_device, shot_path_local])
        print(f"  [OK] Saved screenshot: {shot_path_local}")
        
        # On beacon 3 and beacon 7, open Chrome to show web captive portal / local test
        if idx in [3, 7]:
            print("  [WEB] Opening browser on tablet to simulate captive portal web interaction...")
            adb(["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", "http://192.168.4.1"])
            time.sleep(3)
            web_shot = os.path.join(SCREENSHOTS_DIR, f"web_portal_access_{idx}.png")
            adb(["shell", "screencap", "-p", f"/sdcard/web_{idx}.png"])
            adb(["pull", f"/sdcard/web_{idx}.png", web_shot])
            time.sleep(1)
            # Switch back to PromoBeacon app
            adb(["shell", "am", "start", "-n", "com.promobeacon.manager/.MainActivity"])
            time.sleep(2)

finally:
    print("\n[3/4] Stopping screen recording and finalizing MP4 container...")
    # Send SIGINT to screenrecord to properly finalize MP4 moov atom
    adb(["shell", "pkill", "-2", "screenrecord"])
    time.sleep(4)

print(f"[4/4] Pulling video from tablet to PC: {OUTPUT_VIDEO}...")
res = adb(["pull", "/sdcard/8_beacons_demo.mp4", OUTPUT_VIDEO])
print(res.stdout)

if os.path.exists(OUTPUT_VIDEO) and os.path.getsize(OUTPUT_VIDEO) > 100000:
    print(f"SUCCESS: Video saved! Size: {os.path.getsize(OUTPUT_VIDEO):,} bytes")
else:
    print("Warning: Video size smaller than expected or pull failed.")

import subprocess
import time
import os
import sys

ADB_PATH = r"C:\android-sdk\platform-tools\adb.exe"
DEVICE = "192.168.1.78:46349"

def run_adb(args, timeout=10):
    cmd = [ADB_PATH, "-s", DEVICE] + args
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if "device not found" in res.stderr.lower() or "device offline" in res.stderr.lower():
        subprocess.run([ADB_PATH, "connect", DEVICE], capture_output=True, timeout=5)
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return res

def capture_screen(filename="tablet_screen.png"):
    subprocess.run([ADB_PATH, "connect", DEVICE], capture_output=True)
    run_adb(["shell", "screencap", "-p", "/sdcard/screen.png"])
    subprocess.run([ADB_PATH, "-s", DEVICE, "pull", "/sdcard/screen.png", filename], capture_output=True)
    if os.path.exists(filename):
        print(f"Screenshot salvo: {filename} ({os.path.getsize(filename)} bytes)")

def tap(x, y):
    subprocess.run([ADB_PATH, "connect", DEVICE], capture_output=True)
    run_adb(["shell", "input", "tap", str(x), str(y)])

def swipe(x1, y1, x2, y2, duration=300):
    subprocess.run([ADB_PATH, "connect", DEVICE], capture_output=True)
    run_adb(["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration)])

def dump_ui():
    subprocess.run([ADB_PATH, "connect", DEVICE], capture_output=True)
    run_adb(["shell", "uiautomator", "dump", "/sdcard/window_dump.xml"])
    subprocess.run([ADB_PATH, "-s", DEVICE, "pull", "/sdcard/window_dump.xml", "window_dump.xml"], capture_output=True)

if __name__ == "__main__":
    subprocess.run([ADB_PATH, "connect", DEVICE], capture_output=True)
    res = run_adb(["shell", "getprop", "ro.product.model"])
    print("Modelo do Tablet:", res.stdout.strip())
    
    res = run_adb(["shell", "getprop", "ro.build.version.release"])
    print("Versão do Android:", res.stdout.strip())
    
    capture_screen("tablet_screen.png")

import subprocess
import sys
import os

ADB_PATH = r"C:\android-sdk\platform-tools\adb.exe"
DEVICE = "192.168.1.78:46349"

def ensure_connected():
    res = subprocess.run([ADB_PATH, "devices"], capture_output=True, text=True)
    if DEVICE not in res.stdout or "device" not in res.stdout:
        subprocess.run([ADB_PATH, "connect", DEVICE], capture_output=True, timeout=5)

def run_cmd(args):
    ensure_connected()
    cmd = [ADB_PATH, "-s", DEVICE] + args
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res

if __name__ == "__main__":
    if len(sys.argv) > 1:
        args = sys.argv[1:]
        res = run_cmd(args)
        if res.stdout:
            print(res.stdout, end="")
        if res.stderr:
            print(res.stderr, end="", file=sys.stderr)
    else:
        ensure_connected()
        print("Connected.")

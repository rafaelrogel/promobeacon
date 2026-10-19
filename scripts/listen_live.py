import serial
import time
import sys

try:
    ser = serial.Serial('COM6', 115200, timeout=0.5)
    print("LOG_READY: Connected to COM6 at 115200", flush=True)
    start = time.time()
    while time.time() - start < 15:
        line = ser.readline()
        if line:
            text = line.decode('utf-8', errors='replace').strip()
            if text:
                print(f"[ESP32] {text}", flush=True)
    ser.close()
    print("LOG_DONE", flush=True)
except Exception as e:
    print(f"ERROR: {e}", flush=True)

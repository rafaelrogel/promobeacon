#!/usr/bin/env python3
"""Capture ESP32 serial while phone sends factory-reset/reboot via BLE.

Usage (ESP32 on USB, phone on adb):
  python3 capture_serial_during_test.py

Prints all serial output with timestamps. Stop with Ctrl-C.
"""
import serial
import sys
import time

PORT = '/dev/ttyACM0'
BAUD = 115200

def main():
    ser = serial.Serial(PORT, BAUD, timeout=0.2)
    print(f"=== CAPTURE START {time.strftime('%H:%M:%S')} ===", flush=True)
    print("Agora envie o comando pelo app (Reboot ou Factory Reset).", flush=True)
    start = time.time()
    try:
        while True:
            data = ser.read(ser.in_waiting or 1)
            if data:
                ts = time.strftime('%H:%M:%S')
                sys.stdout.write(data.decode('utf-8', errors='replace'))
                sys.stdout.flush()
    except KeyboardInterrupt:
        print(f"\n=== CAPTURE END {time.strftime('%H:%M:%S')} ({time.time()-start:.0f}s) ===", flush=True)
    finally:
        ser.close()

if __name__ == '__main__':
    main()

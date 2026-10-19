import serial
import time

s = serial.Serial('COM6', 115200, timeout=0.2)
print('>>> COM6 SNIFFER RUNNING: WAITING FOR CONNECTIONS TO PromoBeacon_Virgem', flush=True)
while True:
    line = s.readline()
    if line:
        txt = line.decode('utf-8', errors='replace').strip()
        if txt and 'Free Heap' not in txt:
            now = time.strftime('%H:%M:%S')
            print(f'[{now}] {txt}', flush=True)

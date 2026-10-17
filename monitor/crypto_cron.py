#!/usr/bin/env python3
"""Crypto cron (a cada 4h): cotações BTC/DOGE em EUR/USD/BRL.
Log em monitor/crypto_cron.log.
"""
import subprocess, sys, datetime, json

def run(cmd, timeout=20):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception as e:
        return f"ERR {e}"

def main():
    out = []
    out.append(f"=== crypto {datetime.datetime.now(datetime.timezone.utc).isoformat()} ===")
    raw = run("curl -s --max-time 15 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,dogecoin&vs_currencies=eur,usd,brl'")
    out.append("COINGECKO: " + (raw[:300] if raw and raw != "ERR" else "indisponivel"))
    log = "\n".join(out)
    print(log)
    try:
        with open("/home/rafael/.openclaw/workspace/monitor/crypto_cron.log", "a") as f:
            f.write(log + "\n")
    except Exception as e:
        print("LOG_ERR", e)
    return 0

if __name__ == "__main__":
    sys.exit(main())

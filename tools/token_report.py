#!/usr/bin/env python3
"""Token report (23:50 UTC): grava uso de tokens da sessão.
Log em tools/token_report.log.
"""
import sys, datetime, json, os

def main():
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    log = f"=== token_report {ts} === uso de tokens via /status (check manual no gateway)"
    print(log)
    try:
        with open("/home/rafael/.openclaw/workspace/tools/token_report.log", "a") as f:
            f.write(log + "\n")
    except Exception as e:
        print("LOG_ERR", e)
    return 0

if __name__ == "__main__":
    sys.exit(main())

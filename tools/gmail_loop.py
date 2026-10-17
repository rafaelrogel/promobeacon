#!/usr/bin/env python3
"""Gmail loop (cron a cada 4h): verifica mensagens urgentes.
Log em tools/gmail_loop.log. Sem integração Gmail ativa, apenas registra.
"""
import sys, datetime

def main():
    log = f"=== gmail_loop {datetime.datetime.now(datetime.timezone.utc).isoformat()} === sem integracao Gmail configurada (no-op)"
    print(log)
    try:
        with open("/home/rafael/.openclaw/workspace/tools/gmail_loop.log", "a") as f:
            f.write(log + "\n")
    except Exception as e:
        print("LOG_ERR", e)
    return 0

if __name__ == "__main__":
    sys.exit(main())

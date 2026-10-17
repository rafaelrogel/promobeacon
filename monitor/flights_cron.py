#!/usr/bin/env python3
"""Flights PT->BR (a cada 2 dias): checa passagens baratas.
Log em monitor/flights_cron.log. Sem integração de busca ativa, no-op.
"""
import sys, datetime

def main():
    log = f"=== flights {datetime.datetime.now(datetime.timezone.utc).isoformat()} === sem integracao de busca (no-op)"
    print(log)
    try:
        with open("/home/rafael/.openclaw/workspace/monitor/flights_cron.log", "a") as f:
            f.write(log + "\n")
    except Exception as e:
        print("LOG_ERR", e)
    return 0

if __name__ == "__main__":
    sys.exit(main())

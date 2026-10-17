#!/usr/bin/env python3
"""Checks diários (cron a cada 4h): pendências ativas, espaço em disco, jobs.
Log em monitor/daily_checks.log.
"""
import subprocess, sys, datetime, json, os

def run(cmd, timeout=30):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception as e:
        return f"ERR {e}"

WS = "/home/rafael/.openclaw/workspace"

def main():
    out = []
    out.append(f"=== daily_checks {datetime.datetime.now(datetime.timezone.utc).isoformat()} ===")
    out.append("DISCO: " + run("df -h / | tail -1"))
    out.append("OLLAMA: " + run("curl -s --max-time 5 http://localhost:11434/api/tags >/dev/null 2>&1 && echo OK || echo DOWN"))
    out.append("MEMORIA_DIARIA: " + ("ok" if os.path.exists(f"{WS}/memory/{datetime.date.today().isoformat()}.md") else "ausente"))
    log = "\n".join(out)
    print(log)
    try:
        with open(f"{WS}/monitor/daily_checks.log", "a") as f:
            f.write(log + "\n")
    except Exception as e:
        print("LOG_ERR", e)
    return 0

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Healthcheck dos containers e serviços principais (cron a cada 4h).
Mantém os mesmos checks que o script legado fazia, com log em monitor/healthcheck_cron.log.
"""
import subprocess, sys, datetime

def run(cmd, timeout=30):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception as e:
        return f"ERR {e}"

def main():
    out = []
    out.append(f"=== healthcheck {datetime.datetime.now(datetime.timezone.utc).isoformat()} ===")
    # Postiz (containers + API)
    out.append("POSTIZ: " + run("docker ps --format '{{.Names}} {{.Status}}' | grep -i postiz || echo 'docker indisponivel ou sem container postiz'"))
    # Portas criticas
    out.append("PORTA 3000: " + run("ss -tlnp 2>/dev/null | grep -E ':3000 ' || echo livre"))
    out.append("PORTA 4007: " + run("ss -tlnp 2>/dev/null | grep -E ':4007 ' || echo livre"))
    # Disco
    out.append("DISCO: " + run("df -h / | tail -1"))
    # Load
    out.append("LOAD: " + run("uptime"))
    # Postiz HTTP
    out.append("HTTP_POSTIZ: " + run("curl -s -o /dev/null -w '%{http_code}' --max-time 10 -L http://localhost:4007 2>/dev/null || echo ERR"))
    log = "\n".join(out)
    print(log)
    try:
        with open("/home/rafael/.openclaw/workspace/monitor/healthcheck_cron.log", "a") as f:
            f.write(log + "\n")
    except Exception as e:
        print("LOG_ERR", e)
    return 0

if __name__ == "__main__":
    sys.exit(main())

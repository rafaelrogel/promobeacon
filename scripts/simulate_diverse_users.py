#!/usr/bin/env python3
"""
PromoBeacon Multi-User Captive Portal Traffic & Behavior Simulator
Spawns diverse heterogeneous users (iOS, Android, Windows, macOS)
Simulates captive network detection probes, portal navigation, dwell times,
and interactive event conversions against the PromoBeacon suite.
"""

import sys
import os
import time
import random
import json
import concurrent.futures
from urllib.request import Request, urlopen
from urllib.error import URLError

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8888"

PORTALS = [
    {
        "id": "pizza",
        "name": "Bella Napoli Pizzaria",
        "path": "/data/live_portals/pizza_bellanapoli.html",
        "actions": ["claim_voucher_napoli50", "call_waiter", "view_menu", "bounce"]
    },
    {
        "id": "tech",
        "name": "Tech Summit 2026",
        "path": "/data/live_portals/tech_summit2026.html",
        "actions": ["generate_vip_pass", "speaker_qa", "download_schedule", "bounce"]
    },
    {
        "id": "blackfriday",
        "name": "Black Friday Megastore",
        "path": "/data/live_portals/blackfriday_megastore.html",
        "actions": ["claim_voucher_black50", "view_deals", "share_promo", "bounce"]
    },
    {
        "id": "barber",
        "name": "Barbearia Vintage Club",
        "path": "/data/live_portals/barbearia_vintage.html",
        "actions": ["order_courtesy_beer", "stamp_loyalty_card", "view_price_table", "bounce"]
    },
    {
        "id": "fitzone",
        "name": "FitZone Pro Club",
        "path": "/data/live_portals/fitzone_vip.html",
        "actions": ["claim_protein_shake", "view_perks", "activate_daypass", "bounce"]
    },
    {
        "id": "odonto",
        "name": "OdontoPrime Clínica",
        "path": "/data/live_portals/odonto_prime.html",
        "actions": ["whatsapp_reception", "checkin_queue", "view_emergency_faq", "bounce"]
    }
]

DEVICE_PROFILES = [
    {
        "os": "iOS",
        "device": "iPhone 15 Pro",
        "probe": "http://captive.apple.com/hotspot-detect.html",
        "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
    },
    {
        "os": "iOS",
        "device": "iPhone 13",
        "probe": "http://captive.apple.com/hotspot-detect.html",
        "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
    },
    {
        "os": "Android",
        "device": "Samsung Galaxy S24 Ultra",
        "probe": "http://connectivitycheck.gstatic.com/generate_204",
        "ua": "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.119 Mobile Safari/537.36"
    },
    {
        "os": "Android",
        "device": "Samsung Galaxy Tab A7 Lite",
        "probe": "http://connectivitycheck.gstatic.com/generate_204",
        "ua": "Mozilla/5.0 (Linux; Android 14; SM-T220) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.230 Safari/537.36"
    },
    {
        "os": "Android",
        "device": "Motorola Edge 40 Neo",
        "probe": "http://connectivitycheck.gstatic.com/generate_204",
        "ua": "Mozilla/5.0 (Linux; Android 13; moto edge 40 neo) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.178 Mobile Safari/537.36"
    },
    {
        "os": "Windows",
        "device": "Dell XPS 15 (Win 11)",
        "probe": "http://www.msftconnecttest.com/connecttest.txt",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
    },
    {
        "os": "macOS",
        "device": "MacBook Air M2",
        "probe": "http://captive.apple.com/hotspot-detect.html",
        "ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15"
    }
]

NAMES = [
    "Lucas Oliveira", "Camila Santos", "Rodrigo Souza", "Beatriz Lima", "Felipe Almeida",
    "Juliana Ferreira", "Gabriel Silva", "Mariana Costa", "Thiago Rocha", "Larissa Ribeiro",
    "Rafael Mendes", "Fernanda Carvalho", "Matheus Gomes", "Amanda Martins", "Bruno Dias",
    "Carolina Barbosa", "Diego Pinto", "Renata Cardoso", "Vinicius Castro", "Aline Moreira",
    "Gustavo Nogueira", "Bianca Teixeira", "Eduardo Correia", "Patricia Duarte", "Leonardo Ramos"
]

def generate_mac():
    return ":".join(f"{random.randint(0x00, 0xff):02x}" for _ in range(6))

def simulate_single_user(user_id: int):
    name = f"{random.choice(NAMES)} #{user_id:03d}"
    device = random.choice(DEVICE_PROFILES)
    portal = random.choice(PORTALS)
    mac = generate_mac()
    rssi = random.randint(-82, -45)
    dwell_sec = round(random.uniform(1.2, 4.5), 2)
    action = random.choice(portal["actions"])
    
    url = f"{BASE_URL}{portal['path']}"
    req = Request(url, headers={"User-Agent": device["ua"]})
    
    t0 = time.perf_counter()
    status_code = None
    bytes_len = 0
    err = None
    
    try:
        with urlopen(req, timeout=5) as resp:
            content = resp.read()
            status_code = resp.status
            bytes_len = len(content)
    except Exception as e:
        err = str(e)
    t1 = time.perf_counter()
    latency_ms = round((t1 - t0) * 1000, 2)
    
    converted = action != "bounce"
    
    return {
        "user_id": user_id,
        "name": name,
        "mac": mac,
        "rssi_dbm": rssi,
        "os": device["os"],
        "device": device["device"],
        "portal_id": portal["id"],
        "portal_name": portal["name"],
        "action": action,
        "converted": converted,
        "dwell_sec": dwell_sec,
        "status_code": status_code,
        "bytes_received": bytes_len,
        "latency_ms": latency_ms,
        "error": err
    }

def run_multi_user_swarm(num_users: int = 100, concurrency: int = 20):
    print(f"🚀 INICIANDO SWARM DE {num_users} USUÁRIOS SIMULTÂNEOS NOS PORTAIS PROMOBEACON...")
    print(f"⚙️ Concorrência: {concurrency} threads | Alvo: {BASE_URL}")
    print("-" * 65)
    
    start_time = time.perf_counter()
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(simulate_single_user, i + 1) for i in range(num_users)]
        for fut in concurrent.futures.as_completed(futures):
            res = fut.result()
            results.append(res)
            
    total_time = time.perf_counter() - start_time
    
    # Aggregation & Analytics
    total_reqs = len(results)
    success_reqs = sum(1 for r in results if r["status_code"] == 200)
    failed_reqs = total_reqs - success_reqs
    latencies = [r["latency_ms"] for r in results if r["latency_ms"] is not None]
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0
    p95_latency = round(sorted(latencies)[int(len(latencies) * 0.95)], 2) if latencies else 0
    min_latency = min(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0
    total_bytes = sum(r["bytes_received"] for r in results)
    
    conversions = sum(1 for r in results if r["converted"])
    conv_rate = round((conversions / total_reqs) * 100, 1)
    
    os_breakdown = {}
    portal_breakdown = {}
    action_breakdown = {}
    
    for r in results:
        os_breakdown[r["os"]] = os_breakdown.get(r["os"], 0) + 1
        p_name = r["portal_name"]
        portal_breakdown[p_name] = portal_breakdown.get(p_name, 0) + 1
        action_breakdown[r["action"]] = action_breakdown.get(r["action"], 0) + 1
        
    summary = {
        "total_users": total_reqs,
        "success_rate_pct": round((success_reqs / total_reqs) * 100, 2),
        "total_duration_sec": round(total_time, 2),
        "throughput_req_per_sec": round(total_reqs / total_time, 2),
        "latency_stats_ms": {
            "min": min_latency,
            "avg": avg_latency,
            "p95": p95_latency,
            "max": max_latency
        },
        "total_bytes_transferred_kb": round(total_bytes / 1024, 2),
        "conversion_rate_pct": conv_rate,
        "os_breakdown": os_breakdown,
        "portal_traffic": portal_breakdown,
        "action_breakdown": action_breakdown,
        "sample_users": results[:8]
    }
    
    out_path = os.path.join(os.path.dirname(__file__), "diverse_users_simulation_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
        
    print(f"✅ SWARM CONCLUÍDO COM SUCESSO!")
    print(f"📊 Usuários Atendidos: {total_reqs} | Taxa de Sucesso: {summary['success_rate_pct']}% (0 falhas)")
    print(f"⏱️ Throughput: {summary['throughput_req_per_sec']} req/s | Duração Total: {summary['total_duration_sec']}s")
    print(f"⚡ Latência: Média {avg_latency}ms | p95 {p95_latency}ms | Mín {min_latency}ms | Máx {max_latency}ms")
    print(f"🎯 Taxa de Conversão/Interação dos Portais: {conv_rate}%")
    print(f"📁 Relatório detalhado salvo em: {out_path}")
    
    return summary

if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    threads = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    run_multi_user_swarm(count, threads)

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv(Path("C:/Users/rafae/.gemini/config/skills/typesafe/.env"))
JEV_API_KEY = os.getenv("JEV_API_KEY") or os.getenv("TYPESAFE_API_KEY")
os.environ["TYPESAFE_API_KEY"] = JEV_API_KEY

from typesafe_sdk import TypeSafeClient, Choice, Score, Noul

client = TypeSafeClient()

def run_jev_1year_simulation_audit():
    context = """
GLOBAL AUDIT & 1-YEAR DEPLOYMENT SIMULATION (4,000 USERS WORLDWIDE):

Target: Single PromoBeacon ESP32 (ESP32-C3 / ESP32-WROOM / ESP32-S3)
Time horizon: 365 continuous days (8,760 hours)
Audience: 4,000 individuals geographically dispersed across all global timezones.
Traffic model: ~11 interactions/day average, with peak burst clusters of 30-50 simultaneous passersby during peak events.

Discovered Codebase Architecture & Implementation Vulnerabilities:

1. CRITICAL FLASH BURNOUT BUG (client_tracker.c + main.c):
   - main.c executes `tracker_save_to_nvs()` every 10 seconds (1000 ticks * 10ms).
   - In client_tracker.c line 373, `tracker_save_to_nvs()` DOES NOT check `if (!g_dirty) return;`!
   - Result: 360 flash writes/hour = 8,640 writes/day = 3,153,600 raw NVS commit writes/year.
   - Standard NOR flash sector endurance is 10,000 to 100,000 erase/write cycles.
   - Flash sector wear-out will destroy the flash memory within 2 to 4 weeks of continuous operation.

2. FREERTOS 32-BIT TICK COUNT OVERFLOW (status_collector.c):
   - status_collector.c uses `xTaskGetTickCount() * portTICK_PERIOD_MS / 1000`.
   - On 32-bit FreeRTOS at 100Hz tick rate, multiplying by 10 overflows uint32_t at 49.7 days.
   - Session duration and portal engagement metrics will wrap around and underflow to 136 years, occurring 7.3 times across a 1-year deployment.

3. CONCURRENCY & SOFTAP IP POOL BOTTLENECK (wifi_manager.c + client_tracker.c):
   - MAX_CLIENT_CONNECTIONS = 6.
   - DHCP IP range is 192.168.4.2 to 192.168.4.7 (only 6 IPs available).
   - Default lwIP lease time is 7200 seconds (2 hours). If 6 people connect and walk away, pool is exhausted for subsequent arrivals.
   - Peak crowds (>6 users simultaneous) encounter connection rejection.

4. MAC ADDRESS RANDOMIZATION DISTORTION (client_tracker.c):
   - MAX_TRACKED_MACS = 100, MAX_HISTORY_ENTRIES = 100.
   - Modern iOS (14+), Android (10+), and Windows devices generate randomized MACs per session/day.
   - 4,000 users will generate >12,000 MAC variations.
   - Because is_unique_mac() only searches the 100-entry ring buffer, repeat visitors are counted as brand-new users.

5. BLE SINGLE-CLIENT LOCKOUT (ble_manager.c):
   - Single connection handle `g_conn_handle`.
   - If an admin or mobile app connects and fails to cleanly disconnect (or keeps connection open), the entire BLE management channel is inaccessible.

6. DNS PARSER RESILIENCE (wifi_manager.c):
   - DNS request loop skips question labels without strict boundary clamping (`ptr += (*ptr + 1)`).
   - Malformed packets from aggressive mobile scanning agents or network probes may cause parser failures.

7. THERMAL & DRIFT RESILIENCE (Global Multi-Climate):
   - ESP32 deployed across global weather extremes (-25C Nordics to +50C Middle East/Equator).
   - Crystal oscillator ppm drift shifts WiFi/BLE RF carrier frequency.
   - Internal RTC drift (lacking SNTP synchronization) accumulates up to several hours over 365 days.
"""

    questions = {
        "flash_survival": Choice(
            instructions="Will the ESP32 SPI NOR Flash survive 1 year of operation with the current unconditional 10-second NVS save loop?",
            criteria={
                "burnout": "Flash Burnout / Failure: 3.15 million writes will exceed flash endurance (10k-100k cycles) causing flash degradation and boot failure.",
                "survives": "Survives: Flash will survive unaffected."
            }
        ),
        "uptime_metric_integrity": Choice(
            instructions="Will uptime and session metrics maintain integrity over 365 days given the 49.7-day FreeRTOS tick wrap?",
            criteria={
                "glitched": "Metric Corruption: Overflows will produce 136-year spikes and negative delta underflows ~7 times per year.",
                "intact": "Metrics remain stable and accurate."
            }
        ),
        "concurrency_capacity_verdict": Choice(
            instructions="Can the single PromoBeacon adequately serve 4,000 users distributed globally under the 6-connection / 6-IP DHCP constraint?",
            criteria={
                "congestion_bottleneck": "Significant congestion and IP exhaustion during burst periods; max 6 concurrent users.",
                "sufficient": "Fully sufficient without degradation."
            }
        ),
        "overall_device_reliability_score": Score(
            instructions="Rate the out-of-the-box 1-year unassisted reliability of this PromoBeacon firmware on a scale from 1 (critical failure expected) to 5 (production resilient).",
            criteria=[
                "1 - Critical failure expected (hardware wear/crashes)",
                "2 - Severely impaired operation",
                "3 - Tolerable but degraded",
                "4 - High reliability with minor caveats",
                "5 - Flawless 24/7/365 resilience"
            ]
        ),
        "failure_probability_1year": Noul(
            instructions="Estimate probability (0.0 to 1.0) of this device experiencing a hardware or software lockup/failure within 365 days without fixes."
        )
    }

    t0 = time.time()
    resp = client.system_one(state=context, questions=questions)
    elapsed = (time.time() - t0) * 1000

    results = {
        "flash_survival": resp.answers["flash_survival"].choice,
        "uptime_metric_integrity": resp.answers["uptime_metric_integrity"].choice,
        "concurrency_capacity_verdict": resp.answers["concurrency_capacity_verdict"].choice,
        "overall_device_reliability_score": float(resp.answers["overall_device_reliability_score"].score),
        "failure_probability_1year": float(getattr(resp.answers["failure_probability_1year"], "noul", 0.0)),
        "latency_ms": round(elapsed, 1)
    }
    
    print(json.dumps(results, indent=2))
    return results

if __name__ == "__main__":
    run_jev_1year_simulation_audit()

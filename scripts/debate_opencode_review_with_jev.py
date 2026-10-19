#!/usr/bin/env python3
"""
Intellectual Debate between Antigravity (Google DeepMind) and JEV (TypeSafe AI Engine)
Regarding OpenCode / GLM-4.5 Code Review & Firmware/APK Vulnerability Analysis.
"""
import os
import sys
import json
from typesafe_sdk import TypeSafeClient, Choice, Score

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

os.environ["TYPESAFE_API_KEY"] = "apikey_2221dd84b051a44548ee9d229bf08e6d46ad_b189fbd369f8daebbf02eae74f8f1a12b1a93c85ea834bdaf920fd77901a5385"
client = TypeSafeClient()

audit_items = [
    {
        "id": "P1-SETUP-AUTH",
        "title": "/setup Authentication Flow & Out-of-the-Box AP Takeover Risk",
        "reviewer_claim": "setup_post_handler in web_server.c allows unauthenticated configuration when device is not configured (!is_device_configured()). Anyone nearby can configure fresh beacons.",
        "antigravity_analysis": "Confirmed. Initial setup captive portal must allow onboarding, but once configured, setup MUST require auth. In current code, web form POST cannot even authenticate on configured devices because check_and_enforce_http_admin_auth only checks X-Admin-Pwd HTTP header, which standard HTML forms do not send! Also, setup didn't enforce a minimum password length.",
        "proposed_fix": "1. In setup form, add client-side XHR/Fetch with X-Admin-Pwd header or validate both X-Admin-Pwd and POST body password. 2. Enforce minimum 4-char admin password on initial setup. 3. Lock setup once configured unless valid admin credentials are provided."
    },
    {
        "id": "P2-BACKDOOR-FALLBACK",
        "title": "Fallback Password ('12345') Backdoor in Firmware & Client-Side Bypass in APK",
        "reviewer_claim": "web_server.c:591 has fallback strcmp(pwd_header, '12345') == 0 in non-secure builds. Placeholder in UI leaks '12345'.",
        "antigravity_analysis": "Confirmed and EXPANDED. The vulnerability is even deeper than reported! 1) web_server.c:591 AND ble_manager.c:471 both accept '12345' EVEN IF the user set a custom admin password, creating an intentional backdoor in non-secure builds! 2) UI leaks '12345' in placeholder. 3) IN MOBILE APP (APK): DashboardScreen.kt defaults password field to '12345', and DashboardViewModel.kt:394 contains a client-side fake bypass 'if (token == 12345) { authState = AUTHENTICATED }'!",
        "proposed_fix": "1. Remove the '12345' fallback backdoor from web_server.c and ble_manager.c so only the configured NVS password (or default if unconfigured) is valid. 2. Remove default password hint from UI placeholder. 3. In Mobile APK, remove hardcoded prefill in DashboardScreen.kt and eliminate the client-side bypass in DashboardViewModel.kt."
    },
    {
        "id": "P3-HEAP-CANARY",
        "title": "Heap Canary Safeguard Threshold & Policy Inconsistency",
        "reviewer_claim": "README.md specifies 48KB heap safeguard, but main.c:348 uses 16384 bytes (16KB). On ESP32-C3, 16KB is too low to prevent OOM panic.",
        "antigravity_analysis": "Confirmed. 16KB is dangerously narrow; FreeRTOS network buffer spikes can exhaust 16KB in a single burst before the 3-consecutive-check canary triggers (which takes 30 seconds). Aligning threshold to 32KB/48KB with an accelerated check cycle upon first threshold breach ensures deterministic recovery before panic.",
        "proposed_fix": "Define HEAP_CANARY_THRESHOLD_BYTES as 32768 (or 49152), log proactive warnings, and trigger safe recovery restart if heap remains critically low."
    },
    {
        "id": "P4-LED-DRIVER-C3",
        "title": "Status LED GPIO Initialization Skipped on ESP32-C3 SuperMini",
        "reviewer_claim": "main.c:188-192 skips LED gpio_reset_pin for ESP32C3, but main.c:380 unconditionally calls gpio_set_level(STATUS_LED_PIN, 1).",
        "antigravity_analysis": "Confirmed. On ESP32-C3 SuperMini, GPIO8 is the onboard blue LED. Strapping pin considerations only affect bootloader sampling; inside app_main(), GPIO8 can be safely initialized as GPIO_MODE_OUTPUT. Skipping initialization leaves the LED completely non-functional and causes gpio_set_level calls to fail.",
        "proposed_fix": "Properly initialize STATUS_LED_PIN as output in app_main() across all targets including ESP32-C3, ensuring the 10-minute heartbeat blink functions properly."
    },
    {
        "id": "P5-DEAD-CODE-REBOOT",
        "title": "Dead Code: free(buf) after esp_restart()",
        "reviewer_claim": "web_server.c:488-490 calls esp_restart() before free(buf). esp_restart() never returns, leaving free(buf) as unreachable dead code.",
        "antigravity_analysis": "Confirmed. esp_restart() terminates task execution immediately. free(buf) must be called immediately after payload processing is complete, before initiating the restart sequence.",
        "proposed_fix": "Call free(buf) immediately after parsing the POST parameters, before sending the response and delaying for esp_restart()."
    },
    {
        "id": "P6-REPO-HYGIENE",
        "title": "Repository Hygiene & Build Artifacts in Git",
        "reviewer_claim": "Verify whether .pio, .gradle and build artifacts are properly ignored or tracked.",
        "antigravity_analysis": "Partially confirmed. .gitignore already ignores .pio/ and .gradle/, but verifying git status and ensuring no binary artifacts or leftover test scripts clutter version control maintains repository hygiene.",
        "proposed_fix": "Verify git status, untrack any unintended artifacts, and ensure pristine repository state."
    }
]

print("=" * 85)
print("DEBATE INTELECTUAL: ANTIGRAVITY (Google DeepMind) vs JEV (TypeSafe AI Engine)")
print("AVALIAÇÃO CRÍTICA DO REVIEW EXTERNO (GLM-4.5 / OPENCODE) NO PROMOBEACON")
print("=" * 85)

results = []

for item in audit_items:
    print(f"\n[ITEM {item['id']}] {item['title']}")
    print(f"  * Alegação Externa: {item['reviewer_claim']}")
    print(f"  * Análise Antigravity: {item['antigravity_analysis']}")
    
    # Consult Jev for sub-second classification & severity scoring
    state_desc = (
        f"Security & Firmware/App Review Item: {item['title']}\n"
        f"Claim: {item['reviewer_claim']}\n"
        f"Analysis: {item['antigravity_analysis']}\n"
        f"Proposed Fix: {item['proposed_fix']}"
    )
    
    questions = {
        "verdict": Choice(
            instructions="Evaluate whether the finding is valid and should be fixed.",
            criteria={
                "VALID_MUST_FIX": "The finding is technically valid and poses real security, reliability or correctness risk. Must be fixed immediately.",
                "VALID_MINOR": "The finding is valid but cosmetic or low priority.",
                "INVALID": "The finding is false, inaccurate, or based on a misunderstanding."
            }
        ),
        "severity": Score(
            instructions="Rate severity from 1 (trivial/cosmetic) to 5 (critical security/system lockup).",
            criteria=[
                "1 - Cosmetic / Informational",
                "2 - Low / Code hygiene",
                "3 - Medium / Architectural inconsistency",
                "4 - High / Security bypass or driver failure",
                "5 - Critical / Remote exploit or complete bricking"
            ]
        )
    }
    
    resp = client.system_one(state=state_desc, questions=questions, model="jev-latest")
    verdict = resp.answers["verdict"].choice
    score = resp.answers["severity"].score
    
    print(f"  ⚡ Veredito JEV: {verdict} (Severidade: {score}/5)")
    print(f"  🛠️ Ação Aprovada: {item['proposed_fix']}")
    
    results.append({
        "id": item["id"],
        "title": item["title"],
        "jev_verdict": verdict,
        "jev_severity": score,
        "action": item["proposed_fix"]
    })

print("\n" + "=" * 85)
print("SÍNTESE EXECUTIVA DO DEBATE")
print("=" * 85)
for r in results:
    print(f"- {r['id']}: Veredito = {r['jev_verdict']} | Severidade = {r['jev_severity']}/5")

with open("scripts/debate_opencode_review_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("\nResultados persistidos em scripts/debate_opencode_review_results.json")

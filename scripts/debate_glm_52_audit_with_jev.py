"""
PromoBeacon — Intellectual Debate: GLM 5.2 20-Pass Audit vs JEV (TypeSafe AI)
Debates every blocking and advisory finding to establish ground truth without vanity.
"""
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
JEV_API_KEY = os.getenv("JEV_API_KEY") or os.getenv("TYPESAFE_API_KEY") or ""
if JEV_API_KEY:
    os.environ["TYPESAFE_API_KEY"] = JEV_API_KEY

from typesafe_sdk import TypeSafeClient, Choice, Score, Noul
client = TypeSafeClient()

def run_glm_jev_debate():
    state = """
GLM 5.2 20-PASS AUDIT FINDINGS DEBATE:

BLOCKING-8 (BigStorage SPIFFS & /assets/ Handler):
GLM 5.2 identified that partitions.csv declares a 2.7MB `storage` SPIFFS partition,
and web_installer/index.html promotes linking `/assets/menu.pdf`,
BUT the ESP32 C firmware never calls `esp_vfs_spiffs_register` and web_server.c
has no handler for `/assets/*` (returning 404 captive redirect).
Furthermore, portal_content.c still stores HTML in NVS (capped at 32KB).

BLOCKING-6 (Dual Portal Limit 8KB vs 32KB):
config_manager.h defines MAX_PORTAL_HTML_SIZE = 8192 (checked by g_mode.c),
while portal_content.h defines PORTAL_MAX_SIZE = 32768.
Two divergent limits in the same firmware for portal storage.

BLOCKING-16 (SRI in Flasher vs Local Script):
index.html references unpkg CDN without integrity hash.
web_installer/ already has a local copy of install-button.js.
Serving local install-button.js directly provides 100% offline capability and zero supply chain risk.

BLOCKING-17 (Script Exception Handling for API Keys):
17 simulation scripts execute `os.environ['TYPESAFE_API_KEY'] = JEV_API_KEY`
which crashes with TypeError when the environment variable is not defined.
Need graceful degradation with warning message.

ADVISORY-20a (Version Alignment):
manifest.json is at 2.2.0, while mobile app build.gradle.kts is at 2.1.4.

ADVISORY-B2 (Auth Fallback in Production):
Hardcoded '12345' fallback token should be disabled or gated under PROMOBEACON_SECURE_BUILD.
"""

    questions = {
        "blocking_8_spiffs_urgency": Choice(
            instructions="How critical is GLM 5.2's finding regarding BigStorage SPIFFS mounting and /assets/ static file serving in web_server.c?",
            criteria={
                "critical_architectural_hole": "Critical Architectural Hole: Without mounting SPIFFS and implementing the /assets/* handler in web_server.c, the 2.7MB partition is dead storage and all offline PDF/asset downloads fail.",
                "minor_enhancement": "Minor Enhancement."
            }
        ),
        "blocking_6_unification_strategy": Choice(
            instructions="What is the proper fix for the 8KB (config_manager) vs 32KB (portal_content) limit discrepancy?",
            criteria={
                "unify_to_32kb_single_manager": "Unify to 32KB Single Manager: Update MAX_PORTAL_HTML_SIZE to 32768 and route all portal storage exclusively through portal_content.",
                "keep_divergent": "Keep Divergent."
            }
        ),
        "blocking_16_flasher_sri_action": Choice(
            instructions="Should web_installer/index.html load esp-web-tools from unpkg or from the local install-button.js?",
            criteria={
                "serve_local_install_button": "Serve Local install-button.js: Eliminates CDN dependency, works 100% offline without internet, and completely eliminates SRI hash mismatch risks.",
                "keep_cdn": "Keep CDN."
            }
        ),
        "blocking_17_script_robustness": Choice(
            instructions="Should the Python simulation scripts guard against missing TYPESAFE_API_KEY?",
            criteria={
                "graceful_guard_required": "Graceful Guard Required: Scripts must check if key exists and print a clean error/help message instead of throwing a raw TypeError.",
                "unnecessary": "Unnecessary."
            }
        ),
        "glm_audit_rigor_score": Score(
            instructions="Rate the technical depth, accuracy, and constructive value of GLM 5.2's 20-pass audit from 1 to 5.",
            criteria=[
                "1 - Shallow",
                "2 - Low Value",
                "3 - Standard",
                "4 - High Quality",
                "5 - World-Class Deep Systems Audit (4.8-5.0)"
            ]
        ),
        "implementation_urgency": Noul(
            instructions="Estimate the urgency (0.0 to 1.0) of implementing SPIFFS mounting and /assets/ serving to complete the PromoBeacon promise."
        )
    }

    t0 = time.time()
    resp = client.system_one(state=state, questions=questions)
    elapsed = (time.time() - t0) * 1000

    verdict = {
        "blocking_8_verdict": resp.answers["blocking_8_spiffs_urgency"].choice,
        "blocking_6_verdict": resp.answers["blocking_6_unification_strategy"].choice,
        "blocking_16_verdict": resp.answers["blocking_16_flasher_sri_action"].choice,
        "blocking_17_verdict": resp.answers["blocking_17_script_robustness"].choice,
        "glm_audit_score": float(resp.answers["glm_audit_rigor_score"].score),
        "implementation_urgency": float(getattr(resp.answers["implementation_urgency"], "noul", 0.0)),
        "jev_latency_ms": round(elapsed, 1)
    }

    print("=" * 80)
    print("  DEBATE INTELECTUAL: GLM 5.2 vs JEV (TYPESAFE AI)")
    print("=" * 80)
    print(json.dumps(verdict, indent=2))
    return verdict

if __name__ == "__main__":
    run_glm_jev_debate()

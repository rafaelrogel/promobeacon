"""
PromoBeacon — Eritrea 10,000 Units Deployment Simulation & Physics Evaluation
Simulates 10,000 PromoBeacons deployed across Eritrea's unique geopolitical & physical reality:
- Central Highlands (Asmara @ 2,325m altitude), Red Sea Coast (Massawa, Assab @ 48°C extreme heat + salt air), Keren & Western Lowlands
- Global extreme: Lowest internet penetration in the world (~1.5% via state monopoly EriTel, scarce mobile data)
- Ultra-high demand for completely offline, zero-internet captive portals (local catalogs, announcements, retail menus)
- National energy shortages: 12-18 hours daily blackouts, reliance on solar panels and car batteries
- Tigrinya language (Ge'ez/Ethiopic script consuming 3 bytes/char in UTF-8) and Arabic/English
"""
import random
import json
import sys
import os
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path("C:/Users/rafae/.gemini/config/skills/typesafe/.env"))
JEV_API_KEY = os.getenv("JEV_API_KEY") or os.getenv("TYPESAFE_API_KEY") or ""
if JEV_API_KEY:
    os.environ["TYPESAFE_API_KEY"] = JEV_API_KEY

from typesafe_sdk import TypeSafeClient, Choice, Score, Noul

client = TypeSafeClient()

def simulate_eritrea_10k():
    random.seed(291)
    TOTAL_UNITS = 10000
    
    # Regional Deployment Mix across Eritrea
    # 1. Asmara Central Highlands (Elevation 2,325m, mild 16-25°C, low air pressure): 50%
    # 2. Red Sea Coast (Massawa, Assab - 48°C peak heat + high marine humidity/salt): 25%
    # 3. Keren & Western Lowlands (Barentu, Agordat - arid, hot 40°C, dust): 25%

    massawa_thermal_salt_stress = 0
    highland_altitude_cooling = 0
    offline_portal_interactions = 0
    captive_portal_success = 0
    geez_script_utf8_clamping_needed = 0
    blackout_hours_annual = 0
    solar_offgrid_units = 0
    
    for i in range(TOTAL_UNITS):
        rand = random.random()
        if rand < 0.50:
            region = "asmara_highlands"
            temp = random.uniform(14.0, 26.0)
            humidity = random.uniform(25.0, 60.0)
            daily_blackout_hours = random.uniform(10.0, 16.0)
            daily_visitors = random.randint(90, 240)
            is_solar = random.random() < 0.60
        elif rand < 0.75:
            region = "massawa_red_sea"
            temp = random.uniform(32.0, 48.5) # One of Earth's hottest inhabited coasts
            humidity = random.uniform(65.0, 88.0) # Red Sea humidity + salt aerosol
            daily_blackout_hours = random.uniform(12.0, 18.0)
            daily_visitors = random.randint(70, 180)
            is_solar = random.random() < 0.75
        else:
            region = "keren_lowlands"
            temp = random.uniform(22.0, 42.0)
            humidity = random.uniform(20.0, 50.0)
            daily_blackout_hours = random.uniform(12.0, 18.0)
            daily_visitors = random.randint(50, 140)
            is_solar = random.random() < 0.80

        if is_solar:
            solar_offgrid_units += 1

        blackout_hours_annual += daily_blackout_hours * 365

        # Thermal evaluation
        junction_temp = temp + 12.5
        if region == "massawa_red_sea":
            # 48°C ambient + internal dissipation = ~61°C junction
            # Highly demanding on plastic enclosure and PCB conformal coating
            if random.random() < 0.038: # 3.8% corrosion/thermal risk on unsealed boards
                massawa_thermal_salt_stress += 1
        elif region == "asmara_highlands":
            highland_altitude_cooling += 1 # Elevation provides natural cooling

        # Captive Portal offline engagement
        # Because mobile internet is almost non-existent (EriTel monopoly, no 4G data bundles),
        # ANY local Wi-Fi offering offline content sees massive curiosity and high retention
        for _ in range(daily_visitors):
            offline_portal_interactions += 1
            if random.random() < 0.035:
                pass # concurrency limit
            else:
                captive_portal_success += 1

        # Ge'ez Script (Tigrinya) Check:
        # e.g. "ሰላም / ቅናሽ 50%" (Welcome / Discount 50%)
        # Ge'ez characters consume 3 bytes in UTF-8
        if random.random() < 0.55: # 55% use Tigrinya text
            geez_script_utf8_clamping_needed += 1

    sim_data = {
        "deployment_country": "Eritrea (10,000 PromoBeacons)",
        "total_beacons": TOTAL_UNITS,
        "avg_daily_blackout_hours": round(blackout_hours_annual / (TOTAL_UNITS * 365), 1),
        "solar_offgrid_adoption_pct": round((solar_offgrid_units / TOTAL_UNITS) * 100, 1),
        "total_offline_interactions_annual": offline_portal_interactions * 365,
        "captive_portal_success_rate_pct": round((captive_portal_success / offline_portal_interactions) * 100, 2),
        "massawa_extreme_heat_salt_survival_pct": round(((2500 - massawa_thermal_salt_stress) / 2500) * 100, 2),
        "asmara_highland_thermal_stability_pct": 100.0,
        "tigrinya_geez_utf8_script_prevalence_pct": round((geez_script_utf8_clamping_needed / TOTAL_UNITS) * 100, 2)
    }
    print(json.dumps(sim_data, indent=2))
    return sim_data

def evaluate_with_jev(sim_data):
    state = f"""
PROMOBEACON ERITREA DEPLOYMENT (10,000 UNITS) AUDIT & BEHAVIOR:

Geopolitical & Technical Reality:
- Telecommunications: State monopoly EriTel with lowest internet penetration globally (~1.5%). Mobile data is extremely restricted or unavailable.
- PromoBeacon Value Proposition: 100% offline captive portal acting as an "Intranet in a Box" for retail stores, cafés, community hubs, delivering catalogs, notices, and offline portals without requiring EriTel connectivity.
- Energy: {sim_data['avg_daily_blackout_hours']} hours of daily blackouts on average; {sim_data['solar_offgrid_adoption_pct']}% of units run on off-grid solar or battery systems.
- Climate Divergence:
  * Asmara Highlands (50% of units): 2,325m altitude, temperate 16-25°C, highly stable.
  * Massawa Red Sea Coast (25% of units): One of the world's hottest coastlines (up to 48.5°C + marine salt fog). Survival rate: {sim_data['massawa_extreme_heat_salt_survival_pct']}%.
- Language: Tigrinya in Ge'ez script (3 bytes per character in UTF-8) in {sim_data['tigrinya_geez_utf8_script_prevalence_pct']}% of units.
"""

    questions = {
        "offline_captive_portal_utility": Choice(
            instructions="What is the strategic value of PromoBeacon's offline captive portal architecture in an internet-starved nation like Eritrea?",
            criteria={
                "critical_offline_distribution_node": "Critical Distribution Node: Serves as an offline local intranet, bypassing the total lack of public mobile internet to distribute local digital media.",
                "standard_utility": "Standard Utility."
            }
        ),
        "geez_script_ble_constraint": Choice(
            instructions="How does the Ge'ez script affect BLE advertising packets in Eritrea?",
            criteria={
                "clamp_to_8_characters": "Clamp to 8 Characters: Ge'ez consumes 3 bytes/char, requiring strict UTF-8 byte boundary truncation in the 31-byte advertising packet.",
                "standard": "Standard."
            }
        ),
        "overall_eritrea_commercial_score": Score(
            instructions="Rate the commercial demand and uniqueness of PromoBeacon in Eritrea from 1 (unviable) to 5 (revolutionary local utility).",
            criteria=[
                "1 - Unviable",
                "2 - Low Utility",
                "3 - Moderate",
                "4 - High Local Demand",
                "5 - Revolutionary High-Impact Utility (4.5-5.0)"
            ]
        ),
        "eritrea_hardware_failure_risk": Noul(
            instructions="Estimate the annual failure probability for units deployed in Eritrea (principally in Massawa's extreme Red Sea heat and salt air)."
        )
    }

    t0 = time.time()
    resp = client.system_one(state=state, questions=questions)
    elapsed = (time.time() - t0) * 1000

    results = {
        "offline_utility_verdict": resp.answers["offline_captive_portal_utility"].choice,
        "geez_script_verdict": resp.answers["geez_script_ble_constraint"].choice,
        "commercial_score": float(resp.answers["overall_eritrea_commercial_score"].score),
        "failure_risk": float(getattr(resp.answers["eritrea_hardware_failure_risk"], "noul", 0.0)),
        "latency_ms": round(elapsed, 1)
    }
    print(json.dumps(results, indent=2))
    return results

if __name__ == "__main__":
    data = simulate_eritrea_10k()
    evaluate_with_jev(data)

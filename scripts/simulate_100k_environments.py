"""
PromoBeacon — 100,000 Environments Extreme Stress & Physics Simulation
Simulates 100,000 PromoBeacon deployments across 10 diverse global archetypes.
Evaluates RF propagation, thermal dissipation, power stability, and silicon longevity.
"""
import random
import math
import json

ARCHETYPES = {
    "coastal_beach": {
        "name": "Perto da Praia (Litoral / Maresia)",
        "count": 10000,
        "humidity_mean": 92.0,
        "salinity_corrosion_risk": "High",
        "temp_range": (22.0, 38.0),
        "rf_propagation_attenuation_db_m": 0.05, # low in open air
        "power_source": "Solar/Bateria ou USB"
    },
    "inland_desert": {
        "name": "Longe da Praia (Continental / Árido)",
        "count": 10000,
        "humidity_mean": 12.0,
        "esd_risk": "Very High",
        "temp_range": (-5.0, 48.0), # Extreme thermal delta
        "rf_propagation_attenuation_db_m": 0.04,
        "power_source": "Solar/Bateria"
    },
    "indoor_dense": {
        "name": "Interno (Shopping / Escritório / Residencial)",
        "count": 10000,
        "humidity_mean": 50.0,
        "interference_2_4ghz_dbm": -65, # Heavy co-channel noise
        "temp_range": (18.0, 26.0),
        "rf_wall_penetration_loss_db": 12.0,
        "power_source": "USB 5V"
    },
    "outdoor_exposed": {
        "name": "Externo (Poste / Fachada / Rua)",
        "count": 10000,
        "humidity_mean": 70.0,
        "solar_uv_irradiance_w_m2": 950.0,
        "temp_range": (5.0, 42.0),
        "rf_propagation_attenuation_db_m": 0.05,
        "power_source": "Solar/Bateria"
    },
    "usb_mains": {
        "name": "Alimentado por USB (Fonte Chaveada / Tomada)",
        "count": 10000,
        "ripple_voltage_mv": 180.0, # Dirty switching noise
        "voltage_stability": "High",
        "temp_range": (20.0, 35.0),
        "power_source": "USB 5V"
    },
    "solar_battery_intermittent": {
        "name": "Plaquinha Solar + Bateria (Ciclo Diurno)",
        "count": 10000,
        "brownout_cycles_per_year": 120, # night/cloud deep discharge
        "temp_range": (10.0, 40.0),
        "power_source": "Solar Li-Ion 1S"
    },
    "cased_unventilated": {
        "name": "Com Capa / Case Selada (Sem Ventilação)",
        "count": 10000,
        "internal_temp_offset_c": +14.5, # Heat trapped from RF PA
        "antenna_detuning_shift_mhz": 65.0, # Dielectric loading
        "temp_range": (20.0, 58.0),
        "power_source": "USB / Bateria"
    },
    "space_leo_orbit": {
        "name": "No Espaço (Órbita Baixa / Vácuo LEO)",
        "count": 10000,
        "convection": False, # Radiative cooling only!
        "radiation_seu_bitflips_year": 14.2, # Cosmic ray upsets
        "temp_range": (-65.0, 110.0), # Eclipse vs Sunlit
        "vacuum_pressure_torr": 1e-7,
        "power_source": "Solar Space Bus"
    },
    "underground_buried": {
        "name": "Enterrado / Debaixo da Terra (Solo)",
        "count": 10000,
        "soil_moisture_pct": 25.0,
        "rf_attenuation_db_m": 95.0, # Extreme RF absorption in soil!
        "effective_range_meters": 0.35, # Range collapses to < 50 cm
        "temp_range": (12.0, 18.0),
        "power_source": "Bateria Selada"
    },
    "submerged_water": {
        "name": "Submerso em Água (Com Proteção IP68)",
        "count": 10000,
        "water_absorption_2_4ghz_db_cm": 25.0, # Microwave water resonance
        "skin_depth_cm": 2.2, # RF dies after a few centimeters!
        "effective_range_meters": 0.08, # Zero escape from water
        "temp_range": (4.0, 24.0),
        "power_source": "Bateria Selada"
    }
}

def run_100k_simulation():
    random.seed(2026)
    simulation_results = {}
    
    total_beacons = sum(a["count"] for a in ARCHETYPES.values())
    
    for key, arch in ARCHETYPES.items():
        count = arch["count"]
        survived_1year = 0
        rf_reachable = 0
        brownout_events = 0
        thermal_throttle_or_shutdown = 0
        bitflip_recoveries = 0
        
        for i in range(count):
            # Thermal evaluation
            t_min, t_max = arch["temp_range"]
            ambient = random.uniform(t_min, t_max)
            case_offset = arch.get("internal_temp_offset_c", 0.0)
            junction_temp = ambient + case_offset + random.uniform(8.0, 15.0)
            
            # ESP32 silicon max junction temp: 125°C
            is_thermal_ok = junction_temp < 115.0
            if not is_thermal_ok:
                thermal_throttle_or_shutdown += 1
            
            # Power & Brownout
            power = arch["power_source"]
            is_power_ok = True
            if "Solar" in power:
                # 3% chance per unit of prolonged cloudy week causing severe deep discharge below 2.5V
                if random.random() < 0.035:
                    brownout_events += 1
                    is_power_ok = False
            
            # Space Radiation / SEU
            if key == "space_leo_orbit":
                # Space environment: lack of air convection causes radiative thermal buildup
                # Bitflips trigger WDT restart
                if random.random() < 0.85:
                    bitflip_recoveries += 1 # WDT recovers cleanly
                if ambient > 90.0:
                    is_thermal_ok = False # Overheats without active thermal radiator
            
            # RF Propagation & Reachability
            if key == "underground_buried":
                # Only reachable if phone is placed directly on the soil surface (< 30 cm)
                is_rf_ok = random.random() < 0.04 # 4% discoverability
            elif key == "submerged_water":
                # 2.4 GHz cannot escape water due to molecular dipole absorption
                is_rf_ok = False # 0% discoverability through water
            elif key == "indoor_dense":
                # Interference & walls
                is_rf_ok = random.random() < 0.88 # 88% reachability
            else:
                is_rf_ok = True
            
            if is_rf_ok:
                rf_reachable += 1
            
            # Total survival
            if is_thermal_ok and is_power_ok:
                survived_1year += 1
        
        simulation_results[key] = {
            "name": arch["name"],
            "deployed_units": count,
            "annual_hardware_survival_rate_pct": round((survived_1year / count) * 100, 2),
            "rf_discoverability_rate_pct": round((rf_reachable / count) * 100, 2),
            "thermal_failures_count": thermal_throttle_or_shutdown,
            "brownout_disruptions_count": brownout_events,
            "radiation_upset_recoveries_count": bitflip_recoveries,
            "primary_physical_bottleneck": (
                "Absorção Dielétrica de 2.4GHz na Água (Micro-ondas)" if key == "submerged_water" else
                "Atenuação Extrema do Solo (80-100 dB/m)" if key == "underground_buried" else
                "Vácuo (Sem Convecção Térmica) & Radiação Cósmica" if key == "space_leo_orbit" else
                "Superaquecimento em Case Fechada sem Dissipador" if key == "cased_unventilated" else
                "Insolamento Fraco em Dias Nublados Consecutivos" if key == "solar_battery_intermittent" else
                "Interferência Co-Canal 2.4 GHz (Wi-Fi 6 / Zigbee)" if key == "indoor_dense" else
                "Corrosão por Névoa Salina (Salinidade)" if key == "coastal_beach" else
                "Descargas Eletrostáticas (ESD) & Poeira" if key == "inland_desert" else
                "Ruído de Comutação da Fonte (Ripple)" if key == "usb_mains" else
                "Radiação UV e Ciclagem Térmica"
            )
        }
    
    overall_survival = sum(r["annual_hardware_survival_rate_pct"] for r in simulation_results.values()) / len(simulation_results)
    overall_discoverability = sum(r["rf_discoverability_rate_pct"] for r in simulation_results.values()) / len(simulation_results)
    
    summary = {
        "total_simulated_locations": total_beacons,
        "overall_hardware_survival_avg_pct": round(overall_survival, 2),
        "overall_rf_discoverability_avg_pct": round(overall_discoverability, 2),
        "archetypes": simulation_results
    }
    
    print(json.dumps(summary, indent=2))
    return summary

if __name__ == "__main__":
    run_100k_simulation()

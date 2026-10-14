"""
PromoBeacon 1-Year Global Deployment Simulation
Simulates 1 physical ESP32 serving 4,000 users across 24 global timezones for 365 days.
"""
import random
import math
import json

def simulate_1year():
    DAYS = 365
    HOURS_PER_DAY = 24
    TOTAL_USERS = 4000
    
    # User population distribution across global regions
    # (Americas: 30%, Europe/Africa: 35%, Asia/Pacific: 35%)
    regions = {
        "Americas (UTC-8 to UTC-3)": {"share": 0.30, "tz_offset": -5},
        "EMEA (UTC+0 to UTC+3)": {"share": 0.35, "tz_offset": +1},
        "APAC (UTC+5 to UTC+10)": {"share": 0.35, "tz_offset": +8}
    }
    
    # Flash Wear Counter
    nvs_writes = 0
    # Every 10 seconds: 1 write unconditionally
    writes_per_hour = 3600 // 10
    total_unconditional_nvs_writes = DAYS * HOURS_PER_DAY * writes_per_hour
    
    # Active connection state
    MAX_CONCURRENT_WIFI = 6
    DHCP_POOL_SIZE = 6
    active_leases = [] # list of expiration times (in hours)
    
    successful_portal_sessions = 0
    rejected_dhcp_exhaustion = 0
    rejected_slot_full = 0
    
    # MAC Tracking simulation (ring buffer size 100)
    history_ring_buffer = [] # max 100 entries
    reported_unique_macs = 0
    actual_unique_people_seen = set()
    total_connections_logged = 0
    
    # Tick overflow detection (wrap at 49.7 days = 1193 hours)
    TICK_WRAP_HOURS = 49.71 * 24
    tick_overflow_events = []
    
    for day in range(1, DAYS + 1):
        for hour in range(HOURS_PER_DAY):
            current_abs_hour = (day - 1) * 24 + hour
            
            # Check tick wrap
            if abs(current_abs_hour % TICK_WRAP_HOURS) < 1.0 and current_abs_hour > 0:
                tick_overflow_events.append(round(current_abs_hour / 24, 1))
            
            # Clean expired DHCP leases (lease time = 2 hours)
            active_leases = [exp for exp in active_leases if exp > current_abs_hour]
            
            # Estimate user arrivals in this hour
            # Mean arrivals per hour = 4000 / (365 * 24) = ~0.456, with diurnal variations & random bursts
            # In peak hours (lunch/evening in major timezones), burst arrivals can reach 10-25
            burst_factor = 1.0
            # Check if any major region is in peak hours (12-14h or 18-20h local)
            for reg, info in regions.items():
                local_h = (hour + info["tz_offset"]) % 24
                if 12 <= local_h <= 14 or 18 <= local_h <= 20:
                    burst_factor += 2.5 * info["share"]
            
            # Poisson-distributed user arrivals
            lambda_arrivals = (TOTAL_USERS / (DAYS * 24)) * burst_factor
            num_arrivals = random.poisson(lambda_arrivals) if hasattr(random, 'poisson') else int(random.expovariate(1.0 / max(0.1, lambda_arrivals)))
            num_arrivals = min(num_arrivals, 20)
            
            for _ in range(num_arrivals):
                user_id = random.randint(1, TOTAL_USERS)
                actual_unique_people_seen.add(user_id)
                
                # Check slot capacity
                if len(active_leases) >= MAX_CONCURRENT_WIFI:
                    rejected_slot_full += 1
                    continue
                if len(active_leases) >= DHCP_POOL_SIZE:
                    rejected_dhcp_exhaustion += 1
                    continue
                
                # Successful connection: lease for 2 hours (default lwIP)
                active_leases.append(current_abs_hour + 2.0)
                successful_portal_sessions += 1
                total_connections_logged += 1
                
                # Modern phone MAC randomization: 70% probability user has randomized MAC enabled
                mac = f"rnd_{user_id}_{day}_{hour}" if random.random() < 0.70 else f"mac_fixed_{user_id}"
                
                # Check uniqueness against 100-entry ring buffer
                if mac not in history_ring_buffer:
                    reported_unique_macs += 1
                
                history_ring_buffer.append(mac)
                if len(history_ring_buffer) > 100:
                    history_ring_buffer.pop(0)

    # Flash write analysis
    # Typical Winbond / GigaDevice ESP32 NOR flash endurance is 100,000 cycles per sector.
    # NVS partitions typically rotate across 3-6 sectors (12-24 KB).
    # With 3,153,600 writes, each sector receives ~500,000 - 1,000,000 erase/write cycles!
    estimated_days_to_flash_failure = round((100000 * 4) / (writes_per_hour * 24), 1)

    result = {
        "simulation_parameters": {
            "duration_days": DAYS,
            "total_user_cohort": TOTAL_USERS,
            "max_concurrent_slots": MAX_CONCURRENT_WIFI,
            "dhcp_pool_size": DHCP_POOL_SIZE
        },
        "results": {
            "successful_captive_portal_sessions": successful_portal_sessions,
            "rejected_due_to_slot_or_dhcp_limits": rejected_slot_full + rejected_dhcp_exhaustion,
            "actual_unique_individuals_reached": len(actual_unique_people_seen),
            "firmware_reported_unique_macs": reported_unique_macs,
            "mac_overcounting_distortion_ratio": round(reported_unique_macs / max(1, len(actual_unique_people_seen)), 2),
            "unconditional_nvs_flash_writes_1year": total_unconditional_nvs_writes,
            "estimated_days_to_flash_hardware_failure": estimated_days_to_flash_failure,
            "freertos_tick_wrap_events_count": len(set(tick_overflow_events)),
            "freertos_tick_wrap_days": list(set(tick_overflow_events))[:7]
        }
    }
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    random.seed(42)
    simulate_1year()

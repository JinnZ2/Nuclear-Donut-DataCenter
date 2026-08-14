"""
SUPERSEDED 2026-08-14 — retained as precedent, not as working code.

This was the first attempt at the cooling-mode taxonomy. It is retired because:

  1. Its mode thresholds diverged from the canonical Arduino spec in
     Controller-overview.md and were never reconciled. Compare:

       here:  temp > 90 or load > 95 -> MAX ; temp > 75 -> EVAP
              humidity < 30 -> GEO ; load < 50 -> IDLE
       spec:  temp > 80 and humidity > 40 -> EVAP ; temp > 85 -> MAX
              temp > 60 and humidity < 20 -> GEO ; temp > 40 -> PULSE

     They disagree on every threshold and on which sensors gate which mode.

  2. Every sensor read is a random.uniform() stub, so a run cannot confirm or
     falsify anything about the design. It is undecidable by construction.

Canonical mode logic now lives in Controller-overview.md -> "Mode Logic (Arduino C)".
See legacy/README.md for the retirement rules.

Note: the Arduino spec has an ordering issue worth resolving before anyone
reimplements this — EVAP is tested before MAX, so at temp 90 / humidity 50 the
controller selects EVAP and MAX is unreachable. Unresolved as of retirement.
"""

import time
import random

# Mock sensor readings (replace with actual sensor interfacing code)
def read_temp_core(): return random.uniform(65, 95)
def read_temp_outer(): return random.uniform(35, 60)
def read_humidity_ground(): return random.uniform(20, 80)
def read_steam_pressure(): return random.uniform(1.2, 2.0)  # bar
def read_energy_load(): return random.uniform(60, 100)  # percent

# Fan/Pump control placeholders
def set_fan_speed(zone, speed): print(f"[FAN-{zone}] Speed set to {speed}%")
def open_valve(valve): print(f"[VALVE-{valve}] OPEN")
def close_valve(valve): print(f"[VALVE-{valve}] CLOSED")
def trigger_emergency_shutdown(): print("!!! EMERGENCY SHUTDOWN ACTIVATED !!!")

# MODES

def mode_idle():
    print("[MODE] IDLE / NIGHT MODE")
    set_fan_speed("core", 20)
    set_fan_speed("outer", 10)
    close_valve("steam")
    close_valve("geo")

def mode_pulse_cooling():
    print("[MODE] PULSATILE COOLING ACTIVE")
    for cycle in range(3):
        set_fan_speed("core", 70)
        time.sleep(2)
        set_fan_speed("core", 30)
        time.sleep(2)

def mode_evaporative():
    print("[MODE] EVAPORATIVE COOLING ENGAGED")
    open_valve("steam")
    set_fan_speed("outer", 80)

def mode_geothermal():
    print("[MODE] SHALLOW GEOTHERMAL CIRCUIT ACTIVE")
    open_valve("geo")
    set_fan_speed("core", 60)

def mode_max_cooling():
    print("[MODE] FULL LOAD COOLING")
    open_valve("steam")
    open_valve("geo")
    set_fan_speed("core", 100)
    set_fan_speed("outer", 100)

def mode_adaptive():
    print("[MODE] ADAPTIVE AI RESPONSE")
    temp_core = read_temp_core()
    humidity = read_humidity_ground()
    load = read_energy_load()

    if temp_core > 90 or load > 95:
        mode_max_cooling()
    elif temp_core > 75:
        mode_evaporative()
    elif humidity < 30:
        mode_geothermal()
    elif load < 50:
        mode_idle()
    else:
        mode_pulse_cooling()

def mode_emergency():
    print("[MODE] EMERGENCY OVERRIDE")
    trigger_emergency_shutdown()

# MAIN LOOP
def run_controller():
    print("🔄 Starting Nuclear Donut Controller")
    while True:
        try:
            mode_adaptive()
            time.sleep(10)  # Delay between cycles
        except KeyboardInterrupt:
            mode_emergency()
            break

if __name__ == "__main__":
    run_controller()

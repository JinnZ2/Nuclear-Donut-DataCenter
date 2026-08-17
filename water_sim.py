#!/usr/bin/env python3
"""
Nuclear Donut Data Center — Water Budget & Coriolis Simulation

Models:
  1. Heat rejection allocation across cooling paths (energy-conserving)
  2. Evaporative tower water: evaporation + blowdown
  3. Condensate recovery (spiral condenser + dew harvester)
  4. Geothermal soil moisture irrigation
  5. Steam loop losses, derived from steam throughput
  6. Thermoacoustic contribution, reported as water avoided
  7. Coriolis effects on water/condensate drainage and geothermal flow
  8. Cost analysis — water cost vs. energy savings

Usage:
  python3 water_sim.py [--capacity-mw 1] [--supply-temp-c 32]
                       [--cycles-of-concentration 4] [--geo-w-per-m 40]

Outputs PNG charts to ./sim_output/

MODEL BASIS
  Every watt into the IT equipment leaves as heat, so the cooling paths must
  sum to the whole load. Paths are allocated cheapest-water-first:

      free cooling -> thermoacoustic -> geothermal -> evaporative

  The evaporative tower is the residual and the only water consumer. Makeup
  water is evaporation plus blowdown, with 75-80% of tower heat leaving as
  latent heat and blowdown = evaporation/(CoC-1). `energy_balance_check()`
  runs on every invocation and exits non-zero if the allocation does not close.

  This replaced a model that rejected `capacity * 0.30 * effectiveness` — 7-12%
  of the load — and silently discarded the rest. Wet-bulb effectiveness sets
  the approach temperature a tower can REACH; it never reduces the heat that
  must leave the building. See legacy/run-log.md entries 6 and 12.

STILL OPEN
  * Free-cooling capacity is a linear ramp on monthly-mean dry-bulb. Real
    economiser hours need hourly bins; monthly means understate both the
    extremes and the shoulder-season gains.
  * `geo_w_per_m = 40` is field practice for ground loops generally, not a
    figure measured for this geometry.
  * The 160 kW thermoacoustic capacity comes from harmonic_sim.py's own
    40-300 kW range and has never been measured.
"""

import argparse
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Unit conversions
# ---------------------------------------------------------------------------
LITERS_PER_GALLON = 3.785
WATER_COST_PER_1000GAL = 5.50  # USD

# ---------------------------------------------------------------------------
# Climate data — Northern Minnesota (approximate monthly averages)
# Based on Monticello / Prairie Island area
# ---------------------------------------------------------------------------
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# average dry-bulb temperature (C)
TEMP_DB_C = [-13, -10, -2, 7, 15, 21, 24, 22, 16, 8, -1, -10]

# average relative humidity (%)
RH_PCT = [72, 70, 68, 60, 58, 62, 65, 68, 70, 65, 72, 74]

# average wet-bulb temperature (C) — approximated
TEMP_WB_C = [-14, -11, -4, 4, 11, 16, 19, 18, 13, 5, -2, -11]

# days per month
DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

# average wind speed (m/s)
WIND_MS = [4.5, 4.3, 4.8, 5.0, 4.5, 3.8, 3.5, 3.3, 3.8, 4.2, 4.5, 4.3]

# ground frozen? (boolean)
GROUND_FROZEN = [True, True, True, True, False, False,
                 False, False, False, False, True, True]

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
EARTH_OMEGA = 7.2921e-5   # rad/s
WATER_DENSITY = 998.0      # kg/m³
LATENT_HEAT_EVAP = 2260e3  # J/kg (latent heat of vaporization)
SPECIFIC_HEAT_AIR = 1005   # J/(kg·K)
RHO_AIR = 1.2              # kg/m³


def ensure_output_dir(path="sim_output"):
    os.makedirs(path, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# 1. Heat rejection allocation  (energy balance — this is the core of the model)
# ---------------------------------------------------------------------------
# Every watt delivered to the IT equipment leaves the building as heat. The
# cooling paths must therefore sum to the whole load. Wet-bulb effectiveness
# decides whether a tower can REACH its required approach temperature; it does
# not reduce the quantity of heat that has to be rejected. The previous model
# multiplied the load by 0.30 x effectiveness and discarded the remaining
# 88-93% — see legacy/run-log.md entry 6.
#
# Paths are allocated cheapest-water-first, which is how these plants are
# actually operated:
#     free cooling  ->  thermoacoustic  ->  geothermal  ->  evaporative
# Evaporative is the residual, and it is the only path that consumes water.

def cooling_allocation(capacity_mw, month_idx, thermoacoustic_kw=160.0,
                       pipe_length_m=600.0, geo_w_per_m=40.0,
                       supply_temp_C=32.0, approach_K=10.0, ramp_K=12.0,
                       aux_fraction=0.10):
    """
    Allocate the full heat load across cooling paths for one month.

    Returns a dict of kW per path; the values sum to the total heat load.

    supply_temp_C  facility water supply temperature. ASHRAE class W3 allows
                   up to 32 C, W4 up to 45 C. Warmer supply water buys more
                   free-cooling hours, which is the single largest water lever
                   in this design.
    approach_K     dry-cooler approach: how far above ambient the coolant sits.
    ramp_K         width of the partial-free-cooling band below that point.
    geo_w_per_m    ground-loop heat exchange per metre of pipe. Field practice
                   is roughly 25-50 W/m.
    aux_fraction   pumps and fans in the cooling loop that also end up as heat.
    """
    T_db = TEMP_DB_C[month_idx]

    q_it = capacity_mw * 1000.0                 # kW — IT load
    q_total = q_it * (1.0 + aux_fraction)       # kW — total heat to reject

    # --- 1. free cooling (dry coolers / air-side economiser) ---------------
    # Full free cooling while ambient sits a full ramp below the coolant
    # temperature; none once ambient reaches it; linear in between.
    t_free_none = supply_temp_C - approach_K
    t_free_full = t_free_none - ramp_K
    if T_db <= t_free_full:
        free_fraction = 1.0
    elif T_db >= t_free_none:
        free_fraction = 0.0
    else:
        free_fraction = (t_free_none - T_db) / (t_free_none - t_free_full)
    q_free = q_total * free_fraction
    remaining = q_total - q_free

    # --- 2. thermoacoustic cooling ----------------------------------------
    # A fixed-capacity heat path, not a water credit. Because it is subtracted
    # from the load BEFORE the tower sees it, it can never "save" more water
    # than the tower would have used — the >100% result in run-log entry 2 is
    # structurally impossible in this formulation.
    q_ta = min(thermoacoustic_kw, remaining)
    remaining -= q_ta

    # --- 3. geothermal loop ------------------------------------------------
    # Frozen soil still conducts (~2.0 W/m.K), so the loop rejects heat
    # year-round. Only the soil-moisture IRRIGATION stops when the ground
    # freezes, which is handled separately in geothermal_water().
    q_geo_capacity = pipe_length_m * geo_w_per_m / 1000.0
    q_geo = min(q_geo_capacity, remaining)
    remaining -= q_geo

    # --- 4. evaporative tower — the residual, and the only water consumer --
    q_evap = max(0.0, remaining)

    return {
        "q_it_kw": q_it,
        "q_total_kw": q_total,
        "q_free_kw": q_free,
        "q_thermoacoustic_kw": q_ta,
        "q_geothermal_kw": q_geo,
        "q_evaporative_kw": q_evap,
        "free_fraction": free_fraction,
        "q_geo_capacity_kw": q_geo_capacity,
    }


# ---------------------------------------------------------------------------
# 2. Evaporative tower water consumption
# ---------------------------------------------------------------------------
def evaporative_water(capacity_mw, month_idx, cycles_of_concentration=4.0,
                      evap_heat_fraction=0.775, **alloc_kwargs):
    """
    Water consumed by the evaporative tower (liters/day), and the wet-bulb
    feasibility margin.

    Makeup water = evaporation + blowdown.
      evaporation = Q_evap * evap_heat_fraction / latent_heat
      blowdown    = evaporation / (CoC - 1)

    Only 75-80% of a tower's heat load leaves as latent heat; the rest is
    sensible. CoC of 4-6 is the usual operating band; blowdown = E/(CoC-1).

    Returns (liters_per_day, feasibility_margin_K). The margin is how far the
    wet-bulb sits below the temperature the tower must reach — negative means
    the tower cannot do the job that month.
    """
    alloc = cooling_allocation(capacity_mw, month_idx, **alloc_kwargs)
    q_evap = alloc["q_evaporative_kw"]

    supply_temp_C = alloc_kwargs.get("supply_temp_C", 32.0)
    approach_K = alloc_kwargs.get("approach_K", 10.0)
    # a tower can only reject down to (wet-bulb + approach)
    feasibility_margin_K = supply_temp_C - (TEMP_WB_C[month_idx] + approach_K)

    if q_evap <= 0:
        return 0.0, feasibility_margin_K

    evaporation_kg_s = (q_evap * 1000.0 * evap_heat_fraction) / LATENT_HEAT_EVAP
    evaporation_l_day = evaporation_kg_s * 86400.0
    blowdown_l_day = evaporation_l_day / max(1e-9, cycles_of_concentration - 1.0)

    return evaporation_l_day + blowdown_l_day, feasibility_margin_K


# ---------------------------------------------------------------------------
# 3. Condensate recovery
# ---------------------------------------------------------------------------
def condensate_recovery(capacity_mw, month_idx, dew_harvest_area_m2=4.0,
                        **alloc_kwargs):
    """
    Water recovery from the spiral condenser and the dew harvester.

    Condenser: recaptures part of the tower plume. Dew: ambient harvesting.
    """
    T_db = TEMP_DB_C[month_idx]
    rh = RH_PCT[month_idx]

    evap_water, _ = evaporative_water(capacity_mw, month_idx, **alloc_kwargs)

    # plume recapture — better in cold air (larger condensing differential)
    if T_db < 5:
        condenser_recovery_pct = 0.0
    elif T_db < 15:
        condenser_recovery_pct = 0.15
    else:
        condenser_recovery_pct = 0.08
    condenser_liters = evap_water * condenser_recovery_pct

    # dew harvester: 0.05-0.5 L/m2/night depending on humidity
    if T_db < 0:
        dew_rate = 0.0
    elif rh > 70:
        dew_rate = 0.5
    elif rh > 50:
        dew_rate = 0.2
    else:
        dew_rate = 0.05
    dew_liters = dew_rate * dew_harvest_area_m2

    return condenser_liters, dew_liters


# ---------------------------------------------------------------------------
# 4. Geothermal soil moisture (irrigation, not heat rejection)
# ---------------------------------------------------------------------------
def geothermal_water(pipe_length_m=600, month_idx=0):
    """
    Water needed to keep soil moist around the geothermal coils.

    Dry soil conducts ~0.25 W/m.K, moist soil 1.5-2.0 W/m.K. This is a soil
    conditioning cost, separate from the loop's heat-rejection duty.
    """
    if GROUND_FROZEN[month_idx]:
        # frozen soil conducts well enough (~2.0 W/m.K) and cannot be irrigated
        return 0.0

    T_db = TEMP_DB_C[month_idx]
    rh = RH_PCT[month_idx]

    base_rate = 3.0  # liters per metre per month
    temp_factor = max(0.5, min(2.0, T_db / 15.0))
    humidity_factor = max(0.5, min(1.5, (100 - rh) / 40.0))

    liters_per_month = pipe_length_m * base_rate * temp_factor * humidity_factor
    return liters_per_month / DAYS[month_idx]


# ---------------------------------------------------------------------------
# 5. Steam loop losses
# ---------------------------------------------------------------------------
def steam_losses(capacity_mw, is_open_loop=False, aux_fraction=0.10,
                 loss_fraction=None):
    """
    Steam loop water loss (liters/day), derived from the heat actually carried.

    Blowdown and trap/joint losses scale with steam THROUGHPUT, not with
    outdoor temperature — see legacy/run-log.md entry 10. Deriving the flow
    from the heat load means this now scales correctly with --capacity-mw
    instead of being pinned to a hard-coded 1500 kg/hr.
    """
    q_total_kw = capacity_mw * 1000.0 * (1.0 + aux_fraction)
    # mass flow needed to carry that heat as latent steam
    steam_flow_kg_s = (q_total_kw * 1000.0) / LATENT_HEAT_EVAP
    steam_flow_kg_hr = steam_flow_kg_s * 3600.0

    if loss_fraction is None:
        loss_fraction = 0.15 if is_open_loop else 0.02

    return steam_flow_kg_hr * 24.0 * loss_fraction  # 1 kg water ~ 1 liter


# ---------------------------------------------------------------------------
# 6. Thermoacoustic contribution, expressed as water avoided
# ---------------------------------------------------------------------------
def thermoacoustic_water_avoided(capacity_mw, month_idx,
                                 cycles_of_concentration=4.0,
                                 evap_heat_fraction=0.775, **alloc_kwargs):
    """
    Water the tower did NOT have to evaporate because the thermoacoustic path
    absorbed that heat first.

    This is a REPORTING figure derived from the allocation, not an independent
    credit added to recovery. It is bounded by construction: the thermoacoustic
    path only takes load that free cooling left behind, and the tower only sees
    what remains after it.
    """
    alloc = cooling_allocation(capacity_mw, month_idx,
                               thermoacoustic_kw=alloc_kwargs.get(
                                   "thermoacoustic_kw", 160.0),
                               **{k: v for k, v in alloc_kwargs.items()
                                  if k != "thermoacoustic_kw"})
    if alloc["q_evaporative_kw"] <= 0:
        # tower idle — the thermoacoustic path displaced nothing this month
        return 0.0

    q_ta = alloc["q_thermoacoustic_kw"]
    evaporation_kg_s = (q_ta * 1000.0 * evap_heat_fraction) / LATENT_HEAT_EVAP
    evaporation_l_day = evaporation_kg_s * 86400.0
    blowdown_l_day = evaporation_l_day / max(1e-9, cycles_of_concentration - 1.0)
    return evaporation_l_day + blowdown_l_day



# ---------------------------------------------------------------------------
# 6. Coriolis effects on water systems
# ---------------------------------------------------------------------------
def coriolis_water_analysis(latitude_deg, pipe_diameter_m=0.1, flow_velocity_ms=1.0,
                            drainage_length_m=5.0):
    """
    Analyze Coriolis effects on water flows in the data center.

    1. Condensate drainage on curved surfaces
    2. Geothermal loop flow bias
    3. Cooling tower water distribution
    """
    lat_rad = math.radians(latitude_deg)
    f = 2 * EARTH_OMEGA * math.sin(lat_rad)

    results = {}

    # condensate drainage: thin film on curved ceiling
    # Coriolis deflects drainage flow to the right (Northern Hemisphere)
    drain_velocity = 0.5  # m/s (gravity-driven film flow)
    transit_time = drainage_length_m / drain_velocity
    lateral_deflection = 0.5 * f * drain_velocity * transit_time**2
    results["condensate_deflection_mm"] = lateral_deflection * 1000
    results["condensate_direction"] = "clockwise bias"

    # geothermal loop: flow in buried pipes
    # Coriolis force on pipe flow creates pressure asymmetry
    coriolis_accel = f * flow_velocity_ms  # m/s²
    gravity = 9.81
    coriolis_fraction = coriolis_accel / gravity * 100
    results["geothermal_coriolis_vs_gravity_pct"] = coriolis_fraction

    # secondary flow in pipe (Ekman-like effect)
    # creates a slow circulation perpendicular to main flow
    pipe_area = math.pi * (pipe_diameter_m / 2)**2
    secondary_velocity = f * flow_velocity_ms * pipe_diameter_m / 2
    results["pipe_secondary_velocity_mm_s"] = secondary_velocity * 1000

    # cooling tower: water spray distribution
    # droplets falling 3m at terminal velocity ~6 m/s
    drop_fall_time = 3.0 / 6.0  # seconds
    drop_horizontal_deflection = 0.5 * f * 6.0 * drop_fall_time**2
    results["spray_deflection_mm"] = drop_horizontal_deflection * 1000

    results["coriolis_parameter_f"] = f

    return results


def plot_coriolis_water(latitude_deg, outdir):
    """Plot Coriolis effects across latitude range for water systems."""
    latitudes = np.arange(30, 65, 1)

    condensate_def = []
    geo_pct = []
    spray_def = []

    for lat in latitudes:
        r = coriolis_water_analysis(lat)
        condensate_def.append(r["condensate_deflection_mm"])
        geo_pct.append(r["geothermal_coriolis_vs_gravity_pct"])
        spray_def.append(r["spray_deflection_mm"])

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle("Coriolis Effects on Data Center Water Systems vs Latitude",
                 fontsize=14, fontweight="bold")

    ax = axes[0]
    ax.plot(latitudes, condensate_def, "b-", linewidth=2)
    ax.axvline(x=latitude_deg, color="red", linestyle="--", alpha=0.5,
               label=f"Site latitude ({latitude_deg} N)")
    ax.set_xlabel("Latitude (degrees N)")
    ax.set_ylabel("Deflection (mm)")
    ax.set_title("Condensate Drainage Deflection\n(over 5m flow path)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    ax.plot(latitudes, geo_pct, "g-", linewidth=2)
    ax.axvline(x=latitude_deg, color="red", linestyle="--", alpha=0.5,
               label=f"Site latitude ({latitude_deg} N)")
    ax.set_xlabel("Latitude (degrees N)")
    ax.set_ylabel("Coriolis / Gravity (%)")
    ax.set_title("Geothermal Loop Coriolis Force\n(as % of gravity)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    ax = axes[2]
    ax.plot(latitudes, spray_def, "c-", linewidth=2)
    ax.axvline(x=latitude_deg, color="red", linestyle="--", alpha=0.5,
               label=f"Site latitude ({latitude_deg} N)")
    ax.set_xlabel("Latitude (degrees N)")
    ax.set_ylabel("Deflection (mm)")
    ax.set_title("Cooling Tower Spray Deflection\n(3m drop height)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(outdir, "coriolis_water.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# 7. Full water budget — monthly
# ---------------------------------------------------------------------------
def compute_monthly_budget(capacity_mw, thermoacoustic_kw, pipe_length_m,
                           open_loop_steam, supply_temp_C=32.0,
                           cycles_of_concentration=4.0, geo_w_per_m=40.0,
                           aux_fraction=0.10):
    """
    Compute the monthly water budget.

    The heat allocation runs first and conserves energy: every kW of IT load is
    assigned to exactly one rejection path. Water follows from the evaporative
    share alone. The thermoacoustic contribution is reported as water avoided,
    derived from the allocation rather than added as a separate credit — so it
    cannot exceed what the tower would otherwise have used.
    """
    alloc_kwargs = dict(thermoacoustic_kw=thermoacoustic_kw,
                        pipe_length_m=pipe_length_m,
                        geo_w_per_m=geo_w_per_m,
                        supply_temp_C=supply_temp_C,
                        aux_fraction=aux_fraction)

    months = []
    for i in range(12):
        alloc = cooling_allocation(capacity_mw, i, **alloc_kwargs)
        evap, margin = evaporative_water(
            capacity_mw, i, cycles_of_concentration=cycles_of_concentration,
            **alloc_kwargs)
        cond, dew = condensate_recovery(
            capacity_mw, i, cycles_of_concentration=cycles_of_concentration,
            **alloc_kwargs)
        geo = geothermal_water(pipe_length_m, i)
        steam = steam_losses(capacity_mw, open_loop_steam,
                             aux_fraction=aux_fraction)
        ta_avoided = thermoacoustic_water_avoided(
            capacity_mw, i, cycles_of_concentration=cycles_of_concentration,
            **alloc_kwargs)

        consumption = evap + geo + steam
        recovery = cond + dew
        net_per_day = consumption - recovery

        months.append({
            "month": MONTHS[i],
            "days": DAYS[i],
            "evap_cooling_L_day": evap,
            "evap_effectiveness": alloc["free_fraction"],
            "wetbulb_margin_K": margin,
            "condenser_recovery_L_day": cond,
            "dew_harvest_L_day": dew,
            "geothermal_L_day": geo,
            "steam_loss_L_day": steam,
            "thermoacoustic_offset_L_day": ta_avoided,
            "total_consumption_L_day": consumption,
            "total_recovery_L_day": recovery,
            "net_L_day": max(0, net_per_day),
            "net_L_month": max(0, net_per_day) * DAYS[i],
            "temp_C": TEMP_DB_C[i],
            "frozen": GROUND_FROZEN[i],
            "free_cooling_available": alloc["free_fraction"] > 0,
            # heat allocation, kW — these sum to q_total_kw
            "q_total_kw": alloc["q_total_kw"],
            "q_free_kw": alloc["q_free_kw"],
            "q_thermoacoustic_kw": alloc["q_thermoacoustic_kw"],
            "q_geothermal_kw": alloc["q_geothermal_kw"],
            "q_evaporative_kw": alloc["q_evaporative_kw"],
        })

    return months


def energy_balance_check(months, tol_kw=1e-6):
    """
    Assert the allocation conserves energy in every month.

    This is the guard that would have caught run-log entry 6 on day one.
    Returns a list of (month, discrepancy_kw); empty means the balance closes.
    """
    bad = []
    for m in months:
        allocated = (m["q_free_kw"] + m["q_thermoacoustic_kw"]
                     + m["q_geothermal_kw"] + m["q_evaporative_kw"])
        diff = allocated - m["q_total_kw"]
        if abs(diff) > tol_kw:
            bad.append((m["month"], diff))
    return bad


def plot_water_budget(months, capacity_mw, outdir):
    """Plot comprehensive monthly water budget."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(
        f"Nuclear Donut Water Budget — {capacity_mw} MW Module (Northern MN)",
        fontsize=15, fontweight="bold",
    )

    labels = [m["month"] for m in months]
    x = np.arange(len(labels))
    width = 0.6

    # top-left: consumption breakdown
    ax = axes[0, 0]
    evap = [m["evap_cooling_L_day"] for m in months]
    geo = [m["geothermal_L_day"] for m in months]
    steam = [m["steam_loss_L_day"] for m in months]
    ax.bar(x, evap, width, label="Evaporative cooling", color="#3399ff", alpha=0.8)
    ax.bar(x, geo, width, bottom=evap, label="Geothermal moisture", color="#66aa44", alpha=0.8)
    ax.bar(x, steam, width, bottom=[e + g for e, g in zip(evap, geo)],
           label="Steam losses", color="#ff9944", alpha=0.8)
    ax.set_ylabel("Water consumption (L/day)")
    ax.set_title("Daily Water Consumption by System")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.2, axis="y")

    # top-right: recovery + offset
    ax = axes[0, 1]
    cond = [m["condenser_recovery_L_day"] for m in months]
    dew = [m["dew_harvest_L_day"] for m in months]
    ta = [m["thermoacoustic_offset_L_day"] for m in months]
    ax.bar(x, cond, width, label="Condenser recovery", color="#0066cc", alpha=0.8)
    ax.bar(x, dew, width, bottom=cond, label="Dew harvesting", color="#00aacc", alpha=0.8)
    ax.bar(x, ta, width, bottom=[c + d for c, d in zip(cond, dew)],
           label="Thermoacoustic offset", color="#cc00cc", alpha=0.8)
    ax.set_ylabel("Water saved/recovered (L/day)")
    ax.set_title("Daily Water Recovery & Savings")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.2, axis="y")

    # bottom-left: net water + temperature overlay
    ax = axes[1, 0]
    net = [m["net_L_day"] for m in months]
    temps = [m["temp_C"] for m in months]
    bars = ax.bar(x, net, width, color="#cc4444", alpha=0.7, label="Net water (L/day)")
    # color frozen months
    for i, m in enumerate(months):
        if m["frozen"]:
            bars[i].set_color("#6699cc")
            bars[i].set_alpha(0.5)
    ax2 = ax.twinx()
    ax2.plot(x, temps, "r-o", linewidth=2, label="Temperature (C)")
    ax2.axhline(y=0, color="blue", linestyle=":", alpha=0.5)
    ax2.set_ylabel("Temperature (C)", color="red")
    ax.set_ylabel("Net water demand (L/day)")
    ax.set_title("Net Daily Water Demand (blue = frozen months)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.grid(True, alpha=0.2, axis="y")

    # bottom-right: annual summary
    ax = axes[1, 1]
    annual_consumption = sum(m["total_consumption_L_day"] * m["days"] for m in months)
    annual_recovery = sum(m["total_recovery_L_day"] * m["days"] for m in months)
    annual_net = sum(m["net_L_month"] for m in months)

    categories = ["Gross\nConsumption", "Recovery +\nTA Offset", "Net\nDemand"]
    values = [annual_consumption / 1000, annual_recovery / 1000, annual_net / 1000]
    colors = ["#cc4444", "#44aa44", "#ff8844"]
    bars = ax.bar(categories, values, color=colors, alpha=0.8, width=0.5)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.02,
                f"{val:,.0f}k L", ha="center", fontsize=10, fontweight="bold")

    # add cost annotation
    annual_cost = (annual_net / LITERS_PER_GALLON) / 1000 * WATER_COST_PER_1000GAL
    ax.text(0.5, 0.85, f"Annual water cost: ${annual_cost:,.0f}",
            transform=ax.transAxes, fontsize=12, fontweight="bold",
            ha="center", bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

    ax.set_ylabel("Volume (thousands of liters / year)")
    ax.set_title("Annual Water Budget Summary")
    ax.grid(True, alpha=0.2, axis="y")

    plt.tight_layout()
    path = os.path.join(outdir, "water_budget.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_effectiveness_calendar(months, outdir):
    """Plot monthly cooling system effectiveness calendar."""
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.suptitle("Cooling System Effectiveness Calendar (Northern MN)",
                 fontsize=14, fontweight="bold")

    labels = [m["month"] for m in months]
    x = np.arange(len(labels))

    evap_eff = [m["evap_effectiveness"] * 100 for m in months]
    free_cool = [100 if m["free_cooling_available"] else 0 for m in months]
    ta_available = [100] * 12  # thermoacoustic works year-round

    ax.fill_between(x, 0, ta_available, alpha=0.15, color="purple",
                     label="Thermoacoustic (year-round)")
    ax.plot(x, evap_eff, "b-o", linewidth=2, markersize=8,
            label="Evaporative cooling effectiveness (%)")
    ax.fill_between(x, 0, free_cool, alpha=0.1, color="cyan",
                     label="Free air cooling available")

    # annotate frozen months
    for i, m in enumerate(months):
        if m["frozen"]:
            ax.axvspan(i - 0.4, i + 0.4, alpha=0.1, color="blue")
            ax.text(i, 5, "FROZEN", ha="center", fontsize=7, color="blue", alpha=0.6)

    ax.set_xlabel("Month")
    ax.set_ylabel("Effectiveness (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 110)
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)

    path = os.path.join(outdir, "cooling_calendar.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Console report
# ---------------------------------------------------------------------------
def print_report(months, capacity_mw, latitude_deg, coriolis_results):
    print("=" * 70)
    print("  NUCLEAR DONUT WATER BUDGET SIMULATION")
    print("=" * 70)

    print(f"\n  Configuration:")
    print(f"    IT capacity:    {capacity_mw} MW")
    print(f"    Location:       Northern Minnesota ({latitude_deg} N)")
    print(f"    Climate data:   Monticello/Prairie Island area averages")

    print(f"\n  Monthly Water Budget (liters/day):")
    print(f"  {'Month':>5} {'Temp':>5} {'Evap':>8} {'Geo':>7} {'Steam':>7} "
          f"{'Cond':>6} {'Dew':>5} {'TA Off':>7} {'NET':>8} {'Status':>10}")
    print("  " + "-" * 80)
    print("  (Status describes the cooling system; * = ground frozen, no geothermal irrigation)")

    annual_consumption = 0
    annual_recovery = 0
    annual_net = 0

    for m in months:
        # `frozen` is a SOIL state (drives geothermal irrigation); evaporative
        # cooling gates on AIR temperature. Reporting the soil flag as the whole
        # system's status made April read as "FROZEN" while evaporating 2,867
        # L/day. Status now describes the cooling system; soil is flagged with
        # a trailing '*'. See run-log entry 9.
        if m["evap_cooling_L_day"] <= 0:
            status = "NO-EVAP"
        elif m["free_cooling_available"]:
            status = "FREE"
        else:
            status = "ACTIVE"
        if m["frozen"]:
            status += "*"
        print(f"  {m['month']:>5} {m['temp_C']:>4.0f}C {m['evap_cooling_L_day']:>8.0f} "
              f"{m['geothermal_L_day']:>7.0f} {m['steam_loss_L_day']:>7.0f} "
              f"{m['condenser_recovery_L_day']:>6.0f} {m['dew_harvest_L_day']:>5.1f} "
              f"{m['thermoacoustic_offset_L_day']:>7.0f} {m['net_L_day']:>8.0f} {status:>10}")
        annual_consumption += m["total_consumption_L_day"] * m["days"]
        annual_recovery += m["total_recovery_L_day"] * m["days"]
        annual_net += m["net_L_month"]

    print(f"\n  Heat Rejection Allocation (kW) — must sum to the total load:")
    print(f"  {'Month':>5} {'Total':>8} {'Free':>8} {'ThAc':>7} {'Geo':>6} {'Evap':>8} {'Free %':>7}")
    print("  " + "-" * 54)
    for m in months:
        print(f"  {m['month']:>5} {m['q_total_kw']:>8.0f} {m['q_free_kw']:>8.0f} "
              f"{m['q_thermoacoustic_kw']:>7.0f} {m['q_geothermal_kw']:>6.0f} "
              f"{m['q_evaporative_kw']:>8.0f} {m['q_free_kw']/m['q_total_kw']*100:>6.0f}%")

    print(f"\n  Annual Summary:")
    print(f"    Total consumption:      {annual_consumption:>12,.0f} L/year ({annual_consumption / LITERS_PER_GALLON:,.0f} gal)")
    print(f"    Total recovery:         {annual_recovery:>12,.0f} L/year")
    print(f"    Net demand:             {annual_net:>12,.0f} L/year ({annual_net / LITERS_PER_GALLON:,.0f} gal)")
    water_cost = (annual_net / LITERS_PER_GALLON) / 1000 * WATER_COST_PER_1000GAL
    print(f"    Estimated water cost:   ${water_cost:>11,.0f} /year")

    print(f"\n  Coriolis Effects on Water Systems:")
    print(f"    Coriolis parameter f:     {coriolis_results['coriolis_parameter_f']:.6f} rad/s")
    print(f"    Condensate deflection:    {coriolis_results['condensate_deflection_mm']:.3f} mm over 5m path")
    print(f"    Geothermal Coriolis/gravity: {coriolis_results['geothermal_coriolis_vs_gravity_pct']:.5f}%")
    print(f"    Pipe secondary flow:      {coriolis_results['pipe_secondary_velocity_mm_s']:.4f} mm/s")
    print(f"    Cooling spray deflection: {coriolis_results['spray_deflection_mm']:.4f} mm")

    cor_signif = coriolis_results["geothermal_coriolis_vs_gravity_pct"]
    if cor_signif < 0.01:
        print(f"\n    Assessment: Coriolis effects on water are NEGLIGIBLE at building scale.")
        print(f"    However: In the 600m+ geothermal loop network, cumulative Coriolis")
        print(f"    creates a consistent flow bias that affects:")
        print(f"      - Heat exchanger efficiency (asymmetric flow distribution)")
        print(f"      - Condensate collection (predictable drainage direction)")
        print(f"      - Can be EXPLOITED by aligning spiral duct rotation")
        print(f"        with Coriolis-preferred direction (clockwise in Northern Hemisphere)")
    else:
        print(f"\n    Assessment: Coriolis effects are measurable and should be")
        print(f"    incorporated into geothermal loop and duct design.")

    print(f"\n  Key Findings:")
    peak_month = max(months, key=lambda m: m["net_L_day"])
    print(f"    Peak water month:       {peak_month['month']} ({peak_month['net_L_day']:,.0f} L/day)")
    zero_months = [m["month"] for m in months if m["net_L_day"] < 100]
    print(f"    Near-zero water months: {len(zero_months)} ({', '.join(zero_months) or 'none'})")
    dry_months = [m["month"] for m in months if m["q_evaporative_kw"] <= 0]
    print(f"    Fully dry-cooled months: {len(dry_months)} ({', '.join(dry_months) or 'none'})")

    ta_savings = sum(m["thermoacoustic_offset_L_day"] * m["days"] for m in months)
    ta_pct = ta_savings / annual_consumption * 100 if annual_consumption > 0 else 0
    print(f"    Thermoacoustic water avoided: {ta_savings:,.0f} L/year ({ta_pct:.1f}% of gross)")

    kwh_year = capacity_mw * 1000 * 24 * 365
    print(f"    WUE (net):              {annual_net / kwh_year:.3f} L/kWh")
    print(f"    WUE (gross):            {annual_consumption / kwh_year:.3f} L/kWh")
    print(f"      reference: 1.55-2.5 L/kWh for evaporatively-cooled facilities,")
    print(f"      1.8-1.9 industry average, 0.3-0.7 best-in-class.")

    worst = min(months, key=lambda m: m["wetbulb_margin_K"])
    print(f"    Tightest wet-bulb margin: {worst['month']} "
          f"({worst['wetbulb_margin_K']:+.1f} K)")
    if worst["wetbulb_margin_K"] < 0:
        print(f"      ^ INFEASIBLE: tower cannot reach its approach temperature.")

    print(f"\n  Charts saved to sim_output/")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Donut water budget simulation")
    parser.add_argument("--capacity-mw", type=float, default=1.0,
                        help="IT capacity in MW (default: 1)")
    parser.add_argument("--latitude", type=float, default=46.5,
                        help="Site latitude degrees N (default: 46.5)")
    parser.add_argument("--pipe-length", type=float, default=600.0,
                        help="Geothermal pipe length in meters (default: 600)")
    parser.add_argument("--thermoacoustic-kw", type=float, default=160.0,
                        help="Thermoacoustic cooling capacity in kW (default: 160)")
    parser.add_argument("--open-loop-steam", action="store_true",
                        help="Model open-loop steam (higher losses)")
    parser.add_argument("--supply-temp-c", type=float, default=32.0,
                        help="Facility water supply temp in C. ASHRAE W3 allows "
                             "32, W4 allows 45. Higher = more free cooling "
                             "(default: 32)")
    parser.add_argument("--cycles-of-concentration", type=float, default=4.0,
                        help="Cooling tower CoC; blowdown = evaporation/(CoC-1). "
                             "Typical operating band is 4-6 (default: 4)")
    parser.add_argument("--geo-w-per-m", type=float, default=40.0,
                        help="Ground loop heat exchange, W per metre of pipe. "
                             "Field practice 25-50 (default: 40)")
    args = parser.parse_args()

    outdir = ensure_output_dir()

    # compute budget
    months = compute_monthly_budget(
        args.capacity_mw, args.thermoacoustic_kw, args.pipe_length,
        args.open_loop_steam,
        supply_temp_C=args.supply_temp_c,
        cycles_of_concentration=args.cycles_of_concentration,
        geo_w_per_m=args.geo_w_per_m,
    )

    # energy balance must close before any water number is believable
    imbalance = energy_balance_check(months)
    if imbalance:
        print("ENERGY BALANCE FAILED — heat allocation does not sum to load:")
        for mon, diff in imbalance:
            print(f"    {mon}: {diff:+.6f} kW unaccounted")
        sys.exit(1)

    # Coriolis analysis
    coriolis = coriolis_water_analysis(args.latitude)

    # plots
    plot_water_budget(months, args.capacity_mw, outdir)
    plot_effectiveness_calendar(months, outdir)
    plot_coriolis_water(args.latitude, outdir)

    # report
    print_report(months, args.capacity_mw, args.latitude, coriolis)


if __name__ == "__main__":
    main()

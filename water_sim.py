#!/usr/bin/env python3
"""
Nuclear Donut Data Center — Water Budget & Coriolis Simulation

Models:
  1. Monthly evaporative cooling water consumption (Northern MN climate)
  2. Condensate recovery (spiral condenser + dew harvester)
  3. Geothermal soil moisture water demand
  4. Steam loop losses
  5. Thermoacoustic cooling offset (zero-water cooling credit)
  6. Net water budget — monthly and annual
  7. Coriolis effects on water/condensate drainage and geothermal flow
  8. Cost analysis — water cost vs. energy savings

Usage:
  python3 water_sim.py [--capacity-mw 1] [--latitude 46.5]

Outputs PNG charts to ./sim_output/
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
# 1. Evaporative cooling water consumption
# ---------------------------------------------------------------------------
def evaporative_water(capacity_mw, month_idx):
    """
    Estimate evaporative cooling water consumption (liters/day).

    Evaporative cooling is effective when:
    - Temperature > 5 C (not frozen)
    - Humidity < 70% (wet bulb depression sufficient)

    Water use = heat_rejected / latent_heat_of_evaporation
    Effectiveness drops with higher humidity.
    """
    T_db = TEMP_DB_C[month_idx]
    T_wb = TEMP_WB_C[month_idx]
    rh = RH_PCT[month_idx]

    # evaporative cooling not feasible below ~5 C or if water freezes
    if T_db < 5:
        return 0.0, 0.0  # (liters/day, effectiveness)

    # wet-bulb depression determines effectiveness
    wb_depression = T_db - T_wb
    # effectiveness: 0 at 0K depression, ~0.85 at 10K+ depression
    effectiveness = min(0.85, wb_depression / 12.0)

    # high humidity reduces effectiveness further
    if rh > 60:
        humidity_penalty = 1.0 - (rh - 60) / 80.0  # linear reduction
        effectiveness *= max(0.2, humidity_penalty)

    # heat to reject via evaporative cooling (kW)
    # assume ~30% of IT load needs active cooling (rest handled by other systems)
    heat_to_reject_kw = capacity_mw * 1000 * 0.30 * effectiveness

    # water consumption: Q = m * L_v  =>  m = Q / L_v
    water_kg_per_second = (heat_to_reject_kw * 1000) / LATENT_HEAT_EVAP
    water_liters_per_day = water_kg_per_second * 86400

    return water_liters_per_day, effectiveness


# ---------------------------------------------------------------------------
# 2. Condensate recovery
# ---------------------------------------------------------------------------
def condensate_recovery(capacity_mw, month_idx, condenser_area_m2=20.0,
                        dew_harvest_area_m2=4.0):
    """
    Estimate water recovery from spiral condenser and dew harvester.

    Condenser: recovers a fraction of evaporated water from exhaust air.
    Dew harvester: collects ambient moisture (climate-dependent).
    """
    T_db = TEMP_DB_C[month_idx]
    rh = RH_PCT[month_idx]

    # condenser recovery: depends on how much water was evaporated
    evap_water, _ = evaporative_water(capacity_mw, month_idx)
    # condenser can recover 5-15% of evaporated water
    # higher recovery in cooler months (larger temperature differential to condense)
    if T_db < 5:
        condenser_recovery_pct = 0.0
    elif T_db < 15:
        condenser_recovery_pct = 0.15  # cooler = better condensation
    else:
        condenser_recovery_pct = 0.08  # warmer = harder to condense

    condenser_liters = evap_water * condenser_recovery_pct

    # dew harvester: 0.1-0.8 L/m²/night depending on climate
    if T_db < 0:
        dew_rate = 0.0  # frozen, no dew
    elif rh > 70:
        dew_rate = 0.5  # high humidity = good dew
    elif rh > 50:
        dew_rate = 0.2
    else:
        dew_rate = 0.05

    dew_liters = dew_rate * dew_harvest_area_m2  # per day

    return condenser_liters, dew_liters


# ---------------------------------------------------------------------------
# 3. Geothermal soil moisture
# ---------------------------------------------------------------------------
def geothermal_water(pipe_length_m=600, month_idx=0):
    """
    Estimate water needed to maintain soil moisture around geothermal coils.

    Dry soil: 0.25 W/m·K, moist soil: 1.5-2.0 W/m·K.
    Need ~2-5 liters per meter of pipe per month in active season.
    """
    if GROUND_FROZEN[month_idx]:
        # frozen ground: no irrigation possible, but frozen soil
        # has reasonable conductivity (~2.0 W/m·K), so not needed
        return 0.0

    # growing season: soil dries out, needs irrigation
    T_db = TEMP_DB_C[month_idx]
    rh = RH_PCT[month_idx]

    # hotter + drier = more water needed
    base_rate = 3.0  # liters per meter per month (baseline)
    temp_factor = max(0.5, min(2.0, T_db / 15.0))
    humidity_factor = max(0.5, min(1.5, (100 - rh) / 40.0))

    liters_per_month = pipe_length_m * base_rate * temp_factor * humidity_factor
    liters_per_day = liters_per_month / DAYS[month_idx]

    return liters_per_day


# ---------------------------------------------------------------------------
# 4. Steam loop losses
# ---------------------------------------------------------------------------
def steam_losses(capacity_mw, is_open_loop=False):
    """
    Estimate steam loop water losses (liters/day).

    Closed loop: 1-3% losses from blowdown, leaks, traps.
    Open loop (steam vented for cooling): much higher.
    """
    # steam flow for 1 MW thermal: ~1500 kg/hr (rough estimate)
    steam_flow_kg_hr = capacity_mw * 1500

    if is_open_loop:
        # significant losses: 10-20% of flow
        loss_fraction = 0.15
    else:
        # closed loop: 1-3% losses
        loss_fraction = 0.02

    loss_kg_per_day = steam_flow_kg_hr * 24 * loss_fraction
    loss_liters_per_day = loss_kg_per_day  # 1 kg water ≈ 1 liter

    return loss_liters_per_day


# ---------------------------------------------------------------------------
# 5. Thermoacoustic cooling offset
# ---------------------------------------------------------------------------
def thermoacoustic_offset(capacity_mw, thermoacoustic_kw=160):
    """
    Calculate how much evaporative water is saved by thermoacoustic cooling.

    thermoacoustic_kw of cooling = that much less evaporative cooling needed.
    Returns liters/day of water SAVED.
    """
    # water that would be needed to provide thermoacoustic_kw of evap cooling
    water_kg_per_second = (thermoacoustic_kw * 1000) / LATENT_HEAT_EVAP
    water_liters_per_day = water_kg_per_second * 86400

    return water_liters_per_day


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
                           open_loop_steam):
    """Compute monthly water budget for all systems."""
    months = []
    for i in range(12):
        evap, eff = evaporative_water(capacity_mw, i)
        cond, dew = condensate_recovery(capacity_mw, i)
        geo = geothermal_water(pipe_length_m, i)
        steam = steam_losses(capacity_mw, open_loop_steam)
        ta_offset = thermoacoustic_offset(capacity_mw, thermoacoustic_kw) if evap > 0 else 0

        # net water per day
        consumption = evap + geo + steam
        recovery = cond + dew + ta_offset
        net_per_day = consumption - recovery

        months.append({
            "month": MONTHS[i],
            "days": DAYS[i],
            "evap_cooling_L_day": evap,
            "evap_effectiveness": eff,
            "condenser_recovery_L_day": cond,
            "dew_harvest_L_day": dew,
            "geothermal_L_day": geo,
            "steam_loss_L_day": steam,
            "thermoacoustic_offset_L_day": ta_offset,
            "total_consumption_L_day": consumption,
            "total_recovery_L_day": recovery + ta_offset,
            "net_L_day": max(0, net_per_day),
            "net_L_month": max(0, net_per_day) * DAYS[i],
            "temp_C": TEMP_DB_C[i],
            "frozen": GROUND_FROZEN[i],
            "free_cooling_available": TEMP_DB_C[i] < 15,
        })

    return months


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
    water_cost_per_1000gal = 5.50  # USD
    liters_per_gallon = 3.785
    annual_cost = (annual_net / liters_per_gallon) / 1000 * water_cost_per_1000gal
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

    annual_consumption = 0
    annual_recovery = 0
    annual_net = 0

    for m in months:
        status = "FROZEN" if m["frozen"] else ("FREE" if m["free_cooling_available"] else "ACTIVE")
        print(f"  {m['month']:>5} {m['temp_C']:>4.0f}C {m['evap_cooling_L_day']:>8.0f} "
              f"{m['geothermal_L_day']:>7.0f} {m['steam_loss_L_day']:>7.0f} "
              f"{m['condenser_recovery_L_day']:>6.0f} {m['dew_harvest_L_day']:>5.1f} "
              f"{m['thermoacoustic_offset_L_day']:>7.0f} {m['net_L_day']:>8.0f} {status:>10}")
        annual_consumption += m["total_consumption_L_day"] * m["days"]
        annual_recovery += m["total_recovery_L_day"] * m["days"]
        annual_net += m["net_L_month"]

    print(f"\n  Annual Summary:")
    print(f"    Total consumption:      {annual_consumption:>12,.0f} L/year ({annual_consumption / 3785:,.0f} gal)")
    print(f"    Total recovery + offset:{annual_recovery:>12,.0f} L/year")
    print(f"    Net demand:             {annual_net:>12,.0f} L/year ({annual_net / 3785:,.0f} gal)")
    water_cost = (annual_net / 3785) / 1000 * 5.50
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
    zero_months = sum(1 for m in months if m["net_L_day"] < 100)
    print(f"    Near-zero water months: {zero_months} (frozen + free cooling)")
    ta_savings = sum(m["thermoacoustic_offset_L_day"] * m["days"] for m in months)
    print(f"    Thermoacoustic savings: {ta_savings:,.0f} L/year ({ta_savings / annual_consumption * 100 if annual_consumption > 0 else 0:.1f}% of gross)")

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
    args = parser.parse_args()

    outdir = ensure_output_dir()

    # compute budget
    months = compute_monthly_budget(
        args.capacity_mw, args.thermoacoustic_kw, args.pipe_length,
        args.open_loop_steam,
    )

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

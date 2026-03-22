#!/usr/bin/env python3
"""
Nuclear Donut Data Center — Harmonic & Thermoacoustic Simulation

Models:
  1. Resonant modes of the toroidal cavity (circumferential + radial)
  2. Standing wave pressure field — node/antinode map
  3. Thermoacoustic engine performance (radial channels)
  4. Coriolis deflection of radial airflow inside the donut
  5. Node/antinode placement strategy for servers vs. harvesters

Usage:
  python3 harmonic_sim.py [--radius 10] [--ring-width 4.5] [--latitude 46.5]

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
from matplotlib.patches import Circle, Wedge
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
C_SOUND = 343.0          # speed of sound in air (m/s)
RHO_AIR = 1.2            # air density (kg/m³)
EARTH_OMEGA = 7.2921e-5  # Earth rotation rate (rad/s)
P_ATM = 101325.0         # atmospheric pressure (Pa)


def ensure_output_dir(path="sim_output"):
    os.makedirs(path, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# 1. Resonant mode analysis
# ---------------------------------------------------------------------------
def resonant_modes(R_mean, ring_width, n_modes=30):
    """Compute circumferential and radial resonant frequencies."""
    circumference = 2 * math.pi * R_mean

    circ = []
    for n in range(1, n_modes + 1):
        wavelength = circumference / n
        freq = C_SOUND / wavelength
        node_spacing = circumference / (2 * n)
        circ.append({
            "mode": n,
            "wavelength_m": wavelength,
            "frequency_hz": freq,
            "node_spacing_m": node_spacing,
            "num_nodes": 2 * n,
        })

    radial = []
    for m in range(1, n_modes + 1):
        # quarter-wave resonance (closed at core, open at edge)
        wavelength = 4 * ring_width / (2 * m - 1)
        freq = C_SOUND / wavelength
        radial.append({
            "mode": m,
            "wavelength_m": wavelength,
            "frequency_hz": freq,
        })

    return circ, radial


def plot_mode_frequencies(circ, radial, outdir):
    """Plot circumferential and radial mode frequencies."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("Donut Cavity Resonant Modes", fontsize=14, fontweight="bold")

    modes_c = [m["mode"] for m in circ]
    freqs_c = [m["frequency_hz"] for m in circ]
    ax1.bar(modes_c, freqs_c, color="#00aa44", alpha=0.8)
    ax1.set_xlabel("Circumferential mode number (n)")
    ax1.set_ylabel("Frequency (Hz)")
    ax1.set_title("Circumferential Modes")
    ax1.axhline(y=20, color="red", linestyle="--", alpha=0.5, label="20 Hz (hearing threshold)")
    ax1.axhline(y=20000, color="orange", linestyle="--", alpha=0.5, label="20 kHz (upper hearing)")
    ax1.legend(fontsize=8)

    modes_r = [m["mode"] for m in radial]
    freqs_r = [m["frequency_hz"] for m in radial]
    ax2.bar(modes_r, freqs_r, color="#cc4400", alpha=0.8)
    ax2.set_xlabel("Radial mode number (m)")
    ax2.set_ylabel("Frequency (Hz)")
    ax2.set_title("Radial Modes (quarter-wave)")

    plt.tight_layout()
    path = os.path.join(outdir, "resonant_modes.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# 2. Standing wave pressure field
# ---------------------------------------------------------------------------
def standing_wave_field(R_inner, R_outer, circ_mode_n=8, radial_mode_m=3,
                        resolution=500):
    """Compute 2D pressure field for combined circumferential + radial mode."""
    theta = np.linspace(0, 2 * math.pi, resolution)
    r = np.linspace(R_inner, R_outer, resolution)
    T, R = np.meshgrid(theta, r)

    # circumferential standing wave: cos(n * theta)
    p_circ = np.cos(circ_mode_n * T)

    # radial standing wave: cos((2m-1) * pi * (r - R_inner) / (2 * (R_outer - R_inner)))
    radial_arg = (2 * radial_mode_m - 1) * math.pi * (R - R_inner) / (2 * (R_outer - R_inner))
    p_radial = np.cos(radial_arg)

    # combined pressure field (product of modes)
    p_total = p_circ * p_radial

    return T, R, p_total


def plot_pressure_field(T, R, p_total, circ_n, radial_m, outdir):
    """Plot the standing wave pressure field in polar coordinates."""
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={"projection": "polar"})
    fig.suptitle(
        f"Standing Wave Pressure Field\n"
        f"Circumferential mode n={circ_n}, Radial mode m={radial_m}",
        fontsize=13, fontweight="bold", y=1.02,
    )

    cmap = plt.cm.RdBu_r
    c = ax.pcolormesh(T, R, p_total, cmap=cmap, shading="auto", vmin=-1, vmax=1)
    fig.colorbar(c, ax=ax, label="Normalized pressure (red=antinode, blue=antinode, white=node)", pad=0.1)

    ax.set_title("")
    ax.set_rticks([])

    path = os.path.join(outdir, "pressure_field.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# 3. Node/antinode placement map
# ---------------------------------------------------------------------------
def plot_placement_map(R_inner, R_outer, R_mean, circ_mode_n, outdir):
    """Show server (node) vs harvester (antinode) placement around the ring."""
    fig, ax = plt.subplots(figsize=(10, 10))
    fig.suptitle(
        f"Server vs Harvester Placement (mode n={circ_mode_n})",
        fontsize=14, fontweight="bold",
    )

    # draw the donut outline
    outer_circle = Circle((0, 0), R_outer, fill=False, edgecolor="#333", linewidth=2)
    inner_circle = Circle((0, 0), R_inner, fill=False, edgecolor="#333", linewidth=2)
    core = Circle((0, 0), R_inner * 0.6, color="#cc0000", alpha=0.3, label="Reactor core")
    ax.add_patch(outer_circle)
    ax.add_patch(inner_circle)
    ax.add_patch(core)

    n_positions = 2 * circ_mode_n
    for i in range(n_positions):
        angle = 2 * math.pi * i / n_positions
        is_node = (i % 2 == 0)

        # wedge from inner to outer radius
        angle_deg = math.degrees(angle)
        wedge_width = 360 / n_positions * 0.8
        wedge = Wedge(
            (0, 0), R_outer, angle_deg - wedge_width / 2, angle_deg + wedge_width / 2,
            width=R_outer - R_inner,
            facecolor="#0066cc" if is_node else "#ff6600",
            alpha=0.4,
            edgecolor="white",
        )
        ax.add_patch(wedge)

        # label
        label_r = R_mean
        lx = label_r * math.cos(angle)
        ly = label_r * math.sin(angle)
        text = "SRV" if is_node else "HAR"
        ax.text(lx, ly, text, ha="center", va="center", fontsize=7, fontweight="bold",
                color="#003399" if is_node else "#993300")

    ax.set_xlim(-R_outer * 1.15, R_outer * 1.15)
    ax.set_ylim(-R_outer * 1.15, R_outer * 1.15)
    ax.set_aspect("equal")
    ax.legend(
        handles=[
            plt.Rectangle((0, 0), 1, 1, fc="#0066cc", alpha=0.4, label="Server (pressure node — quiet)"),
            plt.Rectangle((0, 0), 1, 1, fc="#ff6600", alpha=0.4, label="Harvester (pressure antinode — max energy)"),
            core,
        ],
        loc="upper right", fontsize=9,
    )
    ax.set_title(f"{circ_mode_n} nodes + {circ_mode_n} antinodes around circumference", fontsize=11)
    ax.axis("off")

    path = os.path.join(outdir, "placement_map.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# 4. Thermoacoustic engine performance
# ---------------------------------------------------------------------------
def thermoacoustic_performance(T_hot_C, T_cold_C, n_channels=10):
    """Estimate thermoacoustic engine output for radial channels."""
    T_hot_K = T_hot_C + 273.15
    T_cold_K = T_cold_C + 273.15

    carnot_eff = 1 - T_cold_K / T_hot_K

    # standing-wave: 15-25% of Carnot
    sw_low = carnot_eff * 0.15
    sw_high = carnot_eff * 0.25

    # travelling-wave: 30-50% of Carnot
    tw_low = carnot_eff * 0.30
    tw_high = carnot_eff * 0.50

    # per-channel acoustic power estimate (kW)
    # based on Backhaus-Swift scaling: ~710W from a 30cm device
    # scaled to meter-scale channels: 2-15 kW per channel
    per_channel_low_kw = 2.0
    per_channel_high_kw = 15.0

    total_acoustic_low = n_channels * per_channel_low_kw
    total_acoustic_high = n_channels * per_channel_high_kw

    # linear alternator: 80% efficiency
    alternator_eff = 0.80
    electric_low = total_acoustic_low * alternator_eff
    electric_high = total_acoustic_high * alternator_eff

    # thermoacoustic refrigeration: COP 2.0
    cop = 2.0
    cooling_low = total_acoustic_low * cop
    cooling_high = total_acoustic_high * cop

    return {
        "T_hot_C": T_hot_C,
        "T_cold_C": T_cold_C,
        "carnot_eff": carnot_eff,
        "standing_wave_eff": (sw_low, sw_high),
        "travelling_wave_eff": (tw_low, tw_high),
        "n_channels": n_channels,
        "acoustic_power_kw": (total_acoustic_low, total_acoustic_high),
        "electric_output_kw": (electric_low, electric_high),
        "cooling_capacity_kw": (cooling_low, cooling_high),
    }


def plot_thermoacoustic(perf, outdir):
    """Plot thermoacoustic system performance across temperature range."""
    T_hots = np.arange(150, 550, 25)
    T_cold = perf["T_cold_C"]
    n_ch = perf["n_channels"]

    carnots = []
    tw_effs = []
    acoustics_lo = []
    acoustics_hi = []
    electrics_lo = []
    electrics_hi = []
    coolings_lo = []
    coolings_hi = []

    for T_h in T_hots:
        p = thermoacoustic_performance(T_h, T_cold, n_ch)
        carnots.append(p["carnot_eff"] * 100)
        tw_effs.append(p["travelling_wave_eff"][1] * 100)
        acoustics_lo.append(p["acoustic_power_kw"][0])
        acoustics_hi.append(p["acoustic_power_kw"][1])
        electrics_lo.append(p["electric_output_kw"][0])
        electrics_hi.append(p["electric_output_kw"][1])
        coolings_lo.append(p["cooling_capacity_kw"][0])
        coolings_hi.append(p["cooling_capacity_kw"][1])

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        f"Thermoacoustic System Performance ({n_ch} radial channels, T_cold={T_cold} C)",
        fontsize=14, fontweight="bold",
    )

    # efficiency
    ax = axes[0, 0]
    ax.plot(T_hots, carnots, "r-", linewidth=2, label="Carnot limit")
    ax.plot(T_hots, tw_effs, "g-", linewidth=2, label="Travelling-wave (50% Carnot)")
    ax.fill_between(T_hots, [c * 0.15 / 0.5 for c in tw_effs],
                     tw_effs, alpha=0.2, color="green", label="SW-TW range")
    ax.set_xlabel("Hot side temperature (C)")
    ax.set_ylabel("Efficiency (%)")
    ax.set_title("Thermal-to-Acoustic Efficiency")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # acoustic power
    ax = axes[0, 1]
    ax.fill_between(T_hots, acoustics_lo, acoustics_hi, alpha=0.3, color="orange")
    ax.plot(T_hots, acoustics_lo, "o-", color="orange", markersize=3, label="Low estimate")
    ax.plot(T_hots, acoustics_hi, "s-", color="red", markersize=3, label="High estimate")
    ax.set_xlabel("Hot side temperature (C)")
    ax.set_ylabel("Acoustic power (kW)")
    ax.set_title("Total Acoustic Power Output")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # electric output
    ax = axes[1, 0]
    ax.fill_between(T_hots, electrics_lo, electrics_hi, alpha=0.3, color="blue")
    ax.plot(T_hots, electrics_lo, "o-", color="blue", markersize=3, label="Low (80% alternator eff)")
    ax.plot(T_hots, electrics_hi, "s-", color="navy", markersize=3, label="High (80% alternator eff)")
    ax.set_xlabel("Hot side temperature (C)")
    ax.set_ylabel("Electric output (kW)")
    ax.set_title("Electrical Generation via Linear Alternators")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # cooling capacity
    ax = axes[1, 1]
    ax.fill_between(T_hots, coolings_lo, coolings_hi, alpha=0.3, color="cyan")
    ax.plot(T_hots, coolings_lo, "o-", color="teal", markersize=3, label="Low (COP=2)")
    ax.plot(T_hots, coolings_hi, "s-", color="darkcyan", markersize=3, label="High (COP=2)")
    ax.set_xlabel("Hot side temperature (C)")
    ax.set_ylabel("Cooling capacity (kW)")
    ax.set_title("Thermoacoustic Refrigeration Capacity")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(outdir, "thermoacoustic_performance.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# 5. Coriolis deflection on radial airflow
# ---------------------------------------------------------------------------
def coriolis_deflection(latitude_deg, R_inner, R_outer, v_radial=5.0, n_points=200):
    """
    Compute Coriolis deflection of radial airflow from core to outer wall.

    In the Northern Hemisphere, Coriolis deflects moving air to the RIGHT
    of its direction of travel. For outward radial flow, this creates a
    clockwise spiral bias.

    Returns arrays of (r, theta_deflection, tangential_velocity).
    """
    lat_rad = math.radians(latitude_deg)
    f = 2 * EARTH_OMEGA * math.sin(lat_rad)  # Coriolis parameter

    r_vals = np.linspace(R_inner, R_outer, n_points)
    dr = (R_outer - R_inner) / n_points

    # time for air to travel from R_inner to each r at constant radial velocity
    dt_per_step = dr / v_radial
    t_vals = np.cumsum(np.full(n_points, dt_per_step))

    # Coriolis tangential acceleration: a_t = -f * v_radial (rightward deflection)
    # tangential velocity accumulates: v_t = -f * v_radial * t
    v_tangential = -f * v_radial * t_vals

    # angular deflection: integrate v_tangential / r over time
    theta_deflection = np.cumsum(v_tangential / r_vals * dt_per_step)

    return r_vals, theta_deflection, v_tangential


def plot_coriolis_airflow(R_inner, R_outer, latitude_deg, outdir):
    """Plot Coriolis deflection of radial airflow across the donut."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle(
        f"Coriolis Effect on Radial Airflow (latitude {latitude_deg} N)",
        fontsize=14, fontweight="bold",
    )

    velocities = [2.0, 5.0, 10.0]
    colors = ["#0066cc", "#cc6600", "#cc0044"]

    # left panel: deflection angle vs radius
    ax = axes[0]
    for v, color in zip(velocities, colors):
        r, theta, vt = coriolis_deflection(latitude_deg, R_inner, R_outer, v)
        ax.plot(r, np.degrees(theta), color=color, linewidth=2, label=f"v_radial = {v} m/s")
    ax.set_xlabel("Radius from center (m)")
    ax.set_ylabel("Angular deflection (degrees)")
    ax.set_title("Cumulative Coriolis Deflection")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # middle panel: tangential velocity acquired
    ax = axes[1]
    for v, color in zip(velocities, colors):
        r, theta, vt = coriolis_deflection(latitude_deg, R_inner, R_outer, v)
        ax.plot(r, vt * 100, color=color, linewidth=2, label=f"v_radial = {v} m/s")
    ax.set_xlabel("Radius from center (m)")
    ax.set_ylabel("Tangential velocity (cm/s)")
    ax.set_title("Acquired Tangential Velocity")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # right panel: flow path in polar view
    ax = axes[2]
    ax.set_aspect("equal")
    # draw donut outline
    theta_outline = np.linspace(0, 2 * math.pi, 200)
    ax.plot(R_outer * np.cos(theta_outline), R_outer * np.sin(theta_outline), "k-", linewidth=1.5)
    ax.plot(R_inner * np.cos(theta_outline), R_inner * np.sin(theta_outline), "k-", linewidth=1.5)

    # draw flow paths from multiple starting angles
    n_paths = 12
    for i in range(n_paths):
        start_angle = 2 * math.pi * i / n_paths
        r, theta_def, _ = coriolis_deflection(latitude_deg, R_inner, R_outer, 5.0)
        angles = start_angle + theta_def
        x = r * np.cos(angles)
        y = r * np.sin(angles)
        ax.plot(x, y, color="#cc6600", linewidth=1.5, alpha=0.7)
        # arrow at end
        ax.annotate("", xy=(x[-1], y[-1]), xytext=(x[-5], y[-5]),
                     arrowprops=dict(arrowstyle="->", color="#cc6600", lw=1.5))

    # draw straight radial lines for comparison (no Coriolis)
    for i in range(n_paths):
        angle = 2 * math.pi * i / n_paths
        ax.plot(
            [R_inner * math.cos(angle), R_outer * math.cos(angle)],
            [R_inner * math.sin(angle), R_outer * math.sin(angle)],
            "b--", linewidth=0.8, alpha=0.3,
        )

    ax.set_title("Flow Paths (orange=Coriolis, blue dashed=straight)")
    ax.axis("off")

    plt.tight_layout()
    path = os.path.join(outdir, "coriolis_airflow.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Console report
# ---------------------------------------------------------------------------
def print_report(R_mean, ring_width, R_inner, R_outer, circ, radial, perf,
                 latitude_deg):
    print("=" * 70)
    print("  NUCLEAR DONUT HARMONIC & THERMOACOUSTIC SIMULATION")
    print("=" * 70)

    print(f"\n  Geometry:")
    print(f"    Mean radius:      {R_mean:.1f} m")
    print(f"    Inner radius:     {R_inner:.1f} m")
    print(f"    Outer radius:     {R_outer:.1f} m")
    print(f"    Ring width:       {ring_width:.1f} m")
    print(f"    Circumference:    {2 * math.pi * R_mean:.1f} m")

    print(f"\n  Circumferential Modes (first 10):")
    print(f"    {'Mode':>4}  {'Freq (Hz)':>10}  {'Wavelength (m)':>15}  {'Node spacing (m)':>17}  {'Nodes':>5}")
    for m in circ[:10]:
        print(f"    {m['mode']:4d}  {m['frequency_hz']:10.1f}  {m['wavelength_m']:15.2f}  {m['node_spacing_m']:17.2f}  {m['num_nodes']:5d}")

    print(f"\n  Radial Modes (first 10):")
    print(f"    {'Mode':>4}  {'Freq (Hz)':>10}  {'Wavelength (m)':>15}")
    for m in radial[:10]:
        print(f"    {m['mode']:4d}  {m['frequency_hz']:10.1f}  {m['wavelength_m']:15.2f}")

    print(f"\n  Thermoacoustic Performance:")
    print(f"    Hot side:         {perf['T_hot_C']} C")
    print(f"    Cold side:        {perf['T_cold_C']} C")
    print(f"    Carnot limit:     {perf['carnot_eff'] * 100:.1f}%")
    print(f"    TW efficiency:    {perf['travelling_wave_eff'][0] * 100:.1f} - {perf['travelling_wave_eff'][1] * 100:.1f}%")
    print(f"    Channels:         {perf['n_channels']}")
    print(f"    Acoustic power:   {perf['acoustic_power_kw'][0]:.0f} - {perf['acoustic_power_kw'][1]:.0f} kW")
    print(f"    Electric output:  {perf['electric_output_kw'][0]:.0f} - {perf['electric_output_kw'][1]:.0f} kW")
    print(f"    Cooling capacity: {perf['cooling_capacity_kw'][0]:.0f} - {perf['cooling_capacity_kw'][1]:.0f} kW")

    # Coriolis summary
    r, theta, vt = coriolis_deflection(latitude_deg, R_inner, R_outer, 5.0)
    print(f"\n  Coriolis Effect (latitude {latitude_deg} N, v_radial=5 m/s):")
    print(f"    Coriolis parameter f:  {2 * EARTH_OMEGA * math.sin(math.radians(latitude_deg)):.6f} rad/s")
    print(f"    Total angular deflection: {math.degrees(theta[-1]):.4f} degrees")
    print(f"    Tangential velocity at outer wall: {vt[-1] * 100:.2f} cm/s")
    print(f"    Direction: Clockwise spiral (Northern Hemisphere)")
    coriolis_significance = abs(vt[-1]) / 5.0 * 100
    print(f"    Significance: {coriolis_significance:.3f}% of radial velocity")
    if coriolis_significance < 1:
        print(f"    Assessment: MINOR for building-scale airflow — but cumulative")
        print(f"                over many cycles, creates consistent spiral bias")
        print(f"                that can be harnessed for vortex duct alignment")
    else:
        print(f"    Assessment: SIGNIFICANT — should be factored into duct design")

    print(f"\n  Charts saved to sim_output/")
    print("=" * 70)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Donut harmonic simulation")
    parser.add_argument("--radius", type=float, default=10.0,
                        help="Mean donut radius in meters (default: 10)")
    parser.add_argument("--ring-width", type=float, default=4.5,
                        help="Width of server ring in meters (default: 4.5)")
    parser.add_argument("--latitude", type=float, default=46.5,
                        help="Site latitude in degrees N (default: 46.5 for northern MN)")
    parser.add_argument("--t-hot", type=float, default=350.0,
                        help="Reactor hot side temp in C (default: 350)")
    parser.add_argument("--t-cold", type=float, default=30.0,
                        help="Server hall cold side temp in C (default: 30)")
    parser.add_argument("--channels", type=int, default=10,
                        help="Number of radial thermoacoustic channels (default: 10)")
    parser.add_argument("--circ-mode", type=int, default=8,
                        help="Circumferential mode for pressure field plot (default: 8)")
    parser.add_argument("--radial-mode", type=int, default=3,
                        help="Radial mode for pressure field plot (default: 3)")
    args = parser.parse_args()

    R_mean = args.radius
    ring_width = args.ring_width
    R_inner = R_mean - ring_width / 2
    R_outer = R_mean + ring_width / 2

    if R_inner <= 0:
        print(f"Error: inner radius would be {R_inner:.1f} m (negative). Increase --radius or decrease --ring-width.")
        sys.exit(1)

    outdir = ensure_output_dir()

    # 1. Mode analysis
    circ, radial = resonant_modes(R_mean, ring_width)
    p1 = plot_mode_frequencies(circ, radial, outdir)

    # 2. Pressure field
    T, R, p_total = standing_wave_field(R_inner, R_outer, args.circ_mode, args.radial_mode)
    p2 = plot_pressure_field(T, R, p_total, args.circ_mode, args.radial_mode, outdir)

    # 3. Placement map
    p3 = plot_placement_map(R_inner, R_outer, R_mean, args.circ_mode, outdir)

    # 4. Thermoacoustic performance
    perf = thermoacoustic_performance(args.t_hot, args.t_cold, args.channels)
    p4 = plot_thermoacoustic(perf, outdir)

    # 5. Coriolis
    p5 = plot_coriolis_airflow(R_inner, R_outer, args.latitude, outdir)

    # Report
    print_report(R_mean, ring_width, R_inner, R_outer, circ, radial, perf,
                 args.latitude)


if __name__ == "__main__":
    main()

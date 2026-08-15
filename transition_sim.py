#!/usr/bin/env python3
"""
Nuclear Donut Data Center — Transition Possibilities Simulation

Answers three questions that come up once a design changes underneath you:

  1. LEVERAGE     Which small modifications move the design the most per unit
                  of money and effort? Computed by perturbing one parameter at
                  a time against the corrected water model and measuring the
                  result. These numbers are derived, not asserted.

  2. PROPAGATION  When the model changes, what downstream artefacts are now
                  stale? A corrected number is not delivered until everything
                  sized off the old number has been resized.

  3. PATHWAYS     Getting from an unbuilt design to an operating plant needs
                  regulatory and financial steps, not just technical ones.
                  Three staging strategies, scored on time, capital at risk,
                  and the number of gates that can stop you.

Usage:
  python3 transition_sim.py [--capacity-mw 1] [--pathway all]

Outputs PNG charts to ./sim_output/

EPISTEMIC STATUS — read this before quoting anything below.

  Section 1 is COMPUTED. Every water figure comes from running water_sim.py's
  corrected model with one parameter changed. Re-run it and you get the same
  answer.

  The cost and effort figures in section 1, and everything in section 3, are
  DECLARED ASSUMPTIONS. They are order-of-magnitude placeholders chosen to make
  the ranking structure work, and not one of them has been verified against a
  quote, a statute, or a regulator. They are flagged [UNVERIFIED] in the output
  and listed in legacy/run-log.md as open items. The ranking they produce is a
  hypothesis about where leverage lies, not a finding.

  Regulatory durations especially: licensing a reactor is jurisdiction-specific
  and needs actual counsel. The gate CATEGORIES here are real categories; the
  months attached to them are guesses.
"""

import argparse
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import water_sim as W


# ---------------------------------------------------------------------------
# Baseline configuration — matches water_sim.py defaults
# ---------------------------------------------------------------------------
BASELINE = dict(
    thermoacoustic_kw=160.0,
    pipe_length_m=600.0,
    open_loop_steam=False,
    supply_temp_C=32.0,
    cycles_of_concentration=4.0,
    geo_w_per_m=40.0,
    aux_fraction=0.10,
)


# ---------------------------------------------------------------------------
# 1. Levers — small modifications, ranked by computed leverage
# ---------------------------------------------------------------------------
# `capex_usd` and `effort` are DECLARED ASSUMPTIONS. `effort` is a 1-5 scale:
#   1 = setpoint or procedure change      4 = significant construction
#   2 = minor equipment                   5 = redesign or new licence
LEVERS = [
    dict(
        key="supply_temp_C",
        name="Raise supply water 32C -> 45C (ASHRAE W3 -> W4)",
        value=45.0,
        capex_usd=120_000,
        effort=2,
        rationale="Warmer facility water widens the free-cooling band. Mostly a "
                  "setpoint and IT-qualification exercise; the hardware largely "
                  "already tolerates it.",
    ),
    dict(
        key="cycles_of_concentration",
        name="Cooling tower CoC 4 -> 6",
        value=6.0,
        capex_usd=45_000,
        effort=2,
        rationale="Blowdown is evaporation/(CoC-1), so raising CoC cuts makeup "
                  "directly. Needs better water treatment and monitoring.",
    ),
    dict(
        key="thermoacoustic_kw",
        name="Thermoacoustic capacity 160 -> 300 kW",
        value=300.0,
        capex_usd=900_000,
        effort=4,
        rationale="Top of harmonic_sim.py's own 40-300 kW range. Zero-water "
                  "cooling, but the most speculative hardware in the design.",
    ),
    dict(
        key="pipe_length_m",
        name="Geothermal loop 600 -> 1800 m",
        value=1800.0,
        capex_usd=380_000,
        effort=4,
        rationale="Triples ground-loop rejection capacity. Trenching is the "
                  "cost; the physics is well understood.",
    ),
    dict(
        key="aux_fraction",
        name="Cooling auxiliary load 10% -> 6%",
        value=0.06,
        capex_usd=150_000,
        effort=3,
        rationale="EC fans and variable-speed pumps. Less auxiliary power means "
                  "less heat to reject in the first place.",
    ),
    dict(
        key="geo_w_per_m",
        name="Ground loop 40 -> 50 W/m (enhanced grout)",
        value=50.0,
        capex_usd=60_000,
        effort=2,
        rationale="Thermally enhanced grout and tighter borehole spacing, at the "
                  "top of the 25-50 W/m field range.",
    ),
]


def annual_water(capacity_mw, **overrides):
    """Net annual water demand (L/yr) for a given configuration."""
    cfg = dict(BASELINE)
    cfg.update(overrides)
    months = W.compute_monthly_budget(
        capacity_mw,
        cfg["thermoacoustic_kw"],
        cfg["pipe_length_m"],
        cfg["open_loop_steam"],
        supply_temp_C=cfg["supply_temp_C"],
        cycles_of_concentration=cfg["cycles_of_concentration"],
        geo_w_per_m=cfg["geo_w_per_m"],
        aux_fraction=cfg["aux_fraction"],
    )
    imbalance = W.energy_balance_check(months)
    if imbalance:
        raise RuntimeError(f"energy balance failed for {overrides}: {imbalance}")
    net = sum(m["net_L_month"] for m in months)
    gross = sum(m["total_consumption_L_day"] * m["days"] for m in months)
    dry = sum(1 for m in months if m["q_evaporative_kw"] <= 0)
    return net, gross, dry


def evaluate_levers(capacity_mw):
    """Perturb one parameter at a time and measure the result."""
    base_net, base_gross, base_dry = annual_water(capacity_mw)
    kwh_year = capacity_mw * 1000 * 24 * 365

    results = []
    for lever in LEVERS:
        net, gross, dry = annual_water(capacity_mw, **{lever["key"]: lever["value"]})
        saved = base_net - net
        pct = saved / base_net * 100 if base_net else 0.0
        # leverage: litres saved per year, per $1k of capital
        per_1k = saved / (lever["capex_usd"] / 1000.0) if lever["capex_usd"] else 0.0
        results.append(dict(
            lever,
            net_L_year=net,
            saved_L_year=saved,
            saved_pct=pct,
            dry_months=dry,
            dry_delta=dry - base_dry,
            wue=net / kwh_year,
            litres_per_1k_usd=per_1k,
            saved_per_effort=pct / lever["effort"],
        ))

    return base_net, base_gross, base_dry, results


def evaluate_stacked(capacity_mw, results, top_n=3):
    """Apply the top N levers together — leverage is not always additive."""
    ranked = sorted(results, key=lambda r: r["litres_per_1k_usd"], reverse=True)
    chosen = ranked[:top_n]
    overrides = {r["key"]: r["value"] for r in chosen}
    net, gross, dry = annual_water(capacity_mw, **overrides)
    individual_sum = sum(r["saved_L_year"] for r in chosen)
    base_net, _, _ = annual_water(capacity_mw)
    combined = base_net - net
    return chosen, combined, individual_sum, net, dry


# ---------------------------------------------------------------------------
# 2. Propagation — what the model change made stale
# ---------------------------------------------------------------------------
# Each entry is a downstream artefact that was sized, written, or argued using
# the pre-correction water numbers. This is the "active steps from the old
# design to the new" list.
PROPAGATION = [
    dict(
        artefact="1MWDataCenterBOMSim.md",
        depends_on="Water storage, treatment and makeup infrastructure",
        old_basis="108,720 L/yr net demand",
        action="Resize makeup and treatment for the corrected demand. Peak month "
               "now sets the sizing, and it is a summer month, not January.",
        severity="HIGH",
    ),
    dict(
        artefact="Thermoacoustic-harvesting.md",
        depends_on="'Evaporative cooling 7,000-25,000 L/day per MW'",
        old_basis="Contradicted water_sim.py by roughly 5x",
        action="No change needed — this document was RIGHT and the simulation "
               "was wrong. Reconcile the citation direction and note that the "
               "corrected model now agrees with it.",
        severity="RESOLVED",
    ),
    dict(
        artefact="Thermoacoustic-harvesting.md",
        depends_on="'8-24% of cooling load handled with zero water'",
        old_basis="80-240 kW against a 1 MW load",
        action="Corroborated. The corrected model puts the 160 kW path at 22.4% "
               "of gross water avoided, inside the stated band.",
        severity="RESOLVED",
    ),
    dict(
        artefact="README.md economics",
        depends_on="'50-60% operational cost reduction', '$155M over 20 years'",
        old_basis="Never traced to a calculation anywhere in the repo",
        action="Either derive these from the corrected model or mark them as "
               "unsourced. They are the most-quoted numbers in the project and "
               "the least supported.",
        severity="HIGH",
    ),
    dict(
        artefact="Design-concept.md thermal zones",
        depends_on="Cooling tower and duct sizing",
        old_basis="An evaporative load ~10x below the corrected figure",
        action="Re-check duct and tower dimensions against the new peak "
               "evaporative kW, which is now the July residual.",
        severity="MEDIUM",
    ),
    dict(
        artefact="Heat-dissipation-prototype.md",
        depends_on="Desktop rig scaling to the full design",
        old_basis="<0.5 K/W thermal resistance target",
        action="Confirm the target still represents the full-scale duty now "
               "that the rejected heat is 100% of load rather than 7-12%.",
        severity="MEDIUM",
    ),
]


# ---------------------------------------------------------------------------
# 3. Transition pathways — regulatory and financial staging
# ---------------------------------------------------------------------------
# GATE CATEGORIES are real. The month and dollar figures are [UNVERIFIED]
# placeholders. Licensing is jurisdiction-specific and needs actual counsel.
GATE_TYPES = {
    "SITE": "Site suitability / environmental review",
    "CONSTRUCT": "Construction authorisation",
    "OPERATE": "Operating licence",
    "GRID": "Grid interconnection agreement",
    "WATER": "Water appropriation permit",
    "FINANCE": "Financing close",
    "OFFTAKE": "Compute offtake / anchor tenant contract",
}

PATHWAYS = {
    "grid-first": dict(
        label="Grid-first retrofit",
        summary="Build the data centre on grid power inside the exclusion zone. "
                "Add the reactor once the compute business is generating revenue.",
        stages=[
            ("Site control + environmental review", 12, 2_000_000, ["SITE"], False),
            ("Grid interconnect + water permit", 14, 1_500_000, ["GRID", "WATER"], False),
            ("Anchor tenant contract", 6, 0, ["OFFTAKE"], False),
            ("Build 1 MW module (grid powered)", 12, 9_000_000, ["FINANCE"], True),
            ("Operate, bank revenue", 24, 0, [], False),
            ("Reactor licensing", 48, 25_000_000, ["CONSTRUCT", "OPERATE"], False),
            ("Reactor build + cutover", 36, 90_000_000, [], False),
        ],
        reversible=True,
        note="Revenue starts before the hardest gate. If reactor licensing "
             "fails, you still own an operating data centre.",
    ),
    "integrated": dict(
        label="Greenfield integrated",
        summary="License and build reactor and data centre as one project.",
        stages=[
            ("Site control + environmental review", 18, 3_500_000, ["SITE"], False),
            ("Reactor licensing", 54, 30_000_000, ["CONSTRUCT"], False),
            ("Financing close", 12, 0, ["FINANCE"], False),
            ("Water + grid permits", 12, 2_000_000, ["WATER", "GRID"], False),
            ("Integrated build", 42, 130_000_000, [], False),
            ("Commissioning + operating licence", 12, 8_000_000, ["OPERATE"], True),
        ],
        reversible=False,
        note="Best end-state economics and the cleanest thermal integration. "
             "Everything is at risk behind a single licensing gate.",
    ),
    "modular": dict(
        label="Modular staged",
        summary="1 MW increments, each stage funding the next. Reactor enters "
                "at the point where thermal demand justifies it.",
        stages=[
            ("Site control + environmental review", 12, 2_000_000, ["SITE"], False),
            ("Prototype + desktop validation", 9, 400_000, [], False),
            ("Module 1 (grid)", 10, 8_000_000, ["FINANCE", "GRID", "OFFTAKE"], True),
            ("Module 2-3 from revenue", 18, 14_000_000, [], False),
            ("Reactor licensing (parallel)", 48, 25_000_000, ["CONSTRUCT", "OPERATE"], False),
            ("Reactor build", 36, 85_000_000, [], False),
            ("Modules 4-10 + cutover", 30, 45_000_000, ["WATER"], False),
        ],
        reversible=True,
        note="Slowest to full scale, lowest capital at risk at any moment, and "
             "the only pathway that generates design feedback before the "
             "expensive commitments.",
    ),
}


def score_pathway(name, spec):
    """Summarise a pathway: duration, peak exposure, gate count."""
    total_months = sum(s[1] for s in spec["stages"])
    total_capital = sum(s[2] for s in spec["stages"])
    gates = [g for s in spec["stages"] for g in s[3]]

    # Time to first revenue and capital sunk before it. The revenue-generating
    # stage is flagged explicitly — inferring it from the stage label was
    # fragile and mis-scored grid-first by a full 24 months.
    months_to_revenue = total_months
    at_risk = total_capital
    acc_months = 0
    acc_capital = 0
    for label, dur, cap, _g, earns in spec["stages"]:
        acc_months += dur
        acc_capital += cap
        if earns:
            months_to_revenue = acc_months
            at_risk = acc_capital
            break

    return dict(
        name=name,
        label=spec["label"],
        total_months=total_months,
        total_capital=total_capital,
        months_to_revenue=months_to_revenue,
        capital_at_risk=at_risk,
        gate_count=len(gates),
        gates=gates,
        reversible=spec["reversible"],
        note=spec["note"],
        summary=spec["summary"],
    )


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def plot_leverage(results, outdir):
    ranked = sorted(results, key=lambda r: r["litres_per_1k_usd"])
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle("Leverage of Small Design Modifications",
                 fontsize=14, fontweight="bold")

    labels = [r["name"].split("(")[0].strip()[:38] for r in ranked]

    ax = axes[0]
    ax.barh(labels, [r["litres_per_1k_usd"] for r in ranked],
            color="#0066cc", alpha=0.85)
    ax.set_xlabel("Litres saved per year, per $1k capital")
    ax.set_title("Water leverage per dollar\n(computed)")
    ax.grid(True, alpha=0.3, axis="x")

    ax = axes[1]
    ax.barh(labels, [r["saved_pct"] for r in ranked],
            color="#cc6600", alpha=0.85)
    ax.set_xlabel("Net annual water reduction (%)")
    ax.set_title("Absolute effect size\n(computed)")
    ax.grid(True, alpha=0.3, axis="x")

    plt.tight_layout()
    path = os.path.join(outdir, "transition_leverage.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_pathways(scores, outdir):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle("Transition Pathways  [inputs UNVERIFIED — see module docstring]",
                 fontsize=13, fontweight="bold")
    names = [s["label"] for s in scores]
    colors = ["#0066cc", "#cc3300", "#009966"]

    ax = axes[0]
    ax.bar(names, [s["months_to_revenue"] for s in scores], color=colors, alpha=0.85)
    ax.set_ylabel("Months")
    ax.set_title("Time to first revenue")
    ax.tick_params(axis="x", rotation=20)
    ax.grid(True, alpha=0.3, axis="y")

    ax = axes[1]
    ax.bar(names, [s["capital_at_risk"] / 1e6 for s in scores], color=colors, alpha=0.85)
    ax.set_ylabel("$M")
    ax.set_title("Capital at risk before revenue")
    ax.tick_params(axis="x", rotation=20)
    ax.grid(True, alpha=0.3, axis="y")

    ax = axes[2]
    ax.bar(names, [s["gate_count"] for s in scores], color=colors, alpha=0.85)
    ax.set_ylabel("Gates")
    ax.set_title("Regulatory / financial gates")
    ax.tick_params(axis="x", rotation=20)
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    path = os.path.join(outdir, "transition_pathways.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def print_report(capacity_mw, base_net, base_gross, base_dry, results, stacked,
                 scores):
    kwh_year = capacity_mw * 1000 * 24 * 365
    line = "=" * 78

    print(line)
    print("  NUCLEAR DONUT — TRANSITION POSSIBILITIES")
    print(line)
    print(f"\n  Baseline ({capacity_mw} MW, corrected water model):")
    print(f"    Net water demand:   {base_net:>12,.0f} L/year")
    print(f"    Gross consumption:  {base_gross:>12,.0f} L/year")
    print(f"    WUE (net):          {base_net / kwh_year:>12.3f} L/kWh")
    print(f"    Fully dry-cooled:   {base_dry:>12} months")

    print(f"\n{line}")
    print("  1. MOST LEVERAGED SMALL MODIFICATIONS  [water figures COMPUTED]")
    print(line)
    print("\n  Ranked by litres saved per year per $1k of capital.\n")
    print(f"  {'#':>2} {'Modification':<42} {'Save%':>7} {'L/yr/$1k':>10} {'Capex':>10} {'Eff':>4}")
    print("  " + "-" * 78)
    ranked = sorted(results, key=lambda r: r["litres_per_1k_usd"], reverse=True)
    for i, r in enumerate(ranked, 1):
        print(f"  {i:>2} {r['name'][:42]:<42} {r['saved_pct']:>6.1f}% "
              f"{r['litres_per_1k_usd']:>10,.0f} {'$'+format(r['capex_usd'],','):>10} "
              f"{r['effort']:>4}")
    print("\n  Effort: 1=setpoint  2=minor equipment  3=system  4=construction  5=redesign")
    print("  [UNVERIFIED] capex and effort are declared assumptions, not quotes.")

    print("\n  Detail:")
    for i, r in enumerate(ranked, 1):
        print(f"\n  {i}. {r['name']}")
        print(f"     saves {r['saved_L_year']:,.0f} L/yr ({r['saved_pct']:.1f}%), "
              f"WUE -> {r['wue']:.3f} L/kWh, dry months {r['dry_delta']:+d}")
        print(f"     {r['rationale']}")

    chosen, combined, individual_sum, net_stacked, dry_stacked = stacked
    print(f"\n{line}")
    print("  Stacking the top 3 — leverage is not additive")
    print(line)
    for r in chosen:
        print(f"    - {r['name']}")
    print(f"\n    Sum of individual savings:  {individual_sum:>12,.0f} L/yr")
    print(f"    Actual combined saving:     {combined:>12,.0f} L/yr")
    overlap = individual_sum - combined
    print(f"    Overlap (double-counted):   {overlap:>12,.0f} L/yr "
          f"({overlap/individual_sum*100 if individual_sum else 0:.0f}%)")
    print(f"    Net demand after stacking:  {net_stacked:>12,.0f} L/yr "
          f"({net_stacked/kwh_year:.3f} L/kWh)")
    print(f"    Fully dry-cooled months:    {dry_stacked:>12}")
    print("\n    These levers compete for the same heat. Each one removes load")
    print("    the others were going to remove, so their savings overlap. Sizing")
    print("    all three off their individual figures would over-promise.")

    # The top lever works by widening the free-cooling band, and free cooling is
    # the one thing monthly means model worst. Say so where it will be read.
    top = ranked[0]
    if top["dry_delta"] > 0 or dry_stacked >= 11:
        print(f"\n  {'!' * 74}")
        print("  CAVEAT ON THE TOP RESULT — this is where the model is weakest.")
        print(f"  {'!' * 74}")
        print("\n  The leading lever works by widening the free-cooling band, and")
        print("  free cooling is exactly what monthly-mean temperatures model worst.")
        print("  water_sim.py ramps free cooling on the monthly MEAN dry-bulb; the")
        print("  hottest month here averages 24 C, but summer afternoons in northern")
        print("  Minnesota reach the low-to-mid 30s. Those hours are the ones that")
        print("  need the tower, and a monthly mean cannot see them.")
        print("\n  So a result of 12 fully dry-cooled months is almost certainly too")
        print("  good. The tower must still be SIZED for the peak hour even if it")
        print("  runs only a few dozen hours a year — you cannot buy 92% less tower,")
        print("  only run it 92% less.")
        print("\n  What that changes:")
        print("    - the annual WATER saving is probably real, and large")
        print("    - the CAPITAL saving is not; peak-hour sizing is unchanged")
        print("    - 'zero water' is not a claim this model can support at all")
        print("\n  Confirming it needs hourly TMY data for the site. Until then this")
        print("  ranking is a hypothesis about where leverage lies, not a result.")

    print(f"\n{line}")
    print("  2. PROPAGATION — what the model change made stale")
    print(line)
    print("\n  A corrected number is not delivered until everything sized off the")
    print("  old number has been resized.\n")
    for p in PROPAGATION:
        print(f"  [{p['severity']:<8}] {p['artefact']}")
        print(f"             depends on: {p['depends_on']}")
        print(f"             was based on: {p['old_basis']}")
        print(f"             action: {p['action']}")
        print()

    print(line)
    print("  3. TRANSITION PATHWAYS  [ALL FIGURES UNVERIFIED]")
    print(line)
    print("\n  Gate categories are real; the months and dollars attached to them")
    print("  are placeholders. Licensing is jurisdiction-specific — get counsel.\n")
    print(f"  {'Pathway':<22} {'To revenue':>11} {'At risk':>12} {'Total':>12} {'Gates':>6} {'Rev?':>5}")
    print("  " + "-" * 76)
    for s in scores:
        print(f"  {s['label']:<22} {s['months_to_revenue']:>8} mo "
              f"{'$'+format(round(s['capital_at_risk']/1e6),',')+'M':>12} "
              f"{'$'+format(round(s['total_capital']/1e6),',')+'M':>12} "
              f"{s['gate_count']:>6} {'yes' if s['reversible'] else 'NO':>5}")

    for s in scores:
        print(f"\n  {s['label']}")
        print(f"    {s['summary']}")
        print(f"    Gates: {', '.join(sorted(set(s['gates'])))}")
        print(f"    {s['note']}")

    print(f"\n{line}")
    print("  Charts saved to sim_output/")
    print(line)


def main():
    parser = argparse.ArgumentParser(
        description="Transition possibilities and leverage analysis")
    parser.add_argument("--capacity-mw", type=float, default=1.0,
                        help="IT capacity in MW (default: 1)")
    parser.add_argument("--top-n", type=int, default=3,
                        help="How many levers to stack (default: 3)")
    args = parser.parse_args()

    outdir = W.ensure_output_dir()

    base_net, base_gross, base_dry, results = evaluate_levers(args.capacity_mw)
    stacked = evaluate_stacked(args.capacity_mw, results, top_n=args.top_n)
    scores = [score_pathway(k, v) for k, v in PATHWAYS.items()]

    plot_leverage(results, outdir)
    plot_pathways(scores, outdir)

    print_report(args.capacity_mw, base_net, base_gross, base_dry,
                 results, stacked, scores)


if __name__ == "__main__":
    main()

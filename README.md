# Nuclear Donut Data Center

A biomimetic, nuclear-integrated data center design using radial steam distribution, evaporative cooling, and ultra-low-cost land reuse within nuclear exclusion zones.

## Overview

This project visualizes a next-generation data center optimized for:

- Direct nuclear energy integration
- Biomimetic cooling based on leaf airflow
- Radial architecture (donut-shaped) for maximum efficiency
- Modular rack expansion with 3x3 tier design
- Evaporative cooling towers powered by waste steam

## Key Features

- **Power**: Direct from 10-20 MW nuclear reactor
- **Cooling**: Steam + evaporative = 90% energy savings
- **Architecture**: Donut-style radial layout
- **Location**: Within existing nuclear exclusion zones (zero land cost)
- **Security**: Already nuclear-hardened

## Technologies Used

- HTML + CSS for the visual model
- Biomimicry principles (leaf, ant colony, spiral forms)
- Steam thermodynamics + passive cooling design
- Python simulations — acoustic/thermoacoustic, water budget, and self-healing kinetics

## Economic Advantages

- 50-60% operational cost reduction
- Up to $155M in savings over 20 years
- Rapid ROI (6-14 months in some models)

> **Unsourced.** These three figures are the most-quoted numbers in the project and trace to
> no calculation anywhere in this repository. They predate the corrected water model and have
> not been rederived against it. Treat them as aspiration until someone shows the arithmetic —
> see `legacy/run-log.md` entry 14.

## Coming Soon

- Animated steam simulation
- Modular expansion visualizer
- Open-source dataset + blueprint system

## Key Files

- `Index.html` - Interactive data center visualization
- `Design-concept.md` - Architectural and geometric logic
- `Construction-sim.md` - Build blueprint and structural design
- `Heat-dissipation-prototype.md` - Desktop thermal prototype specs
- `1MWDataCenterBOMSim.md` - Bill of materials for 1 MW module
- `Controller-overview.md` - AI and thermal control logic
- `Wiring-control-rules.md` - Electrical wiring and mode logic
- `Prototype-build-list.md` - Materials list for desktop prototype
- `Thermoacoustic-harvesting.md` - Acoustic energy harvesting from donut resonance
- `Remediation-toolkit.md` - Environmental remediation physics toolkit
- `harmonic_sim.py` - Resonant mode, standing wave, and Coriolis airflow simulation
- `water_sim.py` - Energy-conserving heat allocation and monthly water budget
- `transition_sim.py` - Highest-leverage modifications, change propagation, transition pathways
- `legacy/` - Retired work, kept as precedent — see below

## How This Project Handles Being Wrong

The design moves the way science does:

```
hypothesize → run → result → falsified? → edit the claim → search for the new unknowns → rerun
```

Two files carry that record, and neither is optional reading:

- **[`legacy/run-log.md`](legacy/run-log.md)** — every time a claim in this repo was actually
  executed and checked: what it predicted, what the run printed, and whether that falsified
  it. Sixteen entries so far. The largest: the evaporative cooling model **did not conserve
  energy** — it rejected 7–12% of the IT load and discarded the rest, understating water
  demand by ~37×. That model has been rebuilt around an explicit heat allocation that must
  sum to the load, and net demand is now **~4.0 M L/yr per MW (0.455 L/kWh)** with seven
  fully dry-cooled months. **Check the log before quoting any simulation number.**
- **[`legacy/README.md`](legacy/README.md)** — what has been retired, and why. Superseded
  files are moved here with their reasoning attached; they are never deleted. A claim that
  was tested and replaced is still a result, and the precedent it set still carries.

## Status

Ongoing design and simulation phase. Seeking collaborators, symbolic optimization, and feedback.

Simulations run, but "runs" is not "validated" — several published figures are known to be
wrong and are documented as such rather than quietly patched.

---


## 🌱 CISSR Integration

The **Cyber-Integrated Self-Sustaining Regeneration (CISSR)** framework bridges BioGrid2.0's regenerative philosophy with this data center's physical infrastructure. It enables:

- **Material self-healing** (crystalline, polymer, and nanoparticle-based)
- **Biological remediation** (engineered microbes for water purification and crack sealing)
- **Symbolic control logic** (AI-driven damage prediction and response)

### Core Documents
- [CISSR Framework](CISSR/cissr-framework.md)
- [BioGrid2.0 Bridge](CISSR/biogrid-bridge.md)
- [Implementation Plan](CISSR/cissr-implementation-plan.md)
- [Sensor Specification](CISSR/cissr_sensors_spec.md)
- [Simulation Module](CISSR/cissr_sim.py)
- [Babel Protocol](CISSR/babel-protocol.md) and its [literature review](CISSR/docs/babel-literature-review.md)

Made with resilience in mind by [JinnZ2](https://github.com/JinnZ2)

## License

MIT or CC0 - feel free to use, improve, or deploy.

---

*Built on a cellphone by a creator who believes knowledge should be shared freely.*

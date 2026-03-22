# Thermoacoustic Energy Harvesting System

## Core Insight

The donut geometry with a hot center (reactor) and cool exterior (server racks) is the textbook configuration for a **thermoacoustic engine** — a device that converts a temperature gradient into sustained acoustic oscillations. The toroidal building shape matches the topology of the most efficient thermoacoustic engine ever built (Backhaus & Swift, 1999).

Instead of suppressing acoustic resonance in the circular structure, this system **designs it in deliberately** as an energy conversion and cooling mechanism.

---

## How It Works

### The Thermoacoustic Cycle

1. Gas parcels oscillate back and forth inside resonant channels
2. Near the hot end (reactor core), gas absorbs heat and expands
3. Near the cold end (outer wall), gas rejects heat and contracts
4. This phased expansion/contraction sustains and amplifies acoustic oscillations
5. The acoustic power is then harvested as electricity or used to drive cooling

### Architecture in the Donut

```
[Reactor Core - HOT]
       |
       | Radial spoke ducts (thermoacoustic engines)
       | Temperature gradient drives acoustic oscillations
       | Internal SPL: 150-170 dB (contained in ducts)
       |
       v
[Outer Annulus - COOL]
       |
       +---> Toroidal acoustic bus (circumferential travelling wave)
       |        |
       |        +---> Linear alternators at antinodes → Electricity
       |        |
       |        +---> Thermoacoustic refrigerators → Server cooling
       |
       +---> Servers placed at pressure nodes → Quiet, low vibration
```

**Three-stage system:**

1. **Radial thermoacoustic engines** in spoke-like ducts convert reactor waste heat into acoustic power flowing outward
2. **Toroidal acoustic bus** distributes acoustic energy around the circumference via travelling-wave modes
3. **Harvesters** tap the bus at intervals — either linear alternators (electricity) or thermoacoustic refrigerators (cooling)

---

## Performance Estimates (1 MW Module)

### Thermoacoustic Engine (Heat to Acoustic Power)

| Parameter | Value |
|-----------|-------|
| Hot side temperature | 300-500 C (reactor outer vessel) |
| Cold side temperature | 25-35 C (server hall air) |
| Carnot efficiency at these temps | 50-60% |
| Travelling-wave engine efficiency | 40-50% of Carnot |
| **Thermal-to-acoustic efficiency** | **20-30%** |
| Working gas | Pressurized helium (best performance) |
| Estimated acoustic power (8-12 radial channels) | 40-120 kW |

### Linear Alternators (Acoustic to Electric)

| Parameter | Value |
|-----------|-------|
| Acoustic-to-electric efficiency | 75-90% |
| Per-unit output | 50 W - 10 kW |
| Moving parts | Piston only (flexure bearings, sealed for life) |
| **Estimated electrical output** | **32-96 kW** |

### Thermoacoustic Refrigeration (Acoustic to Cooling)

| Parameter | Value |
|-----------|-------|
| COP (Coefficient of Performance) | 1.0-3.0 |
| At COP 2: 1 kW acoustic input = | 2 kW cooling output |
| No refrigerant gases required | Yes |
| No compressors or rotating parts | Yes |
| **Estimated cooling capacity** | **80-240 kW** |

### Combined System Value

The acoustic power can be split between electricity and cooling based on demand:

| Scenario | Electricity | Cooling | Notes |
|----------|-------------|---------|-------|
| All electric | 32-96 kW | 0 | Maximum power recovery |
| All cooling | 0 | 80-240 kW | Maximum heat rejection |
| Balanced (50/50) | 16-48 kW | 40-120 kW | Likely optimal mix |
| Adaptive | Variable | Variable | AI-controlled based on load |

---

## Standing Wave Placement Strategy

### Node and Antinode Physics

In a circular resonant cavity, standing waves create predictable zones:

- **Pressure antinodes**: Maximum pressure oscillation, maximum energy density — best for harvesters
- **Pressure nodes**: Zero pressure oscillation, minimum vibration — best for servers and personnel

### Circumferential Mode Spacing

For a donut with mean circumference L, mode number n creates 2n nodes and 2n antinodes:

| Mean radius | Circumference | Mode n | Frequency | Node spacing |
|-------------|---------------|--------|-----------|-------------|
| 50 m | 314 m | 100 | ~109 Hz | ~1.57 m |
| 25 m | 157 m | 50 | ~109 Hz | ~1.57 m |
| 10 m | 63 m | 18 | ~98 Hz | ~1.75 m |

At practical operating frequencies (50-150 Hz), node/antinode spacing is 1-3 m — fine-grained enough for alternating server pods and harvester modules.

### Zoning Layout

```
Top-down view of outer ring (unwrapped):

[HARVEST] [SERVER] [HARVEST] [SERVER] [HARVEST] [SERVER]
 antinode    node    antinode    node    antinode    node
 max energy  quiet   max energy  quiet   max energy  quiet
```

- Server racks at pressure nodes experience minimal vibration
- Harvesting modules at pressure antinodes extract maximum energy
- Spacing determined by operating frequency of the thermoacoustic system

---

## Addressing the Vibration Problem

This system converts the vibration hazard identified in the acoustic audit into a design feature:

| Problem (from audit) | Solution |
|----------------------|----------|
| Central turbine radiates vibration through structure | Radial spoke ducts contain and channel acoustic energy |
| Circular geometry creates standing waves | Standing waves become the energy transport mechanism |
| Whispering gallery effect focuses noise on outer wall | WGMs become the circumferential energy distribution bus |
| Pulsatile fans create resonance risk | Thermoacoustic oscillations replace pulsatile fan patterns |
| Server racks exposed to vibration | Servers placed at calculated pressure nodes |
| No acoustic treatment in BOM | Acoustic metamaterial barriers isolate server zones |
| 36 fans at 85-95 dB combined | Thermoacoustic cooling reduces fan count and duty cycle |

---

## Addressing the Water Budget Problem

Thermoacoustic refrigeration reduces dependence on evaporative cooling:

| Cooling source | Water consumption | Capacity |
|----------------|-------------------|----------|
| Evaporative cooling (current design) | 7,000-25,000 L/day per MW | Primary |
| Thermoacoustic refrigeration (this system) | **Zero** | 80-240 kW |
| Cold-air free cooling (winter months) | Zero | Variable |

At 80-240 kW of thermoacoustic cooling capacity for a 1 MW module:
- **8-24% of cooling load handled with zero water consumption**
- Reduces evaporative water demand proportionally
- Operates year-round regardless of climate (no freeze risk)
- Partially addresses the seasonal gap during MN winters when evaporative cooling is unavailable

---

## Bio-Inspiration

| Biological system | Engineering parallel |
|-------------------|---------------------|
| Cochlea (inner ear) | Toroidal resonant cavity with frequency-selective zones |
| Echolocation (bats, dolphins) | Acoustic energy focused and harvested at specific targets |
| Thermoreception (pit vipers) | Temperature gradient drives energy conversion |
| Circulatory system | Acoustic bus distributes energy like blood distributes oxygen |
| Organ of Corti | Piezoelectric-like transducers at specific resonant positions |

---

## Precedent and References

### Demonstrated Systems

| System | Achievement | Relevance |
|--------|-------------|-----------|
| Backhaus & Swift (LANL, 1999) | 710 W acoustic, 30% efficiency, toroidal topology | Direct precedent — same loop geometry |
| Aster Thermoacoustics (Netherlands) | Multi-kW commercial waste heat recovery | Proves industrial viability |
| Penn State / Ben & Jerry's | 120 W thermoacoustic refrigerator, no refrigerants | Proves cooling application |
| NASA Stirling Radioisotope Generator | 80 W electric, 23% efficiency, sealed for life | Proves long-term reliability |
| Chinese Academy of Sciences | Multi-kW, thermoacoustic gas liquefaction | Proves high-power scaling |
| US Navy / Penn State | Shipboard thermoacoustic chiller | Proves harsh-environment operation |

### Key Properties of Thermoacoustic Systems

- **No moving parts** (except alternator piston on flexure bearings)
- **No refrigerant gases** (uses inert helium or air)
- **No lubrication required** (sealed, maintenance-free)
- **Lifetime**: 20+ years with no servicing (NASA heritage)
- **Scalable**: Multiple units in parallel for any power level

---

## Integration with Existing Design

### New BOM Items (1 MW Module)

- 8-12x Radial thermoacoustic engine ducts (pressurized helium, regenerator stacks)
- 10-20x Linear alternators (flexure-bearing, 1-10 kW each)
- 4-8x Thermoacoustic refrigerator stages (branching off acoustic bus)
- Acoustic metamaterial/phononic crystal barriers between server and harvester zones
- Helium gas management system (fill, monitor, top-up)
- Acoustic pressure and phase monitoring sensors

### Modifications to Existing Systems

- **Controller-overview.md**: Add thermoacoustic mode — AI balances acoustic power split between electricity and cooling based on real-time demand
- **Construction-sim.md**: Radial spoke ducts designed into the concrete pour as structural/acoustic channels
- **Wiring-control-rules.md**: Linear alternator electrical output feeds into the DC bus alongside reactor power

---

## Open Questions

1. **Optimal operating frequency**: Depends on final building dimensions. Needs acoustic modeling.
2. **Helium containment**: Pressurized helium at building scale requires careful sealing. Leak detection and top-up systems needed.
3. **Acoustic isolation effectiveness**: How well can metamaterial barriers protect server zones? Needs experimental validation.
4. **Cost-benefit**: Capital cost of thermoacoustic system vs. value of recovered energy and reduced water consumption.
5. **Regulatory**: Novel building-integrated thermoacoustic system may require new structural and safety certifications.

---

*Concept originated from the observation that the donut's acoustic "problem" (resonance, standing waves, whispering gallery modes) is actually an energy concentration mechanism waiting to be harvested.*

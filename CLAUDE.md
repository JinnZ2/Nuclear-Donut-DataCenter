# CLAUDE.md

## Project Overview

**Nuclear-Donut-DataCenter** is a biomimetic data center design that integrates direct nuclear energy (10-20 MW micro-reactors) with bio-inspired cooling systems in a radial "donut-shaped" architecture. The project targets deployment within existing nuclear exclusion zones for zero land cost and projects 50-60% operational cost reduction.

**Status:** Active design and simulation phase — not production-ready. Seeking collaborators and feedback.

## Repository Structure

```
Nuclear-Donut-DataCenter/
├── CLAUDE.md                      # This file — AI assistant guide
├── README.md                      # Project overview and key features
├── LICENSE                        # MIT License
├── Index.html                     # Interactive 3D/CSS visualization of the donut design
├── Design-concept.md              # Architectural geometry and radial layout specs
├── Construction-sim.md            # Build blueprint and structural design
├── Heat-dissipation-prototype.md  # Desktop thermal prototype specifications
├── 1MWDataCenterBOMSim.md         # Bill of materials for 1 MW production module
├── Controller-overview.md         # Arduino/Python control system design
├── Wiring-control-rules.md        # Electrical wiring and cooling mode logic
├── Prototype-build-list.md        # Materials list for desktop prototype
├── Thermoacoustic-harvesting.md   # Acoustic energy harvesting from donut resonance
└── Remediation-toolkit.md         # Environmental remediation physics toolkit (15 disciplines)
```

This is a **flat, documentation-first repository** — no subdirectories, no compiled source code.

## Languages and Technologies

| Language | Usage |
|----------|-------|
| Markdown | Primary documentation format (9 files, ~1,100 lines) |
| HTML5/CSS3/JavaScript | Interactive visualization (`Index.html`, ~365 lines, vanilla — no frameworks) |
| Arduino C / pseudo-code | Control system sketches embedded in `Controller-overview.md` |
| Physics/math notation | Equations and formulas throughout, especially `Remediation-toolkit.md` |

## Build, Test, and CI

- **No build system** — no `package.json`, `Makefile`, `Cargo.toml`, or equivalent
- **No test framework** — validation is physical/experimental (thermal prototype testing)
- **No CI/CD pipelines** — no `.github/workflows/` or equivalent
- **No linting/formatting** tools configured
- **No external dependencies** — `Index.html` is fully self-contained with no CDN imports

To view the visualization, open `Index.html` directly in a browser.

## Code Conventions

### HTML/CSS (`Index.html`)
- 4-space indentation
- Kebab-case CSS class names (`.nuclear-core`, `.cooling-tower`, `.rack-section`)
- CSS organized by component with feature-level comments (`/* Nuclear Reactor Core */`)
- Animation keyframes named descriptively (`@keyframes glow-red`, `@keyframes rotate`)
- Cyberpunk/terminal aesthetic: dark background, neon green/orange accents

### Markdown documentation
- Standard header hierarchy (`#` for title, `##` for sections, `###` for subsections)
- Bold for key terms, fenced code blocks for equations/formulas and diagrams
- Markdown tables for comparisons (pipe-delimited with header row)
- Dash-prefixed bullet points (`- `) for specifications and feature lists
- `---` horizontal rules for section dividers
- File naming: `Descriptive-name.md` (capitalized, hyphen-separated)

### Arduino/control pseudo-code
- Fenced code blocks with `c` language annotation
- Enum-style mode constants: `IDLE`, `PULSE`, `EVAP`, `GEO`, `MAX`, `ADAPTIVE`, `EMERGENCY`
- Descriptive function names: `updateMode()`, `applyFanPattern()`, `readAverageTemp()`
- Comments explaining each mode's purpose and trigger conditions

## Key Domain Concepts

- **Donut architecture:** Radial server rack layout around a central nuclear reactor core for uniform heat distribution
- **Biomimetic cooling:** Inspired by termites, leaves, blood vessels, elephant ears, gills — uses leaf-pattern heat sinks, spiral vortex ducts, evaporative cooling
- **Exclusion zone deployment:** Repurposes existing nuclear facility buffer zones (no additional land acquisition)
- **Cooling modes:** Seven operational states from IDLE through EMERGENCY, managed by Arduino controller with sensor feedback loops
- **Phase change materials (PCM):** Paraffin wax thermal buffers for load smoothing
- **Geothermal integration:** 600m+ underground coil mesh for supplementary heat rejection
- **Thermoacoustic harvesting:** Donut resonance converted to electricity or cooling via travelling-wave engines, linear alternators, and thermoacoustic refrigerators

## Documentation Map

| File | Purpose | Key Content |
|------|---------|-------------|
| `README.md` | Entry point | Features, economics, project status |
| `Design-concept.md` | Architecture | Donut geometry, radial layout, thermal zones |
| `Construction-sim.md` | Build plan | Structural materials, assembly sequence, foundation |
| `Heat-dissipation-prototype.md` | Prototype specs | Desktop thermal test rig, performance targets (<0.5 K/W thermal resistance) |
| `1MWDataCenterBOMSim.md` | Production BOM | Full cost breakdown for 1 MW module |
| `Controller-overview.md` | Controls | Arduino sensor/actuator design, 7 cooling modes |
| `Wiring-control-rules.md` | Electrical | Wiring diagrams, mode transition logic |
| `Prototype-build-list.md` | Materials | Shopping list for desktop prototype build |
| `Thermoacoustic-harvesting.md` | Energy recovery | Harvesting donut resonance via thermoacoustic engines |
| `Remediation-toolkit.md` | Remediation | 15 physics disciplines for environmental cleanup |

## Working with This Repository

### Adding new design documents
- Create a new `.md` file at the repository root
- Follow existing naming convention: `Descriptive-name.md` (capitalized, hyphen-separated)
- Use consistent Markdown formatting (see conventions above)
- Update `README.md` if the document covers a major new subsystem

### Modifying the visualization
- All visualization code is in `Index.html` (single file, no build step)
- CSS animations drive the visual effects — modify `@keyframes` rules for behavior changes
- Component sections are clearly commented in the CSS
- Test changes by opening the file in a browser

### Important notes for AI assistants
- This is a **design specification** project, not executable software — do not look for or suggest adding build/test infrastructure unless explicitly requested
- The project creator built this on a cellphone — keep contributions accessible and self-contained
- License is MIT or CC0 — all contributions are freely shareable
- Physics equations in `Remediation-toolkit.md` use LaTeX-style notation in code blocks
- When editing documentation, preserve the existing formatting style and level of technical detail
- The repository uses flat structure intentionally — avoid introducing subdirectories without discussion

## Git Information

- **Default branch:** `main`
- **License:** MIT
- **Created by:** [JinnZ2](https://github.com/JinnZ2)

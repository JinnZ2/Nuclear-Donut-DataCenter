# Run Log

The notebook half of `legacy/`. One entry per time a claim in this repo was actually
executed and checked against what it predicted.

Format for each entry:

- **Claim** — what the repo asserted before the run.
- **Run** — what was executed, and what it printed.
- **Verdict** — `HELD`, `FALSIFIED`, or `UNDECIDABLE`.
- **Edited claim** — what the assertion becomes now.
- **New unknowns** — what the result opened up that nobody has answered yet.

Entries are append-only. A superseded entry is not edited or removed; a later entry
supersedes it and says so.

---

## 2026-08-14 — First full execution of the simulation suite

Environment: Python 3, `numpy` + `matplotlib` installed fresh. All three scripts run from
the repo root with default arguments.

| Script | Exit | Outcome |
|--------|------|---------|
| `harmonic_sim.py` | 0 | Ran clean. Acoustic modes, thermoacoustic performance, and Coriolis block all produced output. No contradictions found in this pass. |
| `CISSR/cissr_sim.py` | 0 | Ran clean. Detected 21 cracks, 21 healing actions, 1.05 units mineral precipitated. Not yet checked against any external prediction. |
| `water_sim.py` | 0 | Ran clean, **but four separate claims in its output are contradicted by its own numbers.** See below. |

**The headline lesson: exit code 0 is not a result.** All three scripts "passed" in the only
sense a script can pass, and one of them is printing physically impossible conclusions. Until
today nothing in this repo had been run and *read*.

---

### Entry 1 — Water volumes in gallons

- **Claim** — `water_sim.py` reports annual water use in both litres and US gallons.
- **Run** — printed `Total consumption: 1,022,446 L/year (270 gal)` and
  `Net demand: 108,720 L/year (29 gal)` and `Estimated water cost: $0 /year`.
- **Verdict** — **FALSIFIED.** 1,022,446 L is 270,132 gal, not 270. The summary block divided
  by `3785` (litres per *thousand* gallons) where the constant is `3.785` litres per gallon —
  a factor of 1000. The same file already had the correct constant elsewhere
  (`liters_per_gallon = 3.785`), so the file contradicted itself.
- **Edited claim** — corrected in `water_sim.py`; the conversion now uses the single
  `LITERS_PER_GALLON` constant everywhere. Annual water cost is **~$158/year**, not $0.
- **New unknowns** — none. This was arithmetic, not physics.

---

### Entry 2 — Thermoacoustic water offset

- **Claim** — thermoacoustic harvesting offsets a large share of cooling water demand.
- **Run** — printed `Thermoacoustic savings: 1,308,998 L/year (128.0% of gross)`, against a
  gross consumption of 1,022,446 L/year.
- **Verdict** — **FALSIFIED.** You cannot save more water than you consume. The offset is
  credited at a flat 6,117 L/day for seven months regardless of whether there is any demand
  to offset — in April the model credits 6,117 L/day against an evaporative load of
  2,867 L/day. Recovery is summed uncapped, while `net_L_day` is separately clamped with
  `max(0, ...)`, so the surplus disappears from the net but still inflates the ratio.
- **Edited claim** — the thermoacoustic water offset is **unquantified**. The 128% figure is
  withdrawn. No replacement number is asserted, because the correct cap depends on a design
  question nobody has answered yet (see below).
- **New unknowns** —
  1. Is the offset meant to *replace* evaporative load (so it should be capped at that
     month's evaporative demand), or to *produce* water usable elsewhere (so the surplus is
     real and should show as recovered inventory, not as savings)?
  2. Is the flat 6,117 L/day itself defensible, or should it scale with the thermal load
     driving the acoustic engine? A constant offset through a season whose cooling load
     varies by 1.9× is suspicious on its face.
  3. Where does surplus recovered water physically go? There is no storage term in the model.
- **Status** — **left in the code, unfixed and now documented.** Fixing it means choosing
  between (1) and (2) above, and that is a design decision, not a bug fix.

---

### Entry 3 — "Near-zero water months: 7 (frozen + free cooling)"

- **Claim** — seven months need almost no water because they are frozen or on free cooling.
- **Run** — the seven months with net demand under 100 L/day are **Apr–Oct**, the *warm*
  months. The five months labelled `FROZEN` (Jan, Feb, Mar, Nov, Dec) each carry
  720 L/day.
- **Verdict** — **FALSIFIED, and inverted.** The label attributes the near-zero months to
  freezing, when freezing is exactly what the water-carrying months have in common. The warm
  months only reach zero because Entry 2's uncapped offset drives them negative and the
  clamp floors them at zero.
- **Edited claim** — this is not an independent finding. It is Entry 2 seen from a different
  angle, and it resolves when Entry 2 resolves.
- **New unknowns** — none beyond Entry 2.

---

### Entry 4 — Peak water month

- **Claim** — printed `Peak water month: Jan (720 L/day)`.
- **Run** — January is the peak because every summer month was zeroed by Entry 2.
- **Verdict** — **FALSIFIED.** A cooling-water budget for northern Minnesota that peaks in
  January is a symptom, not a finding. January's 720 L/day is pure steam loss, which the
  model applies at a constant 720 L/day in all twelve months. Annual net demand
  (108,720 L) is exactly 151 days × 720 L/day — the five frozen months' steam loss and
  nothing else.
- **Edited claim** — the model currently predicts that **all** net water demand is steam
  loss during freezing months. That is a strong, testable claim, and it is entirely an
  artifact of Entry 2 rather than a designed result.
- **New unknowns** —
  1. Should steam loss really be constant year-round, independent of ambient temperature
     and cooling mode?
  2. April is flagged `FROZEN` while simultaneously reporting 2,867 L/day of evaporative
     cooling. The `frozen` flag and the evaporative model disagree about what April is.
     Which one is wrong?

---

## Carried forward — open unknowns

Consolidated list of everything the runs above opened and nobody has closed:

1. Does the thermoacoustic offset replace evaporative load, or produce usable water? *(E2)*
2. Should the offset scale with thermal load rather than sit flat at 6,117 L/day? *(E2)*
3. Where does surplus recovered water go — the model has no storage term. *(E2)*
4. Should steam loss vary with ambient temperature and cooling mode? *(E4)*
5. April is both `FROZEN` and evaporatively cooled — which flag is wrong? *(E4)*
6. `CISSR/cissr_sim.py` runs and prints healing counts, but nothing in the repo says what
   those counts *should* be. Until there is a predicted value, its output is **UNDECIDABLE**
   in the sense used above — it cannot be falsified, so it cannot yet be evidence.

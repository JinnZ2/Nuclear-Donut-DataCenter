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

---

## 2026-08-14 (second session) — Reality-testing the six carried-forward unknowns

Method: a probe harness importing `water_sim` directly and evaluating each model function
month by month, plus two external benchmark checks against published figures. Every number
below is reproducible by re-running the models; the external figures are cited inline.

**Result: five of the six are now closed, and closing them exposed a defect larger than any
of them.** Two further arithmetic bugs were found and fixed in passing.

---

### Entry 5 — Reported water recovery double-counts the offset

- **Claim** — `total_recovery_L_day` is the sum of condenser, dew, and thermoacoustic recovery.
- **Run** — the probe computed `cond + dew + ta_offset` = 1,380,900 L/yr. The script reported
  2,689,898 L/yr. The difference is exactly 1,308,998 L/yr — the offset, counted a second time.
  Source: `recovery` was already defined as `cond + dew + ta_offset`, then stored as
  `recovery + ta_offset`.
- **Verdict** — **FALSIFIED.** Pure double-count.
- **Edited claim** — fixed. Reported annual recovery is 1,380,900 L/yr. Net demand is
  unaffected (it used the single-counted value), so no other figure moves.
- **New unknowns** — none. Arithmetic.

---

### Entry 6 — The evaporative model does not conserve energy *(new, and it is the big one)*

- **Claim** — `evaporative_water()` models the water needed to reject the data center's heat.
- **Run** — the model rejects `capacity × 0.30 × effectiveness`. Evaluated across the year
  that is **65.6–121.9 kW of a 1,000 kW IT load — 7% to 12%.** The other 88–93% is not
  rejected anywhere else in the model. Geothermal is soil *irrigation* (27–81 L/day), not a
  heat path; steam loss is a leak term. The heat simply vanishes.
- **Reality check** — implied WUE is **0.119–0.187 L/kWh**. Published figures for
  evaporatively-cooled data centers are **1.55–2.5 L/kWh**, with an industry average of
  1.8–1.9 L/kWh. The model is ~10× low. (The model's number does land near AWS's reported
  0.19 L/kWh — but AWS reaches that with extensive free-air cooling, not by evaporating less
  water per unit of heat. Matching the number by the wrong mechanism is not agreement.)
  Rejecting the *full* 1 MW evaporatively would need **38,230 L/day ≈ 1.59 L/kWh** — which
  lands inside the real evaporative range, and is the strongest evidence that full-load
  rejection is the correct form and the `0.30 × effectiveness` factor is the error.
- **Verdict** — **FALSIFIED.** Wet-bulb effectiveness sets how close the tower can approach
  the wet-bulb temperature. It does not reduce the quantity of heat that must leave the
  building. Using it as a multiplier on heat load deletes energy from the balance.
- **Edited claim** — evaporative water demand in this repo is understated by roughly an order
  of magnitude. **No water figure in this project should be quoted until this is resolved.**
- **New unknowns** —
  1. What fraction of the IT load is actually rejected evaporatively vs. geothermally vs. by
     free cooling? The model needs an explicit split that sums to 100%.
  2. Does the geothermal loop have a heat-rejection capacity figure anywhere? It is currently
     modelled only as soil irrigation, with no kW rating.
- **Status** — documented, **not fixed.** The split across cooling paths is a design decision
  and changing it rewrites every headline water number in the project.

---

### Entry 7 — U1: does the offset displace load, or produce water?

- **Question** — is the thermoacoustic offset a displacement credit or a water source?
- **Run** — settled by the code's own docstring: *"thermoacoustic_kw of cooling = that much
  less evaporative cooling needed. Returns liters/day of water SAVED."*
- **Verdict** — **ANSWERED: displacement.** It is a credit against evaporative load, which
  means it must be capped at the evaporative load actually present. It was never a water
  source, so it can never legitimately exceed consumption.
- **Edited claim** — U1 is closed. `ta_offset` should be `min(offset, evap)`.
- **Consequence, measured** — applying that cap: recovery falls from 135.1% to **80.2% of
  gross**, and net demand rises from 108,720 to **202,095 L/yr (+86%)**. The cap alone makes
  the model self-consistent, but see Entry 8 — it binds in all 12 months, which is itself a
  symptom of Entry 6.

---

### Entry 8 — U2/U3: should the offset scale, and where does surplus go?

- **Claim** — 160 kW of thermoacoustic cooling displaces evaporative demand.
- **Run** — peak evaporative heat rejection all year is **121.9 kW (June)**; the annual
  minimum during the active season is 65.6 kW. The 160 kW credit **exceeds the load it claims
  to displace in every single month — 0 of 12 fit.** `thermoacoustic_offset()` also ignores
  its `capacity_mw` argument entirely, so the credit is flat regardless of plant size.
- **Verdict on U2** — **FALSIFIED, but not where expected.** A flat credit is wrong, yet the
  *fix is not to scale the offset* — 160 kW is consistent with `harmonic_sim.py`'s own
  40–300 kW range. The offset only looks impossible because Entry 6 understates the load it
  is being subtracted from. Correct the energy balance and 160 kW becomes ~16% of a 1 MW
  rejection load, which is unremarkable.
- **Verdict on U3** — **DISSOLVED.** With the cap applied, recovery exceeds consumption in
  **0 of 12 months**. There is no surplus, so no storage term is needed. U3 was never an
  independent gap; it was Entry 2 wearing a different hat.
- **Edited claim** — U3 is closed and withdrawn. U2 is closed: the offset does not need to
  scale with load, it needs a load that is correctly sized. Both fold into Entry 6.
- **New unknowns** — `thermoacoustic_offset()` accepting and discarding `capacity_mw` is a
  latent trap for anyone who runs `--capacity-mw 10` and believes the output.

---

### Entry 9 — U5: is April frozen or not?

- **Claim** — April is reported `FROZEN` while evaporating 2,867 L/day.
- **Run** — the two gates read different media. `evaporative_water()` gates on **air**
  temperature (`T_db < 5 °C → 0`); April air is +7 °C, so evaporation correctly runs.
  `geothermal_water()` gates on `GROUND_FROZEN`, a **soil** state; northern Minnesota frost
  leaves the ground through April, so soil-frozen in April is correct too.
- **Verdict** — **NEITHER MODEL IS WRONG.** Both are right about their own medium. The defect
  was the printed status column, which rendered a soil flag as a whole-system label.
- **Edited claim** — fixed, and it was a labelling bug, not physics. Status now describes the
  cooling system (`NO-EVAP` / `FREE` / `ACTIVE`) with `*` marking frozen soil. April now reads
  `FREE*` — free cooling available, ground still frozen. Both facts, no contradiction.
- **New unknowns** — none. **Note for the future:** this one was worth chasing precisely
  because it turned out *not* to be a physics error. An apparent contradiction that resolves
  into two correct models and one bad label is still a finding.

---

### Entry 10 — U4: should steam loss vary with ambient temperature?

- **Claim** — steam loop loss is 720 L/day, constant across all twelve months.
- **Run** — 1 MW × 1,500 kg/hr × 24 h × 2% blowdown = 720 L/day. That steam flow carries
  ~942 kW of latent heat, consistent with a 1 MW load, so the flow figure is sound. Blowdown
  is governed by cycles of concentration and makeup water chemistry; leak and trap losses by
  joint integrity. None of those depend on outdoor air temperature.
- **Verdict** — **HELD on the question asked; FALSIFIED on a question nobody asked.**
  Constant *with ambient temperature* is defensible and stands. But `steam_losses()` takes no
  month index at all, so it is also constant *with load* — while the model's own cooling
  demand swings from 65.6 to 121.9 kW across the season. Blowdown scales with steam
  throughput, and throughput is not constant.
- **Edited claim** — steam loss should be constant per unit of steam *flow*, not constant per
  *day*. The 2% fraction is right; applying it to a fixed flow is not.
- **New unknowns** — does the steam loop run at constant flow year-round (reactor always at
  full output, excess dumped) or does it follow load? That is a plant operating decision and
  nothing in the repo states it.

---

### Entry 11 — U6: can `cissr_sim.py` be falsified?

- **Claim** — recorded on 2026-08-14 as **UNDECIDABLE**: the sim prints healing counts but
  nothing says what they should be.
- **Run** — inspection found the output is worse than undecidable, it is dimensionally
  incoherent. `detect_cracks()` returns **array indices**, and `heal_crack()` then multiplies
  those indices by `(1 - healing_rate)` as if an index were a crack width — so a crack at
  index 97 "heals" to 77.6 of nothing. `precipitate_minerals()` is marked `# placeholder` and
  returns population × 1e-6. The input is `np.random.normal(0.3, 0.2, 100)` with **no seed**,
  so no two runs agree.
- **Reality check** — but one declared parameter *is* testable: `healing_rate = 0.2 mm/hour`.
  Published results for crystalline admixtures: cracks up to **0.4 mm** heal completely, with
  150 μm closing in 28 days under water, and 400 μm in 28 days with 10% CSA plus 1.5% CA.
  At 0.2 mm/hour the model would close **134 mm in 28 days** — about **336× the best
  documented rate**, and 300× wider than any crack the literature reports sealing at all.
- **Verdict** — **U6 is closed, and the answer flipped: FALSIFIED, not undecidable.** The
  self-healing literature supplies exactly the external benchmark that was missing, and the
  declared healing rate fails it by two and a half orders of magnitude.
- **Edited claim** — `healing_rate` should be ~**6e-4 mm/hour** (0.4 mm over 28 days) to match
  the best published crystalline-admixture performance. The current value is not a slow
  approximation of reality; it is a different phenomenon.
- **New unknowns** —
  1. Seed the RNG, or the sim cannot be regression-tested at all.
  2. Decide whether `detect_cracks` returns positions or widths, and make `heal_crack`
     consume the same quantity.
  3. Radiation exposure is in `CISSRConfig` (1,000 Gy tolerance) but no model uses it. The
     whole premise is healing *under neutron flux*, and flux appears nowhere in the kinetics.

---

## Carried forward — revised

*Supersedes the carried-forward list in the 2026-08-14 first-session entry above. Items 1, 2,
3, 5 and 6 of that list are now closed by entries 6–11.*

Still open, in the order they should be tackled:

1. **How does the total heat load split across evaporative, geothermal, and free cooling?**
   *(Entry 6.)* Everything else waits on this. Until the energy balance closes, no water
   number in this repo means anything.
2. Does the geothermal loop have a heat-rejection rating, or is it only ever soil irrigation?
   *(Entry 6.)*
3. Does the steam loop run at constant flow, or follow load? *(Entry 10.)*
4. `thermoacoustic_offset()` silently ignores `capacity_mw` — `--capacity-mw 10` produces a
   wrong answer with no warning. *(Entry 8.)*
5. `cissr_sim.py` needs a seeded RNG, coherent crack units, and a healing rate near
   6e-4 mm/hour before it can predict anything. *(Entry 11.)*
6. Radiation flux is the entire premise of CISSR and appears in no kinetic model. *(Entry 11.)*

**Sources for the external checks in entries 6 and 11**

- [Data Center Water Usage: A Comprehensive Guide — dgtlInfra](https://dgtlinfra.com/data-center-water-usage/)
- [A Guide to Data Center Water Usage Effectiveness (WUE) — Data Center Knowledge](https://www.datacenterknowledge.com/cooling/a-guide-to-data-center-water-usage-effectiveness-wue-and-best-practices)
- [What Is Water Usage Effectiveness (WUE) in Data Centers? — Equinix](https://blog.equinix.com/blog/2024/11/13/what-is-water-usage-effectiveness-wue-in-data-centers/)
- [Evaluation of Internal and Superficial Self-Healing of Cracks in Concrete with Crystalline Admixtures — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7663569/)
- [Influence of Crystalline Admixtures and Their Synergetic Combinations on Autonomous Healing in Cracked Concrete — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC8781983/)
- [Self-Healing Concrete with Crystalline Admixture — A Review (ResearchGate)](https://www.researchgate.net/publication/337746220_Self-healing_concrete_with_crystalline_admixture_-_a_review)

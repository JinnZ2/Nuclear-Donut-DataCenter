# Legacy

Superseded files live here. **Nothing in this folder is deleted, and nothing here is
worthless** — a claim that was tested and replaced is a result, and the precedent it set
still carries forward into the design that replaced it.

This project moves the way science does:

```
hypothesize → run → result → falsified? → edit the claim → search for the new unknowns → rerun
```

Each turn of that loop produces something that is no longer current but is still *evidence*.
Deleting it destroys the reason the current design looks the way it does. So it comes here
instead, with a note explaining what it claimed, what happened when it was tested, and what
replaced it.

---

## What is in here

| File | Retired | Claimed | Why it was retired | Replaced by |
|------|---------|---------|--------------------|-------------|
| `architecture.md` | 2026-08-14 | A repo file tree could be maintained as a standalone doc | Went stale in the same month it was written — it described only `CISSR/` and already omitted `CISSR/docs/`. A second source of truth for structure drifts from the first. | `CLAUDE.md` → *Repository Structure* (single source of truth) |
| `Controller-modes-sim.py` | 2026-08-14 | Cooling-mode logic could be prototyped in Python against mock sensors | Mode thresholds diverged from the canonical Arduino spec and were never reconciled; sensor reads are `random.uniform()` stubs, so it can neither confirm nor falsify anything. Kept as the record of the first mode taxonomy. | `Controller-overview.md` → *Mode Logic (Arduino C)* |

---

## Retirement rules

A file moves here when **any** of these is true:

1. **Falsified** — it was run or checked and the result contradicted the claim.
2. **Superseded** — a newer file is now the single source of truth for the same thing.
3. **Undecidable** — it cannot be tested as written (mock data, no measurable prediction),
   so it can never earn or lose confidence.

A file does **not** move here merely for being old, short, or unpolished. Age is not
falsification.

## How to retire a file

1. `git mv <file> legacy/<file>` — keep the name, keep the history.
2. Add a short `> **Superseded** ...` block at the top of the moved file. Change nothing else
   in it. The retired content stays as it was written, or it is not evidence.
3. Add a row to the table above.
4. Fix every inbound reference to the old path.
5. If the retirement came from a *result* rather than a tidy-up, record the run in
   [`run-log.md`](run-log.md).

## What lives where

- **This file** — the index: what was retired and why.
- **[`run-log.md`](run-log.md)** — the notebook: what was claimed, what the run actually
  printed, which claims that falsified, and what is still unknown.

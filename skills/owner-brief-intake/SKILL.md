---
name: owner-brief-intake
description: Converts an owner's natural-language requirement, tender documents, or route/cargo description into a frozen machine-readable design brief with a requirement traceability matrix. Use at the very start of any ship design task, before any sizing or geometry, and whenever the owner changes a requirement mid-project.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: intake
  stage: S0
---

# Owner Brief Intake

Design work before a frozen brief is waste. Your job: turn prose into `brief.json` plus a
traceability matrix, surface contradictions **quantified**, and get the owner's confirmation.

## Extract or ask for

- **Mission**: ship type; cargo/service (units: TEU, DWT, m³, lane-metres, pax, tonnes of
  a named commodity); trade/route with port pairs; terminal constraints (berth depth, crane
  outreach, air-draft under bridges, lock/canal dimensions — Panama, Seaway, Kiel etc.);
  ice class; service speed AND the economic context of it; range/endurance; crew and
  passengers; intended charter mode (voyage, time, COA) because it decides who pays for speed.
- **Envelope (hard limits)**: LOA, beam, air draft, max draft (each with its source —
  terminal, canal, class), displacement or DWT target, capacity items.
- **Regulatory**: flag, class society + rule set, conventions in scope (the
  `regulatory-mapping` skill expands this), fuel policy (HFO/LNG/methanol/ammonia-ready?)
  because it drives arrangement and EEDI path.
- **Commercial**: budget band, delivery window, series or one-off, yard preference or
  constraint, warranty expectations for speed/consumption.
- **Reference**: parent/sister ship data if any — the single most valuable input you can get.

If a field is missing, ASK (batched, with defaults proposed and consequences stated) rather
than assuming. Flag and class may be "to be selected" — record that explicitly and note the
consequence: no rule compliance can be *claimed*, only *provisionally evaluated* against a
named assumed rule set.

## Contradiction detection (the core value)

Check, quantify, and surface — never silently resolve:

- DWT target vs draft/beam limits: compute Δ at max draft and compare with lightship + DWT.
- Speed vs EEDI phase vs budget: high speed + small DWT + Phase 3 is often infeasible; say so
  with numbers from the `edi-trade-study` grid before the owner falls in love with 14 kn.
- Range vs fuel capacity vs cargo volume: fuel tanks compete with cargo and ballast.
- Crew/pax vs accommodation volume vs air draft.
- Ice class vs EEDI (ice-classed ships have different paths) vs speed.

Present each as: "Requirement A and B conflict; satisfying A costs X of B; options: …".

## Output

```json
{
  "ship_type": "...", "service": "...", "trade": "...",
  "cargo_capacity_target_t": 35500, "dwt_target_t": 39000,
  "service_speed_kn": 14.0, "range_nm": 12000, "crew": 22,
  "max_loa_m": 190.0, "max_breadth_m": 29.8, "max_air_draft_m": 25.0,
  "max_scantling_draft_m": 10.5,
  "flag": "...", "class_society": "...", "rule_set": "...",
  "propulsion": "...", "fuel_policy": "...",
  "requirements": [{"id": "R-01", "text": "...", "verify": "method + artefact"}],
  "assumptions": [{"id": "A-01", "text": "...", "consequence_if_wrong": "..."}],
  "open_questions": [{"id": "Q-01", "text": "...", "blocks": "S1"}]
}
```

Every requirement gets an ID and a verification method ("how will we know it is satisfied,
and in which artefact"). Every assumption gets a consequence. Freeze with the owner's
explicit confirmation — this is human gate #1 (`human-gates-escalation`).

## Gates

- Every requirement row has an ID, testable text, and a verification method (an artefact that
  will prove it) — 100% coverage, checked mechanically before freeze.
- Every assumption has a consequence-if-wrong; every open question names what it blocks.
- Contradiction list is empty or each item is an explicit owner decision recorded with date.
- Owner confirmation recorded (human gate #1) before any downstream stage consumes brief.json.

## Prohibitions

- No sizing, no geometry, no "meanwhile I started a hull…" before the brief is frozen or the
  owner explicitly accepts a provisional brief in writing (recorded as an assumption).
- Never resolve a contradiction by dropping the harder requirement.
- Never treat marketing prose ("eco-friendly", "future-proof") as a requirement; convert it
  to a testable one (EEDI phase, fuel-ready notation, CII band) or record it as an open question.

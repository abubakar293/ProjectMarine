---
name: class-statutory-compliance
description: Builds and maintains the rule-compliance matrix - machine-readable clause database from supplied rule documents, per-clause evidence links, satisfied/N-A/OPEN statuses with owners. Use at S7 and continuously as designs change; also use to set up the clause database at project start.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: compliance
  stage: S7
---

# Class & Statutory Compliance

Compliance is data, not prose. The deliverable is a matrix where every applicable clause has
a status, a computed evidence link, and — when OPEN — a named owner and action.

## The clause database

Encode each clause from the SUPPLIED rule documents (never from memory) as:

```json
{"clause_id": "SOLAS II-1/25-8", "source": "SOLAS as amended", "edition": "2024 consolidated — confirm",
 "applies_to": {"ship_type": ["cargo"], "gt_min": null, "keel_date_min": "2009-01-01"},
 "requirement": "...", "formula": "...", "limit": {"op": ">=", "value": 0.055, "units": "m.rad"},
 "verification": "stability-intact:area_0_30", "evidence_link": "analysis/2026-10-25-intact-departure/"}
```

- `verification` binds the clause to the computation that satisfies it — the binding is what
  makes the matrix live: when the computation re-runs, the status updates.
- `evidence_link` points at the run folder (inputs hash, solver log, outputs).
- Editions: the register from `regulatory-mapping` pins them; a clause without an edition is
  not encoded.
- Rule-change notices: subscribe the project to the class society's update feed; a clause
  that changed after encoding is worse than a missing one — version the database.

## Building the matrix

1. Applicability pass: for each clause, evaluate `applies_to` against the ship data →
   applicable / N-A (with the basis written down — fleet finding E02: "N/A without basis"
   is a MAJOR).
2. Evidence pass: bind each applicable clause to its verification computation; run; record
   computed value vs limit; status = satisfied / FAIL / OPEN(no computation yet).
3. Gap pass: clauses with no possible computation in the current stack become OPEN items with
   the external tool or class interaction named ("run weather criterion in NAPA", "class
   review of fatigue assessment").
4. Every FAIL is a design defect or a data defect — route to the owning discipline skill;
   every OPEN gets owner + action + due date into `design_record.json`.

## Interaction with class

Plan-approval submission packages (the drawing/report index from `documentation-package`),
AIP requests for novel features, and surveyor queries all consume the matrix. An agent may
ASSEMBLE and CHECK completeness of a submission; it may not claim approval. The realistic
external checkpoint for agent-driven design is an Approval-in-Principle-style gate: the
published agentic-engineering precedent in offshore structures passed CCS AIP with exactly
this architecture (deterministic backends + automated reviewer + external class check).

## Gates

- 100% of applicable clauses have a status; 0 unsourced.
- 0 satisfied-by-prose: every "satisfied" has an evidence_link that re-runs.
- The matrix regenerates from the record in one command; hand-edited rows are impossible
  (the file is generated).

## Prohibitions

- No clause text quoted from memory — the #1 rule of this repo (three mis-transcribed
  formulas, defects #36–38).
- No status flipped without the evidence re-running.
- No marking OPEN items N/A to make the matrix look clean (fleet rule: a visible OPEN is
  safe; a hidden one is how people die).

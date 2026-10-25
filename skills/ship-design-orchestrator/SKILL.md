---
name: ship-design-orchestrator
description: Runs an end-to-end ship or vessel design project from an owner's natural-language requirement to a shipyard-ready design package. Use when asked to design, size, re-design or produce a preliminary/contract design package for any ship, barge, workboat, ferry, offshore unit or yacht - including brief intake, stage sequencing, gate enforcement, multi-agent review, and deliverable assembly. Start here for any ship design task.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: orchestration
  stage: S0-S9
---

# Ship Design Orchestrator

You are the lead designer of record for a ship design project. You coordinate discipline
skills; you do not substitute for their solvers. **You never invent a number.** Every value
in the design record comes from a logged tool run that anyone can re-execute.

## First move: intake, not design

Whatever the user gave you, do not start drawing or sizing. Activate `owner-brief-intake`
and produce `brief.json` first. If the brief has internal contradictions (DWT vs draft vs
beam limits, speed vs EEDI vs budget), **surface them with the trade-off quantified** — never
silently resolve them in favour of whichever is easiest to compute.

## Stage machine

Run stages in order. Each stage writes artefacts to the design record and passes a gate.
**Never advance with a failed gate**: iterate inside the stage, or escalate to a human via
`human-gates-escalation`. The gate definitions live in docs/PIPELINE.md; the skills per
stage are:

| Stage | Skills | Gate essence |
|---|---|---|
| S0 Brief | `owner-brief-intake`, `regulatory-mapping` | every requirement has ID + verification method |
| S1 Sizing | `ship-sizing`, `weight-control` | displacement budget closes ±2% |
| S2 Hull | `hull-form-generation` | coefficients in band; mesh watertight |
| S3 Stability | `hydrostatics-crosscheck`, `stability-intact`, `stability-damage`, `seakeeping-maneuvering` (when scoped) | two solvers <0.01% apart upright; IS criteria pass or OPEN-with-owner |
| S4 Powering | `resistance-powering`, `edi-trade-study` | validity bands; EEDI compliant **under stress** or escalated |
| S5 Structure | `structural-loads`, `scantlings-midship`, `structural-fe-verification`, `simulation-suite` (FE/CFD runs) | equilibrium identities; FE-vs-integrator BM agreement <1%; utilisation <1.0 |
| S6 Arrangement | `general-arrangement`, `machinery-layout`, `marine-systems` | one tank model; range delivered |
| S7 Compliance | `class-statutory-compliance` | every clause satisfied / N-A / OPEN with citation |
| S8 Cost & build | `weight-control`, `cost-estimating`, `shipyard-data-requirements`, `production-design-handoff` | steel 55–95% of lightship; yard limits respected |
| S9 Package | `documentation-package`, `sea-trials-warranty`, `cad-drawing-generation` | drawings read back against the model; booklet matches model hash; **finalization freeze honoured** |

Cross-cutting, always active: `verification-gates`, `provenance-discipline`,
`defect-patterns`, `agent-fleet-review`, `human-gates-escalation`, `error-fix-loop`,
`toolchain-selection`, `simulation-suite`.

## The design record (single source of truth)

```
project/
  brief.json                # frozen requirement set
  master-model/             # dimensions, hull (STEP/STL/offsets), tanks, weights — hashed
  rules/                    # machine-readable clause table (user-supplied; you cite, never recall)
  analysis/<run>/           # inputs, solver log, outputs, plots — one folder per run
  drawings/  reports/       # generated FROM the record, never hand-edited after
  design_record.json        # results + traceability + open items with owners
  runs.log                  # stage, tool, version, input hash, output hash, pass/fail
```

Anything not in the record does not exist. If a downstream number changes because an
upstream one changed, the run log must show the chain.

## Multi-agent layout

Spawn one reviewer/worker per discipline rather than one generalist doing everything; each
gets its own skill and solver access. Coordinate **through files in the record**, not
conversation. Before each concept freeze, run `agent-fleet-review` against your own output.
Require at least three structurally different candidates at concept stage (different
Cb/LCB families, subdivision, or propulsion architecture) and record why the losers lost —
a single-candidate design is design fixation.

## Hard rules

1. A failed gate **raises**, it does not warn-and-continue. Count your raises vs warnings;
   if warnings outnumber raises, your gates are decoration.
2. Rule constants come from rule text in force, or the item is OPEN. Never from memory.
   (Three separate memory-transcriptions of one wave-BM formula gave 1.5e8, 152, and 3.5e5
   kN·m against a true ~2e6 — see docs/DEFECT-LOG.md #36–38.)
3. Every third-party tool is validated against closed-form ground truth before its first
   real use (`verification-gates`).
4. Third-party solvers get **cleaned** meshes: degenerate triangles changed one correct
   solver's volume by −19% (defect #14).
5. Unit conventions of every tool are established empirically and written down at the call
   site (defect: assuming kg where the tool wanted tonnes floated a ship 1000× too light).
6. OPEN items carry an owner role and an action. An OPEN item that is visible is safe; one
   an agent quietly marked satisfied is how people die.

## Gates (this skill's own)

- No stage advances with a failed gate; the driver raises (count raises vs warnings — see
  fleet finding I09: warnings outnumbering raises means gates are decoration).
- The design record regenerates deterministically; geometry hash matches across re-runs.
- Generated drawings pass read-back verification (the DXF is re-opened and measured
  against the model) before they enter the package.
- Simulation results enter the record only from validated tool runs (`simulation-suite`):
  closed-form or benchmark case reproduced within tolerance, at the same tool version.
- The record carries a `finalization` block; while ANY FAIL or OPEN item exists its status
  is NOT_FINALIZED, and only a human gate may ever move it to RELEASED (`error-fix-loop`).
- Every requirement in brief.json has a status in the traceability matrix at all times
  (PASS / FAIL / OPEN with owner and action).
- Concept freeze requires ≥3 scored candidates AND a discriminating gate (a tie is reported
  as a tie, never as a winner).

## Prohibitions

- Never invent a number, a rule constant, a vendor envelope, or a yard limit.
- Never advance past a failed gate "to keep moving".
- Never report a single candidate as "the design" — alternatives with rejection reasons, or
  an explicit statement that the space could not be explored and why.
- Never present an OPEN item as satisfied, or strip an ESTIMATE tag from an owner-facing
  document.

## When to stop and get a human

Concept freeze, class submission, contract design, production release — and any time you
hit: novel hull type with no parent data; a rule interpretation not in your rule set;
a safety-critical margin you cannot verify deterministically; a commercial trade-off
affecting the owner's business case. Present evidence and uncertainty; never minimise them.

# The pipeline

Ten stages from owner's requirement to shipyard-ready package. Each stage produces artefacts
into a single **design record** (versioned files + JSON + run log) and ends at a **gate**.
A failed gate stops the run — a warning that does not stop the run is not a gate.

```
S0 Brief ──► S1 Sizing ──► S2 Hull form ──► S3 Hydrostatics & stability ──► S4 Powering & EEDI
                                                                                  │
S9 Documentation ◄── S8 Cost & build ◄── S7 Compliance ◄── S6 Arrangement ◄── S5 Structure
    package            strategy            matrix           & systems
```

| Stage | Skill(s) | Artefacts | Gate (stops the run when failed) |
|---|---|---|---|
| S0 | `owner-brief-intake`, `regulatory-mapping` | `brief.json`, requirement traceability matrix, applicable-instrument list | every requirement has an ID + verification method; contradictions surfaced, not silently resolved; flag/class fixed or explicitly deferred with consequences stated |
| S1 | `ship-sizing`, `weight-control` | principal dimensions, displacement budget, weight groups with margins | displacement closes ±2%; lightship/DWT and freeboard plausible vs parent ships |
| S2 | `hull-form-generation` | parametric generator, offsets table, watertight mesh, STEP/IGES | ∇, LCB, Cb, Cp match targets; Cm ≤ 1 and coefficients inside the type band; mesh watertight after welding and degenerate removal |
| S3 | `hydrostatics-crosscheck`, `stability-intact`, `stability-damage`, `seakeeping-maneuvering` (when scoped) | hydrostatics table, load cases, GZ curves, stability results | two-solver agreement < 0.01% upright; small-angle identity dGZ/dφ → GM within 3%; IS Code criteria pass or are OPEN with an owner |
| S4 | `resistance-powering`, `edi-trade-study` | speed–power sheet, engine/propeller selection, EEDI file, trade study | validity bands respected; EEDI compliant **under stress** or a quantified trade decision is escalated to the owner |
| S5 | `structural-loads`, `scantlings-midship`, `structural-fe-verification` | load curve, SWBM, scantlings, FE results | Σq = 0 and Σq·(x−LCG) = 0; utilisation < 1.0; rule constants sourced or OPEN |
| S6 | `general-arrangement`, `machinery-layout`, `marine-systems` | GA, compartmentation, capacities, tank list, engine room, systems | one tank model shared by capacities and stability; fuel capacity delivers the range; escape/fire/access checks pass |
| S7 | `class-statutory-compliance` | rule compliance matrix with clause citations | every applicable clause marked satisfied / N-A / OPEN with evidence link |
| S8 | `cost-estimating`, `production-design-handoff`, `shipyard-data-requirements` | weight report, steel take-off, cost estimate, build strategy, yard data request list | steel fraction 55–95% of lightship; block sizes vs yard limits; cost basis and exclusions stated |
| S9 | `documentation-package`, `sea-trials-warranty`, `cad-drawing-generation` | spec, stability booklet, reports, drawing index, trials programme | reproducible build from the record; booklet amendment matches the stability model hash; warranty language carries the uncertainty |

## Cross-cutting (every stage)

- `ship-design-orchestrator` — the stage machine itself; it drives this table.
- `verification-gates` — the four mechanisms: ground truth, two solvers, plausibility bands,
  equilibrium identities.
- `simulation-suite` — validated CFD/FE/seakeeping runs on free tools first, paid tools when
  the project has them; every tool reproduces its benchmark before project use.
- `toolchain-selection` — the free-first ladder and paid-tool API integration patterns.
- `cad-drawing-generation` — every sheet rendered from the frozen model and READ BACK against it.
- `error-fix-loop` — the fix protocol and the finalization freeze: nothing is completed,
  released or signed while any error remains open.
- `provenance-discipline` — VERIFIED / STANDARD / ESTIMATE / NOT-IMPL tags; refuse rather
  than invent.
- `defect-patterns` — the 48-defect catalogue as a pre-flight checklist.
- `agent-fleet-review` — chartering reviewer fleets against your own output.
- `human-gates-escalation` — the five human sign-off points and how to present OPEN items.

## The design record

One directory, one source of truth, everything hashed:

```
project/
  brief.json                 # frozen requirement set (S0)
  master-model/              # dimensions, hull geometry (STEP/STL/offsets), tanks, weights
  rules/                     # machine-readable clause table (supplied by you, cited by the agent)
  analysis/                  # one folder per run: inputs, solver log, outputs, plots
  drawings/  reports/        # generated from the record, never hand-edited afterwards
  design_record.json         # rolled-up results + traceability + open items with owners
  runs.log                   # every tool call: stage, tool, version, input hash, output hash
```

Anything not in the record does not exist. Revision drift between the stability booklet and
the loading model is a real-world cause of trial disputes — the record makes it impossible
by construction: both are generated from the same hashed geometry.

## Where humans sign

Five fixed gates (`human-gates-escalation`): brief freeze → concept freeze → class submission
→ contract design → production release. The agent prepares; a named engineer signs. The
agent's job at each gate is to present the OPEN items, the uncertainty, and the evidence —
not to minimise them.

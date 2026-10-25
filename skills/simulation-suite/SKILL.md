---
name: simulation-suite
description: Plans, runs and validates every simulation a ship design needs - resistance/self-propulsion CFD, seakeeping, structural FE, buckling, fatigue screening, flooding, maneuvering - on free tools first (OpenFOAM, CalculiX, Code_Aster, gmsh) and paid tools when the project has them, with each simulation validated against ground truth or benchmark data BEFORE its results are trusted. Use at S3-S5 for any analysis beyond closed-form methods, and to build the project simulation plan.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.2.0"
  domain: simulation
  stage: S3-S5
---

# Simulation Suite

Simulations are how the design stops being an estimate. Three rules make them trustworthy:
**validate before use, quantify uncertainty, cross-check every decision-grade result.**

## Build the simulation plan first

Per ship type and stage, the plan lists every simulation with: purpose, tool (free and paid
path), validation case, acceptance criterion, and the decision it feeds. A simulation not
tied to a decision is compute burned.

| Simulation | Purpose / decision fed | Free path | Paid path | Validation case (public data) |
|---|---|---|---|---|
| Resistance CFD (RANS, free surface) | speed–power, replaces ESTIMATE wave resistance | OpenFOAM (interFoam/overset; shipFoam/DTC-Foam extensions) | STAR-CCM+, Fine/Marine, Fluent | **KCS / KVLCC2 / DTMB 5415** at the ITTC/Gothenburg test conditions |
| Self-propulsion | wake, thrust deduction, η_R, engine point | OpenFOAM overset + actuator disk/body-force prop | STAR-CCM+, Fine/Marine | KCS self-propulsion benchmark |
| Propeller open water + cavitation | η₀, cavitation inception | OpenProp (design), panel codes | XPROP, CAV20xx suite | Wageningen B-series open-water data |
| Seakeeping (RAOs, added resistance) | operability, slam screening, loads for FE | potential panel (in-house/NeMOH-class), strip theory | WAMIT, AQWA, HydroD, WASIM | ITTC/WILDA available RAO sets; KCS head-sea |
| Structural FE global (hold/cargo) | hull-girder utilisation, hot spots | CalculiX, Code_Aster (+ PrePoMax GUI) | Sesam/Sestra, Nauticus Hull, Patran-Nastran | ISSC/SISS benchmarks; closed-form beam cases |
| Buckling & fatigue screening | scantling verdicts | OpenFOAM-independent: class formulas encoded from supplied text, fe-safe-class open tools | Sesam Stofat, Nauticus | rule worked examples |
| Flooding / progressive damage | damage-stability time domain | in-house quasi-static (the reference equilibrium solver extended), OpenFOAM for green water | NAPA, Maxsurf Damage, GHS | MARIN/SHED flooding experiments where available |
| Maneuvering | turning/stopping for the booklet | MMG-model in Python + PMM data if any | class-approved simulators | KVLCC2 zigzag/turning public data |
| Vibration/noise (if comfort class) | accommodation limits | CalculiX modal + FEM/SEA hybrids | VA One, LMS | plate/beam closed-form modal cases |

## Validate before use — non-negotiable

A tool run on the project before it has reproduced its benchmark is an unmeasured
instrument. Per tool:

1. **Closed-form cases** where they exist (beam FE against Euler–Bernoulli: cantilever tip
   load δ = PL³/3EI; simply supported UDL M_max = wL²/8 — the reference `fe_beam.py` runs
   exactly these and raises on >0.5% deviation).
2. **Public benchmark hulls** for hydro: KCS/KVLCC2/DTMB with published test data; report
   your error against it (a good free-surface RANS setup lands within a few % on Ct).
3. **The project's own cross-checks**: empirical vs CFD vs (if any) model-test — three
   points, not one. Disagreement beyond the declared tolerance = investigate, never average.

## Uncertainty, ITTC-style

Every decision-grade CFD result carries: grid convergence (≥3 grids, Richardson/ITTC-1978
style estimate of the discretisation error), iteration convergence, input uncertainty
(geometry hash, boundary conditions), and the validation gap from step 2. One number
without its bar is not a result. The reference build's mesh convergence study (volume
−2.0% → −0.8% with refinement, monotone from below) is the same discipline one level down.

## Free-to-paid escalation

Start free (it is also the only path an open-source user has). Escalate to paid tools when:
the class requires a named tool; the decision value at stake exceeds the licence; or the
free path's validation gap is too large for the decision. **A paid tool does not skip
validation** — it gets the same ground truth first (defect #14: a commercial-grade solver's
volume moved −19% on a mesh with degenerate triangles; the tool was not at fault).

## Where results land

One folder per simulation run in the design record: inputs (with hashes), tool + version,
case file, raw outputs, post-processed numbers, validation reference, uncertainty bar, and
the decision it feeds. The compliance matrix cites run folders, not chat messages.

## Gates

- Validation case reproduced within its stated tolerance BEFORE project use (recorded once
  per tool version).
- Grid/element convergence evidence in every decision-grade run.
- Cross-method agreement within the declared tolerance, or the discrepancy is an OPEN item.
- No simulation result feeds a gate with a wider uncertainty than the gate's margin
  (a +2% EEDI margin resting on ±15% CFD is not a pass).

## Prohibitions

- No default mesh, default turbulence model, or "the tutorial settings" on a decision run
  without the validation case behind it.
- No single-grid CFD presented as converged.
- No tuning the physics (roughness, relaxation, eddy viscosity) to hit a target number —
  that is doping, and it is detectable: the validation case breaks first.
- No discarding a run because the answer is inconvenient; inconvenient answers are findings.

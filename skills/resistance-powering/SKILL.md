---
name: resistance-powering
description: Predicts resistance, installed power and fuel consumption with declared applicability bands and margins - ITTC-57 friction, form factor, wave-resistance treatment, propulsor matching, engine selection - honest about what is ESTIMATE. Use at S4 for speed-power prediction, engine selection, EEDI inputs, and any speed/consumption discussion.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: naval architecture
  stage: S4
---

# Resistance & Powering

A powering number is a contractual number the moment it reaches a charter party. Build the
chain so every link carries its provenance tag and the total carries its uncertainty.

## The chain

R_T = R_F(1+k) + R_APP + R_W + R_B + R_TR + R_A  →  EHP = R_T·V  →  DHP = EHP/η_D  →
MCR = DHP/(η_shaft·η_gear) + margins.

- **R_F**: ITTC-57 line, Cf = 0.075/(log₁₀Re − 2)² — VERIFIED against its definition in a
  self-test. Re at the ACTUAL water temperature; state it.
- **Form factor (1+k)**: transcribed-and-tested regression (Katsui or Holtrop) or model-test
  value. If neither is available: **ESTIMATE 1.45, band 1.30–1.60** — and say so. The
  reference build's memory-transcription of Katsui gave 279.7 and was deleted, not tuned
  (defect #40; see `provenance-discipline`).
- **R_W**: the honest options in order of trust: (1) model test / parent correlation;
  (2) validated CFD (RANS with grid-convergence evidence, ITTC scaling stated);
  (3) transcribed-and-tested regression; (4) **declared allowance** — at Fn ≈ 0.17 for
  Cb ≈ 0.85, R_W ≈ 15% ± 8 pts of R_F as a PLANNING allowance, tagged ESTIMATE with an
  action to replace. Never (5): recalled regression coefficients. The reference
  implementation raises NotImplementedError on option 5 by construction.
- **Wetted surface** from the geometry solver, never a formula estimate (the record says which).
- **Roughness**: coating-specific allowance per ISO 15016 method — state coating class and
  the % used (reference: 4% ESTIMATE).
- **Sea margin**: declare it (15% typical) and keep it OUT of the EEDI attained value but IN
  of the installed MCR — conflating the two is a classic filing error.

## Propulsor and engine

- η_D = η_H·η_R·η₀ with η_H = (1−t)/(1−w). Preliminary single-screw: w ≈ 0.5·Cb − 0.05,
  t ≈ 0.55·w — tagged ESTIMATE, to be replaced by self-propulsion analysis or model test
  before any warranty. η₀ from the propeller designer's open-water data at the J of the
  self-propulsion point — NOT at the design-point J you like.
- Propeller: diameter maxed by clearance/immersion at ALL approved drafts (ballast immersion
  governs more often than designers expect); cavitation checked at ballast and full load;
  for CPP the pitch range and combinator law are part of the record.
- Engine: MCR at the speed point with declared margins; check the engine's continuous-service
  window (do not install an engine whose service point sits below ~25–30% load — glazing and
  fouling, and it means the wrong engine, not the wrong ship); SCR/EGR for NOx Tier III;
  derating curves recorded.
- Alternative fuels: SFC and C_f from the engine maker + MEPC.215(63); LNG carries methane
  slip (not EEDI-visible, real GHG); ammonia adds NOx and toxicity regimes — hand to
  `regulatory-mapping`.

## Deliverable: the speed sheet

One table: V, R_T breakdown, EHP, w/t/η_R/η₀, DHP, MCR, SFC, consumption t/day — with every
margin as its own column and every ESTIMATE tagged in the table, not in a footnote. Plus the
trial-correction plan (ISO 15016) and the warranty exclusion language draft for
`sea-trials-warranty`.

## Gates

- All inputs inside the method's applicability band (Fn, Cb, L/B, B/T, LCB%) — the reference
  records the band check per quantity; outside-band HARD quantities stop the run.
- Power chain reproducible from the record: inputs → outputs with formulas shown.
- Uncertainty carried: state the ± on installed power implied by your ESTIMATE set (the
  reference declared ±25% and used exactly that as the EEDI stress factor).
- Consumption at the service profile (not only sea speed): port days, maneuvering, auxiliary
  load per the owner's operating profile — this feeds CII and the owner's OPEX, and it is
  where "eco" claims live or die.

## Prohibitions

- No speed/consumption warranty language built on ESTIMATE-tagged links.
- No CFD presented without grid convergence and scaling method.
- No propeller matched at only one draft.
- No silent default margins — every margin is a column with a source.

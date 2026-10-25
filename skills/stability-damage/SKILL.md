---
name: stability-damage
description: Runs damage stability - subdivision layout, deterministic and SOLAS 2009 probabilistic methods, damage extents and permeabilities - encoding the process and refusing coefficients that must come from supplied rule text. Use at S3/S6 for cargo ships above the probabilistic threshold, passenger ships, and any type where the regulatory register requires damage survival.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: naval architecture
  stage: S3
---

# Damage Stability

Survivability is a design driver, not a post-check: subdivision decides where tanks and holds
may go, so run this EARLY — after arrangement freeze it becomes a renegotiation.

## Method selection (from the regulatory register)

- Cargo ships above the SOLAS threshold: **probabilistic** (SOLAS II-1 Part B-1: attained
  subdivision index A = Σ pᵢ·sᵢ ≥ required R, with the R formula by ship type/length,
  factor method pᵢ from zone geometry, sᵢ from survivability factors).
- Below threshold / specific types: deterministic floodable length or the type's own code.
- Passenger: probabilistic with A/R ≥ 1 including machinery/ballast damage cases and the
  "safe return to port" regime where applicable.
- Type codes override where stricter (chemical/gas carriers, HSC, offshore).

## What you compute vs what you refuse

COMPUTE (geometry and hydrostatics — no rule constants needed):
- zone/compartment geometry from the arrangement model; damage-zone combinations per the
  applicable extent rules **as supplied**;
- floodable volumes with declared permeabilities (cargo 0.60–0.95 by cargo type,
  accommodation 0.95, machinery 0.85, tanks 0/0.95 by content — state which set and source);
- equilibrium after flooding: sinkage, trim, heel by the same two-solver equilibrium machinery;
- residual GZ per the applicable criterion set; cross-flooding times where ducts are modelled;
- stage flooding sequences where progressive flooding is credible.

REFUSE (record OPEN, named owner = stability engineer + class):
- the R-index formula coefficients and the s-factor constants — from the rule text in force;
- exact damage extents (longitudinal/vertical/transverse dimensions) — rule text;
- any Administration-specific interpretation.
The refusal pattern is the same as `stability-intact`'s weather criterion: compute what is
closed-form physics, structure the boundary so recalled constants cannot leak in.

## Gates

- A ≥ R with the R value CITED from supplied rule text, or the item is OPEN — never "A/R
  looks fine".
- No damage case with heel beyond the criterion limit at equilibrium; no downflooding below
  the margin line in the final condition.
- Every watertight boundary in the arrangement model matches the subdivision used here —
  one geometry, hashed (a bulkhead moved in GA but not in damage stability is defect-class,
  BLOCKER).
- Cross-flooding arrangements sized for the assumed equalisation times.

## Prohibitions

- No damage stability after arrangement freeze without flagging it as a re-open of S6.
- No permeability set without a source.
- No "the deterministic check passes so the probabilistic will too" — different methods,
  different failure modes; the register says which one governs.

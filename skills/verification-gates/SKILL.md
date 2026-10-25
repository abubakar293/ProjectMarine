---
name: verification-gates
description: Enforces the four verification mechanisms that make agent-produced engineering trustworthy - closed-form ground truth, two independent solvers, physical plausibility bands, and equilibrium identities. Use whenever computing, reviewing, or trusting ANY numerical engineering result (geometry, hydrostatics, stability, strength, power, weight, cost), or when writing code that computes physics.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: verification
  stage: cross-cutting
---

# Verification Gates

A number that cannot be checked is an opinion with units. Four mechanisms, in order of
yield-per-effort. All four caught real defects in the reference implementation; the full
catalogue is docs/DEFECT-LOG.md (48 items, every one plausible at the time).

## 1. Closed-form ground truth (do this first, always)

Before any solver touches a real hull, it must reproduce a shape with a known exact answer.
The reference uses a 100×20×10 m prism at 6 m draft: volume 12,000 m³, KB 3.000 m,
Awp 2,000 m², BMt 5.5556 m, BMl 138.889 m, LCF = LCB = 50.00 m. Both solvers reproduce all
seven to 0.0000%.

- Ground truth caught: clipping-winding reversal, unrotated distance arrays, missing
  waterplane cap, wrong moment quadrature, both rotation-matrix errors.
- **Design the test so the trivial case cannot pass**: an early version clipped at z = 0,
  where the cap term vanishes identically — it passed while every real draft was 4,000 m³
  wrong (defect #17). Put the waterplane at a non-zero height.
- Assert the *convention*, not just the number: unit normal, upright → (0,0,1), +heel tilts
  the normal to the low side, +pitch drops the bow. A convention assertion caught a
  rotation whose third row was independent of heel.

## 2. Two independent implementations

Compute every key quantity twice, by different code (ideally different authors/methods),
and **print the disagreement per quantity**. Never average; never take the max; investigate.

- On the reference hull the two solvers agree to 0.0000% on nine hydrostatic quantities and
  ≤0.25% on GZ to 60° heel (rising to ~5% at 80–90°, where faceted-mesh sinkage resolution
  differs — document the tolerance, don't quote large-angle GZ beyond two significant
  figures).
- This is the ONLY mechanism that caught the worst defect in the log: heel implemented about
  the vertical axis instead of the longitudinal axis. Every upright hydrostatic was exactly
  right; the entire stability assessment was computed at zero heel (#23).
- Near-zero quantities: compare absolute deltas against a scale, not percentages — GZ(0°)
  of 1e−5 vs −1e−5 is agreement, not a "−200% disagreement" (#47).

## 3. Physical plausibility bands

Every order-of-magnitude-sensitive quantity gets a band, checked at computation time:

| Quantity | Band | Caught |
|---|---|---|
| Cm | ≤ 1.0, and 0.96–1.00 for bulk carriers | impossible section (#4) |
| Cp | 0.80–0.90 (bulk carrier) | degenerate form exponent (#6) |
| Form factor 1+k | 1.3–1.6 | mis-transcribed regression → 279.7 (#40) |
| Wave BM | 8e5–6e7 kN·m (this size class) | three bad transcriptions (#36–38) |
| Hull steel | 55–95% of lightship | take-off 279 t on 9,062 t lightship (#43) |
| Implied mean structural area | 2–12 m² | stray ×1000 (#45) |
| Midship/mean area ratio | 0.8–3.0 | strength-vs-mass conflation (#44) |

Bands come from parent ships and are **cited**. An uncited band is another guess.

## 4. Equilibrium identities

Physics has exact identities; use them as gates:

- Load curve: Σq = 0 **and** Σq·(x − LCG) = 0; SF and BM zero at both ends.
  The force identity caught a mixed trapezoid/rectangle quadrature that halved every lumped
  mass (#34). The moment identity caught even-keel buoyancy paired with trimmed weights —
  vertical force balanced to six digits while the moment was off by 1.2e6 kN·m (#35).
- Weight build-up: ΣW = Δ·g exactly, asserted at assembly, not after the fact.
- Mesh: watertight (every edge in exactly two non-degenerate triangles), outward normals
  (positive enclosed volume), volume converging monotonically from below with refinement
  (inscribed faceting).

Band provenance: every band in this skill is either VERIFIED (closed-form, e.g. the prism
constants) or a parent-ship STANDARD/ESTIMATE with its source named in the table or in
docs/DEFECT-LOG.md. An uncited band is another guess wearing a gate's uniform.

## Gate behaviour

A gate **raises**. It does not warn-and-continue, and it does not return NaN quietly.
If you find yourself writing `log.warning(...)`, ask what the run should do when the warning
is true — if the answer is "stop", write `raise`. Count raises vs warnings in your driver;
more warnings than raises means the gates are decoration (fleet finding I09).

## Prohibitions

- Never average two solvers' answers, and never pick the convenient one — investigate.
- Never weaken a band to make a result pass; bands are cited, and changing one is a design
  decision with a source, not a debugging step.
- Never ship a single-solver number while a second implementation is available; if truly
  impossible, the record says REDUCED ASSURANCE and names the missing check.
- Never convert a `raise` into a `warning` to "unblock" a run — that deletes the gate
  (fleet finding I09).

## When the check fails

Do not tune until plausible. Diagnose: build the smallest case with a known answer, print
every intermediate term, and reason numerically, not algebraically. Two wrong hand-derivations
of one rotation matrix were each "fixed" by a third derivation before a 6-line numeric
probe settled it in one shot (see reference-implementation/code/diagnostics/).

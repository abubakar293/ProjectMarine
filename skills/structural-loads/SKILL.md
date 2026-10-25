---
name: structural-loads
description: Computes hull-girder loads - still-water bending moment by direct integration of the real load and buoyancy curves with equilibrium identities as gates, and wave bending moment from supplied rule text or OPEN. Use at S5 for longitudinal strength, and whenever loading conditions or hull geometry change.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: structure
  stage: S5
---

# Structural Loads

## Still-water BM: integrate, don't estimate

Build q(x) = w(x) − b(x) from the REAL distributions and integrate twice with free-free ends:

- w(x): lightship groups at their LCGs, cargo per hold (distributed over hold length — not
  lumped at hold centres unless the spacing is honestly fine), tank contents at their fill,
  using the SAME frozen weights the stability stage used (one source of truth).
- b(x): immersed sectional areas at the **TRIMMED waterline** — z_wl(x) = z_ref + (x−LCG)·tanθ
  with z_ref solved so ∇ still equals the displacement. Even-keel buoyancy against trimmed
  weights leaves a residual moment of ~1.2e6 kN·m on the reference case while vertical force
  balances to six digits (defect #35). Only the moment identity catches it.
- SF(x) = ∫q, BM(x) = ∫SF, with the constants fixed by SF(0)=SF(L)=0, BM(0)=0.

### Quadrature discipline (one rule, everywhere)

Lumped weights become m/dx spikes; if your integrators use the trapezoid rule, those spikes
are halved and half of every lumped mass silently vanishes (defect #34: ΣW = 229,000 kN
instead of 458,000; SWBM doubled). Use ONE quadrature (rectangle on a uniform grid is
simplest and consistent), assert it uniform, and use the same rule in the check code —
mixing rules in the checker hides exactly what the checker exists to find.

## Gates: equilibrium identities (raise, don't warn)

- Σq·dx = 0 to 1e-6·Δ·g (vertical force).
- Σq·(x−LCG)·dx = 0 (moment about the LCG).
- SF and BM zero at both ends to 1e-3.
- ΣW = Δ·g asserted when the weight list is assembled, not after integration.

### Self-test that can fail

Validate the integrator on cases with known answers: (1) balanced uniform load → BM ≡ 0
everywhere; (2) two quarter-point loads on uniform buoyancy → hogging w·a²/2 at the quarter
points and **exactly zero at midships** (the first version of this test asserted a
simply-supported W·L/8 midship value against a free-free beam — the integrator was right,
the expectation was wrong, defect #41).

## Wave BM: rule text or OPEN

M_vw comes from the rule set in force (CSR for bulk carriers/oil tankers; class rules
otherwise), at the correct condition (sea-going/harbour, hogging/sagging, with the rule's
partial safety factors). The reference implementation **refuses** it after three
memory-transcriptions produced 1.52e8, 152 and 3.52e5 kN·m against a parent expectation of
~2e6 (defects #36–38). The refusal record carries the gates that caught each attempt, so
the next engineer knows the band before they transcribe. When you DO have the rule text:
encode formula + edition, keep the parent-band gate as a backstop (8e5–6e7 kN·m for this
size class), and unit-test the transcription against a hand-computed example.

## Deliverables

Load/SF/BM curves per governing condition (loaded, ballast, alternate-hold where approved,
heavy cargo); the equilibrium check record; M_vw per rule condition or the OPEN record;
the envelope (max hogging/sagging) feeding `scantlings-midship`.

## Prohibitions

- No SWBM from a multiplier (0.02·Δ·g·L) once real weights exist — multipliers are for S1
  screening only, tagged ESTIMATE.
- No BM curve shipped without BOTH equilibrium identities in the record.
- No local loads (slamming, green water, cargo grab impacts, container stack weights) folded
  into girder loads — separate local-strength cases.

## Escalation

- Wave bending moment (M_vw) requires direct rule transcription or class software extraction when not available from memory; escalate to the structural lead or class society before freezing the girder envelope.
- Permissible still-water bending moment exceeded in any approved loading condition requires ballast/cargo redistribution or structural reinforcement sign-off from the lead naval architect.
- Dynamic slamming, whipping, or springing loads on non-standard hull forms require specialized hydrodynamic/seakeeping analysis beyond beam integration.

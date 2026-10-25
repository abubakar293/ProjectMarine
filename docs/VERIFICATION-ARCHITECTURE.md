# How the multi-agent verification actually works

Not "ask 60 models to look at it". Each reviewer has a **narrow charter** and a
**deterministic check** it can run. A reviewer that only reads prose can only agree with
prose; a reviewer that recomputes a number can disagree with it.

## The three roles

```
                    ┌─────────────────────────────┐
   owner brief ───► │  DESIGNER (run_case.py)     │
                    │  S0 brief → S7 traceability │
                    └──────────────┬──────────────┘
                                   │  design_record.json + artefacts
                                   │  (hashed, reproducible from brief.json)
                                   ▼
                    ┌─────────────────────────────┐
                    │  FLEET (agents/run_fleet.py)│  60 chartered reviewers
                    │  A intake        × 4        │  each recomputes or
                    │  B naval arch    × 12       │  cross-checks; none is
                    │  C structure     × 5        │  allowed to trust the
                    │  D arrangement   × 4        │  record it is reading
                    │  E compliance    × 4        │
                    │  F verification  × 10       │
                    │  G production    × 3        │
                    │  H documentation × 6        │
                    │  I architecture  × 10       │
                    └──────────────┬──────────────┘
                                   │  findings.json (severity + evidence + action + owner)
                                   ▼
                    ┌─────────────────────────────┐
                    │  GATE                       │  BLOCKER ⇒ stop.
                    │                             │  A warning that does not
                    └──────────────┬──────────────┘  stop the run is not a gate.
                                   │
                                   ▼
                          human + class sign-off
```

## Why this caught what it caught

The reference case shipped **48 defects** (see `DEFECT-LOG.md`), every one of which produced
plausible-looking output at the time. They fell to four mechanisms, not to careful reading:

**1. Closed-form ground truth.** An analytic prism 100 × 20 × 10 m at 6 m draft, where
volume, KB, Awp, BMt, BMl, LCF and LCB are known exactly. Both solvers reproduce it to
0.0000%. This is the cheapest, highest-yield check in the whole stack: it caught the
clipping winding reversal, the unrotated distance arrays, the missing waterplane cap, the
wrong first-moment quadrature, the missing volume division, the un-shifted moment frame and
both rotation-matrix errors.

**2. Two independent implementations.** Every hydrostatic value on the real hull is
computed twice — by a from-scratch divergence-theorem solver and by `navaltoolbox` — and the
disagreement is printed, not averaged. On the final run they agree to 0.0000% on nine
quantities and to ≤0.25% on GZ up to 60° heel.

This is what caught the most dangerous defect of all. Heel had been implemented as a
rotation about the **vertical** axis instead of the longitudinal axis, so the waterplane
normal never tilted. Every upright hydrostatic was *exactly right*. The entire stability
assessment was computed at zero heel. Nothing in the upright output could have revealed it.

**3. Physical plausibility bands.** Cm ≤ 1, Cp inside the type band, C_w inside 2.0–10.75,
M_vw inside a parent-ship band, hull steel 55–95% of lightship, implied mean structural area
2–12 m², midship-to-mean area ratio 0.8–3.0. These caught three separate mis-transcriptions
of the wave bending moment (1.52e8, 152 and 3.52e5 kN·m against a parent expectation of
~2e6) and a form factor of 1+k = 279.7.

**4. Equilibrium identities.** Σq = 0 and Σq·(x − LCG) = 0 on the load curve; ΣW = Δ·g
exactly. The first caught a quadrature inconsistency that had silently halved every lumped
mass. The second caught a subtler one where vertical force balanced *perfectly* and only the
moment betrayed that buoyancy had been taken at even keel while the weights sat at the
trimmed equilibrium.

## Rules the fleet enforces on itself

These are not aspirations; they are checks with agent IDs.

| Rule | Agent | Why |
|---|---|---|
| No number without a logged tool run | I05 | an audit trail is what makes the rest defensible |
| One geometry, one tank model, hashed | I01, F05 | revision drift between the booklet and the loading computer is a real cause of trial disputes |
| Re-running gives byte-identical output | I08 | determinism is checked by re-generating the STL and comparing SHA-256 |
| A failed gate stops the pipeline | I09 | counted `raise` vs `WARNING` in the driver; more warnings than raises is a finding |
| Third-party unit conventions pinned empirically | F06 | `navaltoolbox` returns tonnes at `water_density=1.025` and kilograms at `1025.0`; `gz_curve` takes mass in the same unit. Assuming kg floated the ship 1000× too light |
| Meshes cleaned before they reach a solver | F03 | 522 degenerate triangles changed a *correct* solver's volume by −19% and its BMt by +19% |
| Rule constants sourced or refused, never recalled | F07, C02 | `wave_bm` returns OPEN with a reason; the weather criterion has a separate function that only accepts a supplied roll angle |
| Provenance tagged on every constant | F07, B10 | VERIFIED / STANDARD / ESTIMATE / NOT-IMPL |
| Open items visible with an owner | E04, I04 | an OPEN item that is visible is safe; one an agent quietly marked satisfied is not |
| The gate must discriminate | I03 | three candidates all scored 88.51, so "selected: C" was arbitrary — reported as a BLOCKER against the gate itself |
| Limits stated as loudly as capabilities | I07, A04 | an overstated capability is the most dangerous thing this stack can ship |

## The refusal mechanism

The most important behaviour in the system is the one that produces no number.

`structure.wave_bm()` returns `{"implemented": False, "status": "OPEN", "reason": ...,
"action_required": ...}`. `iscode.weather_criterion()` computes the unambiguous parts and
refuses K. `powering.py` raises `NotImplementedError` for the Holtrop–Mennen wave-resistance
term.

Each of those was *attempted* first, produced a wrong number, and was deleted rather than
tuned until it looked plausible. Tuning a mis-transcribed regression until it gives a
believable answer is worse than not having it: the result then carries the authority of a
citation it does not deserve. The boundary is enforced structurally — the weather criterion's
"accept a supplied roll angle" path is a *different function*, so an agent cannot reach it by
accident while computing K itself.

## What the fleet is not

It is not 60 opinions. Every finding carries evidence that is a number, a file, or the output
of a recomputation. Three findings from an earlier run were false positives (a stale JSON key,
a self-test detector that missed an external test module, and a regex that flagged the literal
`24 * 0.0216` as placeholder algebra) and were fixed in the reviewers — a fleet that cannot be
wrong about its own findings is not checking anything either.

It also does not replace a naval architect. The two remaining substantive BLOCKERs are a
genuine regulatory failure (EEDI Phase 3, −44.8% margin) and a gate that cannot yet rank its
candidates. Both need a human decision and better computations respectively; neither needs
another reviewer.

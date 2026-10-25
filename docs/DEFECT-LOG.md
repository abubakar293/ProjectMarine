# Defect log — what the multi-agent verification actually caught

Every entry below is a defect that **shipped plausible numbers** at the moment it was found.
That is the point of the log: none of these would have been caught by reading the output.

The reference case is a Handysize bulk carrier (Lpp 180 m, B 29.8 m, D 15.2 m, T 10.5 m,
Cb 0.845), fully regenerated from a frozen brief by `code/run_case.py`.

| # | Where | Defect | Symptom that exposed it | What it would have cost |
|---|---|---|---|---|
| 1 | hull generator | Parallel-middle-body branch tested *after* the afterbody branch, so `u = x/l_run > 1` inside the PMB | Cb came out 0.344 instead of 0.845; Cm = 1.057 (> 1, geometrically impossible) | A hull that does not exist |
| 2 | hull generator | `run_frac + ent_frac ≥ 1`, so the PMB had negative length | Cb target unreachable; bisection returned its upper bracket | Silently "converged" wrong form |
| 3 | hull generator | Global beam multiplier used to hit Cb | B redefined from 29.8 m to 35.8 m | Violates the terminal/lock constraint the owner set |
| 4 | hull generator | Cm > 1 not rejected | Midship section area exceeded B × T | Impossible section passed downstream |
| 5 | hull generator | Waterline fullness exponent varied along the length, so `c(x)` was not the section-area coefficient | Actual area ∝ c^0.52; ends far fuller than the distribution claimed (A/Am = 5.1 × c near the stem) | Fair-looking hull with wrong Cp and wrong resistance |
| 6 | hull generator | Degenerate exponent accepted to force Cb | Solved exponent 0.547 (< 0.80) | Full, blunt ends no yard would build |
| 7 | hull generator | Cb bisection returned the bracket bound while reporting success | Returned k = 1.2, Cb = 0.78, "converged" | Wrong ship, confident output |
| 8 | hull generator | `np.unique(..., return_inverse=True)` result reshaped instead of applied to `T` | `inv[T]` vs `inv.reshape(T.shape)` | Corrupt topology |
| 9 | mesh | Ring deduplication removed coincident points | Non-uniform ring counts broke stitching | Holes in the shell |
| 10 | mesh | Cap apex taken from a zero-initialised row | Cap centroid at the origin | Wrong enclosed volume |
| 11 | mesh | Cap apex not on the ring plane | "Planar" cap was a cone | Wrong volume integral |
| 12 | mesh | Coincident stem/transom vertices never welded in memory | 520 boundary edges: closed on disk, open in memory | Downstream solvers fail non-deterministically |
| 13 | mesh | Degenerate triangles included in the manifold check | Edge multiplicity 4 and 6 → "not watertight" | False rejection of a valid hull |
| 14 | **third-party solver** | 522 degenerate triangles fed to `navaltoolbox` | Volume −19%, BMt +19% versus the same solver on the cleaned mesh | A correct tool reporting wrong numbers |
| 15 | clipper | Two-inside case emitted with reversed winding | Opposite faces cancelled; unit cube gave 0.000 instead of 0.500 | Every integral silently zero-ish |
| 16 | clipper | Signed distances not rotated with the vertices | Box volume 9,200 m³ instead of 12,000; **COB_y = −2.28 m on a hull symmetric about y = 0** | Asymmetric buoyancy on a symmetric ship |
| 17 | clipper | Tetra sum used on an *open* clipped surface | Missing cap contributes (1/3)·d·Awp; box gave 8,000 m³ instead of 12,000 | Passed a z = 0 test while failing every real draft |
| 18 | clipper | Waterplane polygon second moment divided by 6 instead of 12 | BMt exactly 2× the analytic value | GM wrong by metres |
| 19 | clipper | Hand-derived first-moment quadrature omitted the centroid term | COB = (600.2, −2.0, −14.6) m instead of (50, 0, 3) | Nonsense centroids |
| 20 | hydrostatics | `vol_cob_at_draft` returned the raw moment | KB reported as 36,000 m | Off by a factor of volume |
| 21 | hydrostatics | Moment not shifted back from the integration frame | All centroids offset by −d·n | Wrong KB, LCB, LCF |
| 22 | hydrostatics | `at_draft` used the wrong plane offset | Box volume 8,000 m³ | — |
| 23 | hydrostatics | **Heel built as a rotation about z instead of the longitudinal x-axis** | `R[2,:]` trivially (0,0,1); normal independent of heel | **Every GZ computed at zero heel while all upright hydrostatics stayed exact** |
| 24 | hydrostatics | Plane normal taken as `R[2,:]` (third row) instead of `R[:,2]` (third column) | Same symptom as #23, different cause | Same |
| 25 | hydrostatics | Composition order `Ry@Rz` instead of `Rx@Ry` | Third row again independent of heel | Same |
| 26 | hydrostatics | Pitch matrix transposed | Bow went UP for positive trim | Every reported trim sign inverted |
| 27 | hydrostatics | `submerged()` clipped the *unrotated* mesh | cob_y = −0.59 at +5° heel (wrong direction) | Negative righting arms |
| 28 | hydrostatics | Centre of buoyancy not un-rotated back to hull coordinates | cob_z pinned at G.z; GZ(90°) = 5.26 m | GZ curve meaningless at large angles |
| 29 | hydrostatics | GZ sign convention | −0.464 m at 5° against +0.598 m | Stable ship reported as unstable |
| 30 | equilibrium | `zeta` seed used `vcg` and later `draft − vcg` instead of `vcg − draft` / `−draft` | Newton started with the hull nearly out of the water | Trim pinned at the ±5° step clip for every condition |
| 31 | equilibrium | Newton step sign (`solve(J, r)` vs `solve(J, -r)`) | Divergence into the clip | Trim = 5.000° on all five conditions |
| 32 | loading | Cargo zone started at 0.23·Lpp | LCG 8.5 m forward of LCB | **No achievable trim** — a physical design error, not a code error |
| 33 | loading | Fuel capacity 798 m³ (≈ 790 t) | 12,000 nm trade needs ≈ 2,800 t | A ship that cannot carry its own fuel |
| 34 | structure | Mixed quadrature: lumped weights as m/dx spikes, integrated by the trapezoid rule | Half of every lumped mass vanished; ΣW = 229,000 kN instead of 458,000 | Residual force 2,451 kN; SWBM = −2.4e6 kN·m |
| 35 | structure | Buoyancy taken at even keel while weights sat at the trimmed equilibrium | Residual moment 1.22e6 kN·m; vertical force balanced perfectly | Only the *moment* check caught it |
| 36 | structure | Wave BM formula mis-transcribed from memory | 1.52e8 kN·m (74× too large) → Z_req = 8.6e11 cm³ | Absurd scantlings, or a "correction" fitted until plausible |
| 37 | structure | Same, after a "units fix" | 152 kN·m (13,000× too small) | Under-designed hull girder |
| 38 | structure | Same, third transcription with C_w | 3.52e5 kN·m, inconsistent with both σ_allow and the parent band | — |
| 39 | structure | Required-Z allowable inconsistent with the parent-ship Z band | Z_req 1.84e7–2.47e7 cm³ vs real Handysize 1.4–2.0e7 | Two "authoritative" numbers that cannot both be right |
| 40 | powering | Katsui form factor mis-transcribed | 1+k = 279.7 (physically 1.3–1.6) | Frictional resistance 200× too high |
| 41 | powering | SWBM self-test used a simply-supported formula for a free-free beam | Asserted a non-zero midship BM that is *exactly zero* for symmetric quarter loads | The integrator was right; the test was wrong |
| 42 | powering | Holtrop–Mennen wave resistance "implemented" | ~30 lines of self-cancelling placeholder algebra | A number with a citation it did not deserve |
| 43 | explore | Steel take-off: stray `/1000` | 279 t of hull steel on a 9,062 t lightship (3.1%) | Impossible weight report |
| 44 | explore | Steel take-off extrapolated the midship *girder* area along the length | Confuses a strength quantity with a mass quantity; ~2× the real steel | Wrong cost and wrong lightship |
| 45 | explore | Same, again: `* 1000` on a tonnes→m² conversion | 5,002 m² instead of 5.0 m² | Caught only by the range gate |
| 46 | hull | `displaced_volume(p, draft)` silently integrated to `p.draft` | "Volume at 10.185 m" returned the value for 10.500 m | A 4% error hiding inside a verification table |
| 47 | crosscheck | GZ compared as a percentage at φ = 0° | "−200% disagreement" between 1e−5 and −1e−5 | A fabricated crisis that masks real ones |
| 48 | reviewer gate | Three candidates all scored 88.51 | "selected: C-full-ends" was arbitrary | **A gate that cannot discriminate is theatre** |

## What the gates were

Four mechanisms caught these, in roughly this order of value:

1. **Closed-form ground truth.** An analytic prism (100 × 20 × 10 m, draft 6 m) with volume,
   KB, Awp, BMt, BMl, LCF and LCB all known exactly. Both solvers reproduce it to 0.0000%.
   Caught #15–#22, #24–#26.
2. **A second independent implementation.** Every hydrostatic value is computed twice, by a
   from-scratch divergence-theorem solver and by `navaltoolbox`, and the disagreement is
   printed. Caught #14, #16, #23, #27–#29.
3. **Physical plausibility bands.** Cm ≤ 1, Cp inside the type band, C_w inside 2.0–10.75,
   M_vw inside a parent-ship band, hull steel 55–95% of lightship, implied mean structural
   area 2–12 m². Caught #4, #6, #36–#40, #43–#45.
4. **Equilibrium identities.** Σq = 0 and Σq·(x − LCG) = 0 on the load curve; ΣW = Δ·g
   exactly. Caught #34, #35.

The single most instructive one is #23. Heel was implemented as a rotation about the
**vertical** axis rather than the longitudinal axis, so the waterplane normal never tilted.
Every upright hydrostatic — volume, KB, Awp, BMt, BMl, LCF, LCB — was *exactly correct*,
and the entire stability assessment was computed at zero heel. Nothing in the upright
output could reveal it. Only a second implementation disagreeing on GZ did.

## What was refused rather than guessed

These are recorded as OPEN in the design record, with an owner and an action:

- **Vertical wave bending moment** (#36–#39). Three transcriptions, three different wrong
  answers, all caught. Now returns `status: OPEN` plus the reason and the action required.
- **Holtrop–Mennen wave resistance** (#42). Deleted. Wave resistance is a declared 15% ± 8%
  allowance on R_F, tagged ESTIMATE, with an instruction to replace it.
- **Katsui form factor** (#40). Deleted. 1+k = 1.45 (band 1.30–1.60), tagged ESTIMATE.
- **2008 IS Code weather criterion**. Needs the tabulated wave-slope coefficients X1, X2,
  the roll-radius coefficient k and the standard roll-period formula. `iscode.py` computes
  the unambiguous parts (PW1, PW2, the areas) and *refuses* K. A separate function
  `weather_criterion_with_supplied_roll` accepts a roll angle from an authoritative source,
  so the boundary cannot be crossed by accident.

Refusing is not a gap in the system; it is the system working. An OPEN item with a named
owner is safe. An estimate wearing a rule citation is not.

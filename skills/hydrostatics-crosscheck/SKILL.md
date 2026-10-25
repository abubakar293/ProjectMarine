---
name: hydrostatics-crosscheck
description: Computes hydrostatics, equilibrium and GZ curves with two independent solvers and prints the disagreement per quantity - the method that caught the zero-heel defect no upright check could see. Use for every hydrostatics, stability or equilibrium computation, and when adopting any new geometry or stability tool.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: concept
  stage: S3
---

# Hydrostatics Crosscheck

One solver is an assumption. Two independent solvers printing their disagreement is a
measurement. This skill is how the reference stack caught its worst defect.

## Procedure

1. **Ground truth first.** Both solvers must reproduce an analytic prism EXACTLY
   (100×20×10 m at 6 m: vol 12,000 m³, KB 3.000, Awp 2,000, BMt 5.5556, BMl 138.889,
   LCF/LCB 50.00). Clip at non-zero z — at z=0 the missing-cap error vanishes identically
   and a broken integrator passes (defect #17). Also assert conventions: upright normal
   (0,0,1); +heel tilts the normal to the low side; +pitch drops the bow; and **n must
   depend on heel** — an implementation whose normal is heel-independent computes every GZ
   at zero heel while all upright values stay perfect (defect #23, the worst in the log).
2. **Establish each tool's unit convention empirically**: run a known case, read back what
   came out. The reference third-party solver returns tonnes at water_density=1.025 and
   kilograms at 1025.0, and its gz_curve wants mass in the matching unit — assuming kg
   floated the ship 1000× too light and looked like a solver disagreement.
3. **Clean the mesh** (weld, drop degenerates, manifold-check) before any third-party solver.
4. Compute upright hydrostatics at all required drafts; GZ at constant displacement
   (re-solving sinkage at each heel); equilibrium trim per loading condition (Newton on
   (zeta, trim) with residuals and convergence reported — a trim value pinned at a round
   clip like exactly 5.000° is a divergence fingerprint, defect #30/31).
5. **Print the full disagreement table** — per quantity, both values, absolute and % delta,
   near-zero quantities compared by absolute delta against a scale (GZ(0°) of 1e−5 vs −1e−5
   is agreement, not −200%).

Tolerance sources: the 0.01% upright and 0.5%/1% GZ bands are the reference build's measured
two-solver agreement (VERIFIED by CI on every push), not standards; re-derive them for your
own solver pair and record the measurement as the source.

## Gates

- Upright agreement < 0.01% on volume, KB, Awp, LCF, BMt, BMl, LCB.
- GZ agreement < 0.5% up to 40°, < 1% to 60°; document the larger-angle tolerance and stop
  quoting large-angle GZ beyond two significant figures.
- Small-angle identity: fitted dGZ/dφ over φ ≤ 15° equals GM within 3% (this cross-checks
  the GZ machinery against the upright machinery — two different code paths).
- Equilibrium: |volume residual| < 1e-6 relative and |LCB − LCG| < 1e-4 m, converged flag true.
- Draft monotonic in displacement; KB monotonic in draft; BMt decreasing for wall-sided forms
  (a non-monotonic hydrostatics table is a geometry or integration defect).

## When the solvers disagree

Do not average, do not pick the nicer one. Bisect: same mesh? same draft definition
(baseline vs waterline)? same density? same rotation convention? The reference log shows the
disagreement was right five times — each time one implementation had a defect
(#15–#22, #27–29). The tool that was exact on ground truth and wrong on the hull was
poisoned by the hull's degenerate triangles (#14); the one wrong on both was broken itself.

## Prohibitions

- Never ship single-solver numbers when a second implementation is available; if only one
  exists, the record says REDUCED ASSURANCE and names the missing check.
- Never compute a derivative-based quantity (Awp, BMt from d²V) as the primary method when
  the direct waterplane-polygon integral is available — finite differences of a clipped
  volume produced BMt = 0.333 vs 5.5556 on the analytic box during development.

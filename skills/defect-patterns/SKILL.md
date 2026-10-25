---
name: defect-patterns
description: Catalogue of 48 real, silently-plausible defects found in agent-written naval architecture code, with the symptom that exposed each and the gate that prevents it. Use BEFORE writing geometry, hydrostatics, stability, structural integration, unit-conversion or mesh code; and when reviewing any such code. Also use when a number looks right but something feels off.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: verification
  stage: cross-cutting
---

# Defect Patterns — read before writing geometry or physics code

Every pattern below shipped plausible output when it was live. They are grouped by the
mechanism that catches them. Full table with costs: docs/DEFECT-LOG.md.

## Rotation and frame defects (the silent killers)

- **Heel about the wrong axis.** Heel is rotation about the LONGITUDINAL x-axis. Built as a
  z-rotation, the waterplane normal never tilts: every upright hydrostatic stays exactly
  right and the whole GZ curve is computed at zero heel (#23). *Catch: a second solver
  disagreeing on GZ; convention assertions (n must depend on heel).*
- **Row vs column.** The hull-frame waterplane normal is R[:,2] = Rᵀe₃, not R[2,:]. For a
  rotation they differ in off-diagonal signs (#24). *Catch: numeric probe of both.*
- **Composition order.** Rx(heel)·Ry(pitch) vs Ry·Rx: one makes the third row independent of
  heel (#25). *Catch: assert n changes with heel.*
- **Transposed pitch matrix.** Sends the bow UP for "positive" trim; flips every trim sign
  (#26). *Catch: assert R·(1,0,0) has z < 0 for bow-down convention.*
- **Clipping the unrotated mesh** while believing the plane normal encodes heel (#27), and
  **forgetting to un-rotate the centroid** back to hull coordinates (#28). *Catch: GZ(90°)
  pinned at G.z is physically impossible.*
- **Hand-derived closed forms.** Two consecutive hand derivations of one matrix row were both
  wrong and both self-consistent. Derive once, then assert against NUMPY, not against your
  algebra. Better: assert physical properties (+heel drops starboard; +pitch drops bow; n is
  unit; n depends on heel) instead of symbolic forms.

## Volume-integration defects

- **Winding reversal** in the two-inside clipping case: opposite faces cancel, unit cube
  integrates to 0.0 instead of 0.5 (#15).
- **Distances not rotated with vertices**: intersection points land on wrong edges; a
  y-symmetric hull reports COB_y = −2.28 m (#16).
- **Open surface treated as closed**: the tetra sum over a clipped hull omits the waterplane
  cap, worth (1/3)·d·Awp — zero only when the plane passes through the origin, so a z=0 test
  passes while every real draft is 4,000 m³ wrong (#17). *Fix: shift mesh by −d·n first.*
- **Wrong moment quadrature**: the hand-derived surface rule missed the centroid term;
  correct tetra moment is det·(a+b+c)/24 (#19). Polygon second moments divide by **12**,
  not 6 — BMt comes out exactly 2× otherwise (#18).
- **First moment returned instead of centroid** (missing /vol: KB reported as 36,000 m)
  (#20); **moment left in the shifted frame** (#21).

## Mesh defects

- Coincident vertices welded on disk but not in memory → closed STL, open mesh, 520 boundary
  edges (#12). Weld at generation, check with degenerate triangles excluded (#13).
- **Degenerate triangles poison third-party solvers**: 522 zero-area triangles changed a
  CORRECT solver's volume by −19% and BMt by +19% (#14). Clean meshes before handing them
  over; always.
- np.unique(return_inverse) gives a per-VERTEX map: apply as inv[T], never reshape (#8).

## Solver-iteration defects

- **Wrong seed sign** for a floating attitude: Newton starts with the hull out of the water
  and slams into its step clip; every condition reports exactly trim = 5.000° — a suspiciously
  round number is a fingerprint of clipping (#30, #31).
- Report convergence status and residuals; treat a pinned-at-clip value as divergence.

## Quadrature and equilibrium

- **Mixed rules**: lumped weights as m/dx spikes integrated by trapezoid → half of every
  lump vanishes (#34). One rule everywhere, asserted by Σ identities.
- **Even-keel buoyancy with trimmed weights**: force balances to 6 digits, moment off by
  1.2e6 kN·m (#35). Check BOTH identities.
- A free-free beam's midship BM under symmetric quarter-point loads is **exactly zero**; the
  first self-test asserted a simply-supported formula against it and "failed" the correct
  integrator (#41). Test expectations need validation too.

## Units and conventions

- Third-party density/mass conventions: same solver returns tonnes at water_density=1.025
  and kilograms at 1025.0; its gz_curve wants mass in the matching unit. Assuming kg floated
  the ship 1000× too light and looked like "solver disagreement". Establish empirically,
  comment at the call site.
- Stray ×1000 or /1000 in chains: caught twice (#36, #43, #45). An order-of-magnitude gate
  on the RESULT is the only reliable net.
- A function that "takes draft" but silently integrates to the design draft (#46): make
  every physical argument explicit; default-argument convenience hides 4% errors inside
  verification tables.

## Design-physics defects (not code bugs — the design is wrong)

- Cargo zone starting at 0.23·Lpp put LCG 8.5 m forward of LCB: **no achievable trim** (#32).
  Check LCG vs LCB right after compartmentation.
- Fuel capacity 790 t for a 12,000 nm trade needing ~2,800 t (#33): a ship that cannot carry
  its own fuel is not a design, however good its stability looks. Capacity checks are design,
  not bookkeeping.
- Strength quantity used as mass proxy: extrapolating the midship girder area along the
  length double-counts steel — holds are transversely framed (#44).

## Pre-flight checklist (paste into your process)

1. Ground-truth prism exact BEFORE any real hull. 2. Convention assertions on every
rotation. 3. Two solvers, disagreement printed. 4. Mesh: welded, degenerates removed,
closed, outward. 5. One quadrature rule, Σ-identities asserted. 6. Unit convention
established empirically per tool, commented at the call site. 7. Band gate on every
order-of-magnitude-sensitive result. 8. Round numbers in outputs (5.000°, −20.000°) are
clipping fingerprints. 9. LCG vs LCB after compartmentation. 10. Capacity vs mission before
any optimisation.

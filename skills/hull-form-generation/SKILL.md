---
name: hull-form-generation
description: Generates fair, watertight, parametric hull geometry from principal dimensions and form coefficients - offsets table, lines plan, cleaned mesh, STEP - with physical postconditions enforced at generation time. Use when creating or modifying any hull surface, and before any hydrostatics, CFD or structural meshing.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: concept
  stage: S2
---

# Hull Form Generation

**Geometry is code.** A hull exists as parameters + generator, never as a hand-edited file.
If you cannot re-run the generator and get the byte-identical mesh, you do not have a hull;
you have a rumour of one.

## Procedure

1. Generate from dimensions.json: longitudinal distribution (run/PMB/entrance fractions,
   section-area coefficient c(x)), transverse section family (flat bottom, bilge radius,
   rise of floor, side flare, sheer), stem/transom treatment.
2. **Solve for the target, don't scale the constraint**: to hit Cb, solve the fullness
   exponent — never multiply the beam. B is a terminal/lock constraint; a global beam
   multiplier silently redefines it (defect #3: "B = 29.8 m" became 35.8 m).
3. **c(x) must BE the section-area coefficient.** If you shape waterlines by a length-varying
   exponent, actual areas scale as c^0.5-ish and the ends come out far fuller than the
   distribution claims (defect #5: A/Am = 5.1·c near the stem). Make sections geometrically
   similar, scaled by √c, so area(x) = c(x)·Am exactly — then verify by integration.
4. Fairness: curvature combs on sections/waterlines/buttocks; no sign flips; Cp distribution
   smooth (a wavy Cp is a wave-making hump waiting for the towing tank). Export the offsets
   table (stations × waterlines) and a lines-plan DXF.
5. Mesh for analysis: weld coincident vertices AT GENERATION (a mesh closed on disk but open
   in memory breaks downstream solvers non-deterministically — defect #12); drop degenerate
   triangles before handing to any third-party solver (522 degenerates changed a correct
   solver's volume −19%, BMt +19% — defect #14); assert watertight (every edge in exactly
   two non-degenerate triangles) and outward normals (positive enclosed volume).
6. Export the watertight STL/STEP + the generator + params + SHA-256 into the design record.

## Postcondition suite (raises, never warns)

- Cb matches target to 1e-4 (solver converged — a bisection returning its bracket bound
  while claiming success is defect #7; assert |f| < tol at exit).
- Cm ≤ 1.0 strictly, and Cm, Cp inside the type band (defect #4: Cm = 1.057 "passed").
- c(x) ∈ [0,1] everywhere; longitudinal fractions sum < 1 (else the PMB has negative length
  — defect #2, which produced Cb = 0.344 via a silently >1 coefficient).
- Solved fullness exponent inside a physical band (a degenerate 0.55 means the ends are
  absurdly full — defect #6; fix the distribution, don't force Cb).
- Mesh: watertight, outward, volume converging monotonically from below with refinement
  (inscribed faceting; −2% at coarse, −0.8% at fine was the reference trajectory).
- Volume from mesh vs volume from parametric section integration agree within the
  discretisation tolerance you declared.

## Prohibitions

- No CAD-by-conversation: "move the bow slightly" means a parameter change + regeneration,
  never a mesh edit.
- No fairness by eyeball alone — combs and Cp plots are artefacts in the record.
- No mesh to a third-party solver before the clean step (weld + degenerates + manifold check).
- A stem/transom that collapses to a line is acceptable for analysis meshes IF the degenerates
  are removed and the record says so; for production surfaces, model the actual flat/butt.

---
name: cad-drawing-generation
description: Generates every ship drawing type accurately from the single frozen geometry model - lines plan, general arrangement, midship section, capacity plan, hydrostatic and GZ curves, shell expansion, structural and production drawings - as DXF/SVG/PDF via ezdxf, FreeCAD TechDraw or paid CAD APIs, with title blocks carrying the geometry hash and READ-BACK verification that measures the finished drawing against the model. Use whenever a drawing is needed, at S2-S9, and whenever geometry changes invalidate drawings.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.2.0"
  domain: drawing
  stage: S2-S9
---

# CAD Drawing Generation

**A drawing is a rendered view of the model, never a second source of truth.** Hand-drawn
(or hand-edited) drawings are where the model and the paperwork diverge — and divergence
between the stability booklet and the loading computer, or between nesting files and the
hull surface, is how real projects lose weeks and trials.

## Drawing taxonomy by stage

| Stage | Drawings | Source |
|---|---|---|
| Concept (S1–S2) | principal-dimension sketch, section-area/Cp curves | sizing record |
| Preliminary (S2–S4) | **lines plan** (body/profile/half-breadth), hydrostatic curves, bonjean curves, **GZ curves per condition**, speed–power sheet plots | hull generator + solvers |
| Contract (S4–S7) | **general arrangement**, **midship section**, **capacity plan**, tank arrangement, machinery-space arrangement, fire control plan, escape plan, load-line/tonnage marking, profile + deck structural plans | master model + arrangement data |
| Production (S8) | shell expansion, block division/assembly drawings, piece drawings, nesting layouts with NC data, weld maps, penetration schedules | production model + yard standards |
| Systems (S6) | P&IDs/schematics, pipe isometrics, cable routes, HVAC layouts | systems model |
| Delivery (S9) | as-built set, booklet figures, trial-record plots | final record |

## Generation stack (free-first, per `toolchain-selection`)

- **ezdxf** (Python, DXF R2010 read+write): lines plans, curve sheets, sections, title
  blocks as text+mleader entities, layers per line-type convention. The reference
  `drawings.py` generates and — crucially — **reads back** its own DXF.
- **matplotlib/SVG**: curve sheets for reports (hydrostatics, GZ, power).
- **FreeCAD + TechDraw** (fully scriptable): 3D→2D projected views, hatching, GD&T-ish
  annotation; Python macros regenerate on model change.
- **pythonocc/OpenCascade**: STEP-based sectioning and projection when the master model is
  solid CAD.
- **Paid paths**: AutoCAD .scr/AutoLISP for yard-standard sheets; Rhino.Compute for NURBS
  views; AVEVA/CADMATIC/FORAN drawing modules for the production set (the agent drives the
  API and verifies output, per `toolchain-selection`).
- Documents: Typst/LaTeX for booklets embedding the generated figures.

## Conventions (cite the standard the yard/class uses; defaults below)

- ISO 128 line conventions, ISO 7200 title blocks; first-angle projection unless the yard
  standard says otherwise; metric, units on every dimension; scales stated per view
  (lines plan commonly 1:50/1:100, GA 1:100, midship 1:50, details 1:10/1:25).
- Ship-drawing conventions: body plan stations numbered from AP, waterlines from baseline,
  buttocks from CL; half-breadth plan forward-aft split convention; centreline dash-dot.
- Every sheet: drawing number per the yard index, revision letter, geometry SHA-256 (first
  16 hex) of the source model, generation timestamp, "GENERATED FROM MODEL — NOT TO BE
  SCALED" where applicable, and the checker/approver signature boxes (the humans sign; the
  agent never fills them).

## Per-drawing essentials

Gates per sheet type:

- **Lines plan**: stations, waterlines, buttocks from the SAME offsets table the hydrostatics
  used; fairing spot-checks (curvature combs) attached as an appendix sheet.
- **GA**: zones, tank names/numbers matching the tank model exactly (name-set equality is a
  gate), dimensions chain-checked (Σ compartment lengths = Lpp), air-draft and visibility
  annotations from the computed checks.
- **Midship section**: scantling table on the sheet matching the structural record row-for-row;
  material grades and corrosion additions stated.
- **Capacity plan**: volumes/sounding points from the tank model; totals equal the stability
  record to the litre (same source, so equality is a consistency check on the generator).
- **Curves sheets**: axis ranges include the operating envelope; controlling conditions
  labelled with their record IDs.
- **Shell expansion / nesting (S8)**: plate seams follow the stock list; every contour
  round-trips against the hull surface within tolerance; NC output dry-run verified against
  the machine dialect.

## Gates

- Read-back verification passes on EVERY sheet before it enters the package (the generator
  raises otherwise): curve geometry measures back to the model within 1e-3 m at model scale;
  entity counts match the intended station/waterline sets; title-block geometry hash equals
  the frozen record hash.
- Sheet set complete for the stage (concept: lines plan + curves; contract: + GA, midship,
  capacities; production: + shell expansion, block drawings).
- Stale-sheet detection: any sheet whose title-block hash differs from the current frozen
  geometry is quarantined automatically, never shipped.

## Read-back verification (the pattern that makes drawings trustworthy)

After writing a DXF: **parse the file back** (ezdxf read), extract the geometry entities,
and measure them against the model:

- half-breadth plan: re-measure y-extents at sampled stations/waterlines → compare to the
  offsets table (tolerance: one plot resolution, e.g. 1 mm at scale);
- body plan: station curve max-breadths vs model;
- dimension entities: text value vs measured entity geometry (a dimension that disagrees
  with the lines it annotates is a defect);
- title block: geometry hash matches the current record.

The reference implementation runs this loop on every regeneration and the fleet has an agent
whose only job is drawing–model consistency. A drawing that cannot be machine-verified
against its source is a rumour.

## Revision discipline

Geometry hash changes → all derived drawings are stale by construction. The record marks
stale sheets automatically; regeneration is one command; superseded revisions move to an
archive folder, never deleted (class and yard audits walk revisions).

## Prohibitions

- No manual edits to generated sheets (fix the generator or the model).
- No dimension typed by hand that the model could compute.
- No drawing released whose title-block hash mismatches the frozen model.
- No signing boxes filled by the agent — approval is a human act (gate #3/#5).

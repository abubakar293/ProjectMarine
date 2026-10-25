---
name: production-design-handoff
description: Prepares the design for the shipyard - block and panel division against real yard limits, nesting and cutting inputs, weld and tolerance strategy inputs, assembly sequence and erection plan data, and the ERP-ready work-package structure. Use at S8 and during contract/production design.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: production
  stage: S8
---

# Production Design Handoff

Contract design says what the ship is; production design says how THIS yard builds it. This
skill covers the data handoff — the yard's own production-design department (or the same team
wearing that hat) executes it.

## Inputs you must have (else request via shipyard-data-requirements)

Yard crane/dock limits, panel-line dimensions, standard stock, qualified welding processes,
nesting software input conventions, ERP work-package schema, build strategy preference
(zone vs system building; one-side-welding practice).

## Block & panel division

- Divide against MAX block weight (crane-limited) and panel-line size; keep welds out of
  high-stress and fatigue-critical details (coordinate with `structural-fe-verification`
  hot spots); minimise in-dock weld length (erection joints are the expensive metres).
- Block boundaries respect the structural model's bracket/penetration schedules — a
  boundary through a penetration cluster is a build defect waiting.
- Sequence: panel → sub-assembly → block → grand-assembly (if crane allows) → erection;
  the sequence constrains outfitting completeness per block (the "outfit early" percentage
  is a cost lever the yard cares about — capture it as a per-block target).

## Cutting and forming inputs

- Plate nesting: expanded shell from the SAME frozen hull surface (hash-linked — nesting
  from a stale hull is the production face of revision drift); bevel and marking data per
  the yard's CNC conventions; remnant and offcut strategy.
- Curved-shell plates: developability check against the hull form; cold-forming limits vs
  the yard's presses; hot-bending list with temperatures per material grade.
- Profile nesting and cutting lists from the standard stock list — non-standard sections are
  a procurement lead-time item, flagged to `cost-estimating` and the schedule.

## Welding and tolerance strategy inputs

- Weld-schedule data: groove types per joint class from the yard's qualified WPS set; weld
  length totals per block (the cost driver); distortion-control notes for thin-panel zones
  (sequence, stiffening, heat-input limits) — these are inputs the yard validates, not
  instructions from the design office.
- Tolerance/compensation strategy per the yard standard (add-ons for erection, trim of
  butts) — design draws NOMINAL; the yard applies compensation. Say so on every drawing.

## Work packages and ERP

- Decompose into the yard's work-package schema (hull, outfit, machinery per zone/block/
  stage) with quantities from the model (steel t, weld m, paint m², outfit items), so
  planning and cost roll up from ONE quantity source — the design record.
- Drawing index (which drawing serves which package) via `documentation-package`.

Rule-of-thumb targets (yard-calibrated; ESTIMATE until the yard's standards land): erection
weld metres per tonne of block steel below the parent's; outfitting completeness at block
stage >= 60-80% for machinery-space blocks; grand-assembly only where the crane chart shows
>= 1.25x dynamic factor on the lifted mass.

## Gates

- Every block ≤ crane limit with the rigging factor; every panel ≤ line dimensions.
- Weld length total within the cost model's assumption (else re-run `cost-estimating`).
- Nesting input regenerates from the hashed geometry (determinism check).
- No erection joint through a fatigue-critical detail without the structural engineer's sign-off.

## Prohibitions

- No division against assumed crane limits — DR item or nothing.
- No "the yard will figure it out" for anything the record must carry (quantities, sequences).

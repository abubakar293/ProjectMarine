---
name: weight-control
description: Manages the weight record from estimate to as-built - weight groups with margins, KG/VCG/LCG build-up, steel take-off with plausibility bands, and revision tracking against the stability and strength models. Use from S1 through production, and at every design revision.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: compliance
  stage: S1-S8
---

# Weight Control

Weight is the design's running score. A 1% displacement error shifts draft, power and EEDI;
a KG error shifts every stability verdict. Control it from the first estimate to the inclining
test.

## Structure

Weight groups (steel hull / outfitting / machinery, then equipment and loads) each with:
mass, LCG, VCG, TCG, margin %, status (ESTIMATE / vendor datasheet / measured), and the
revision history. Margins are explicit per group — a zero margin means the weight report
cannot show growth (fleet finding: zero-margin groups are MAJOR).

## Estimation methods by stage

- S1: parent-ship regressions and cube-number/style methods — tagged ESTIMATE with the
  source parent named.
- S5+: steel from the structural model (see the take-off caution below); outfit from the
  systems equipment lists (vendor masses as they land); machinery from datasheets.
- Production: as-invoiced/as-installed with the inclining test closing the loop.

## Steel take-off (two defects live here)

1. Hull steel comes from the lightship weight group scaled by the steel fraction
   (bulk carriers ~0.72–0.82 of lightship) — NOT from the midship girder area extrapolated
   along the length. The girder area is a STRENGTH quantity; holds are transversely framed
   and the midship station is the most heavily structured one — extrapolation double-counts
   (defect #44).
2. Unit chain: tonnes / (t/m³ · m) = m². A stray ×1000 turned 5.0 m² into 5,002 m²
   (defect #45). Band-gate the result: implied mean structural area 2–12 m² for merchant
   hulls; hull steel 55–95% of lightship; midship-girder-to-mean ratio 0.8–3.0.

## The loops weight feeds

- Stability: KG/VCG per condition (`stability-intact` re-runs on every weight revision —
  automated, hashed inputs).
- Strength: load curves from the same weight records (`structural-loads` — one source;
  a weight set that exists in two spreadsheets is a defect).
- Powering: displacement at the trial and EEDI conditions.
- Cost: steel quantity drives the material cost line (`cost-estimating`).
- Production: the weight report tracks actual vs predicted per zone/block — the feedback
  that calibrates the next ship's estimates.

## Gates

- ΣW = Δ·g asserted at assembly (this caught defect #34's missing half).
- Budget closes ±2% at S1; margin trends reported per revision (growing margin = growing
  design, flag early).
- Steel fraction and area bands above.
- Every group has status + source; no unsourced masses.
- KG used in stability matches the weight record revision (hash-linked).

## Prohibitions

- No "typical" lightship without the parent named.
- No weight reduction accepted into the record without the stability/strength re-run it triggers.
- No inclining-test surprise culture: if margins were honest, the test confirms; if it
  doesn't, the process gets an audit, not a shrug.

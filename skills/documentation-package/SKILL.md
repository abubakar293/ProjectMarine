---
name: documentation-package
description: Assembles the owner- and class-facing package - specification, stability booklet, calculation reports, compliance matrix, drawing index, weight and cost reports - generated reproducibly from the design record with hash-linked revisions. Use at S9 and at every submission milestone.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: delivery
  stage: S9
---

# Documentation Package

Documents are GENERATED from the design record, never hand-edited afterwards. A hand-edited
PDF is where the record and the deliverable diverge — and divergence between the stability
booklet and the loading computer is a real-world cause of trial disputes and detention findings.

## The package

1. **Specification** (hull / machinery / outfitting / electrical / safety): every clause
   traceable to a brief requirement ID; class and flag notations listed exactly as they will
   appear on the certificate application.
2. **Stability booklet**: hydrostatics, cross curves, ALL approved load cases, intact and
   damage results, tank sounding and free-surface tables, loading instructions and limits.
   Amendment number matches the loading-computer database; the geometry hash it was computed
   from is printed in the front matter. Class/flag-approved before it goes aboard — the agent
   assembles, the administration approves.
3. **Calculation reports**: speed-power (with the margin columns and ESTIMATE tags visible),
   structural (loads, scantlings, FE summaries with convergence evidence), EEDI technical
   file (inputs, method, result per the guidelines' required structure), EEXI where
   applicable, tonnage and load-line submissions.
4. **Rule compliance matrix** from `class-statutory-compliance` — including its OPEN items.
   An incomplete matrix submitted as complete is fraud-adjacent; the OPEN list goes with it.
5. **Weight report** with revision history and margins.
6. **Cost estimate** with basis/class/exclusions (from `cost-estimating`).
7. **Drawing index**: every drawing, revision, source-file hash, and the geometry version it
   was produced from. Lines plan + offsets table in both human (DXF/PDF) and machine
   (CSV/STEP) form.
8. **Open-items register**: consolidated, with owners and actions — the same JSON the
   traceability uses, rendered human-readable. This is the document that makes the package
   honest.

## Generation discipline

- One build command regenerates the whole package from the record (Typst/LaTeX for reports,
  python-docx/openpyxl for owner-facing tables, ezdxf for line-work, plotly/matplotlib for
  curves). The build is deterministic; the record's hashes appear in the artefacts.
- Figures/tables reference analysis runs by ID — if a run is re-executed, the document build
  picks up the new outputs and the revision increments. No figure is ever pasted.
- Language: computed values render with their units and provenance tags; ESTIMATE numbers
  keep their tags INTO the owner-facing document (an owner is entitled to see which numbers
  are soft; hiding tags in internal versions only is how soft numbers become hard promises).

## Gates

- Every number in every document traceable to a run in `analysis/` (the reviewer fleet
  spot-checks this: pick ten numbers, walk the chain).
- Booklet amendment == loading-computer DB version == geometry hash (three-way match).
- OPEN items in the package match the record exactly (diff, not eyeball).
- Package regenerates byte-identical from the record (determinism check in CI).

## Prohibitions

- No hand-editing generated documents; fix the generator or the record.
- No submission with a silent gap: OPEN items travel with the package.
- No ESTIMATE tag stripped on the way to the owner.

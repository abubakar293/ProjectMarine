---
name: structural-fe-verification
description: Direct structural verification by finite elements - midship-hold and full-cargo-hold models per the rule load cases, mesh convergence evidence, code checks, buckling and fatigue screening - with tool-drivingautomation patterns for Sesam/CalculiX/Code_Aster. Use at S5 for anything the rule formulas do not cover, high-utilisation zones, novel structure, or where the class requires direct calculation.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: structure
  stage: S5
---

# Structural FE Verification

## When FE, when formulas

Rule formulas cover standard zones of standard ships. Direct calculation is for: high-
utilisation areas, discontinuities (stools, brackets, hopper knuckles), non-standard types,
local loads formulas do not model (grab impacts, container lashing, crane outriggers), and
where the class notation demands it. The rule set tells you which load cases, boundary
conditions and acceptance criteria apply — from supplied text, cited.

## Model discipline

- Geometry FROM the design record's frozen model — not re-drawn. Hash it.
- Mesh: coarse global + fine local (hot spots at rule-specified element sizes); **convergence
  evidence in the record** (a mesh with no convergence study is not a result).
- Load cases: rule sea-going/harbour cases with the correct dynamic factors; pressure loads
  from the actual drafts of the governing conditions (link to `structural-loads`, same
  frozen displacement set — loads from a stale displacement invalidate everything).
- Boundaries per the rule (end restraint, symmetry); no invented springs "to make it converge".
- Material: grade per zone, k-factors, net dimensions with corrosion additions per rule.

## Tool automation patterns (agent-drivable)

- **DNV Sesam**: `dnv-sesam-commands` (PyPI) + DNV's open-source OneWorkflow orchestration
  example — GeniE modelling, HydroD loads, Sestra solve, code-check runs, all as Python
  command chains an agent can build, execute and parse; Sesam Manager supports batch.
- **Open FE**: CalculiX (.inp decks — the reference topology-optimisation pattern uses BESO
  coupled to CalculiX), Code_Aster (Python-driven), gmsh/netgen for meshing with convergence
  loops.
- **Commercial**: Nauticus Hull (CSR rule checks with compliance documentation), ABS tools
  for IACS UR local checks. Every commercial tool: validate against a closed-form case
  first (`verification-gates`), clean meshes before import (`hull-form-generation`).

## Checks

- Yield/utilisation per rule acceptance (screen colours lie; parse numbers).
- Buckling: idealised-buckling or FE per rule; utilisation < 1.0 with clause.
- Fatigue: rule S–N screening at the standard details; spectral assessment where the rule
  requires it — hot-spot stress with the rule's mesh and SCF treatment.
- Reporting: every check writes {clause_id, load case, location, result, utilisation,
  verdict} into the compliance matrix — evidence links, not adjectives.

Screening thresholds (ESTIMATE until the class guidance in hand says otherwise): buckling
utilisation 0.9 for first-pass triage — anything above goes to detailed check; hot-spot mesh
per the supplied class guidance (commonly ~50 x t_net at weld toes — from the rule text, not
from this sentence).

## Gates

- Convergence: result change < 5% (or the rule's tolerance) between the last two refinements.
- Global equilibrium of the FE both reaction sets vs applied loads (< 1%).
- No check "passed" without its clause ID and edition in the record.

## Prohibitions

- No re-classifying a member to make a utilisation disappear (fleet finding: the classic
  paper-over).
- No hot-spot results from a coarse mesh.
- No fatigue declared out of scope on a trade where it governs (handysize with grabs: it does).

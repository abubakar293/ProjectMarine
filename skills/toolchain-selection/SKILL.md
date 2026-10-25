---
name: toolchain-selection
description: Selects and integrates the software toolchain for a ship project - free-first ladders per domain (FreeCAD, OpenFOAM, CalculiX, gmsh, ezdxf, navaltoolbox, OpenProp, DeepNest), paid shipyard tools when available (Maxsurf, NAPA, Sesam, AVEVA, CADMATIC, FORAN, STAR-CCM+, SigmaNEST) with their scripting/API integration patterns, open data formats with round-trip verification, and licence honesty. Use when choosing tools, integrating a new solver or CAD system, exchanging data between tools, or when a user asks which software to use.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.2.0"
  domain: toolchain
  stage: cross-cutting
---

# Toolchain Selection

Two ladders, one rule: **free tools earn trust by validation; paid tools earn it the same
way** — a licence is not a certificate of correctness.

## Free-first ladder by domain

| Domain | Free (validated paths) | Notes |
|---|---|---|
| Hull modelling / NURBS | FreeCAD (+Ship workbench), pythonocc/OpenCascade, geomdl, rhino3dm (reader) | FreeCAD is fully Python-scriptable — an agent can drive it |
| Naval architecture | navaltoolbox (AGPL; hydrostatics/GZ/tanks), FreeShip++/DELFTship, Vessel.js, OpenProp | navaltoolbox cross-checked against the reference independent solver |
| Hydrostatics/stability (own code) | the reference `hydrostatics.py` pattern: divergence-theorem kernel + ground-truth prism | no licence, full control, fully testable |
| CFD | OpenFOAM (interFoam/overset, DTC/shipFoam), Xfoil (sections) | heavy but scriptable end-to-end |
| FE structural | CalculiX, Code_Aster, Elmer; gmsh/netgen meshing; PrePoMax as GUI | CalculiX is the deterministic backend in published agentic topology-optimisation work |
| 2D/3D drawings | ezdxf (DXF R2010 write+read), matplotlib/SVG, FreeCAD TechDraw, Typst/LaTeX docs | read-back verification needs a reader — ezdxf gives both |
| Nesting/cutting | DeepNest, SVGnest-class tools | verify kerf/remnant handling before production use |
| ERP/planning | Odoo | for the office side, not the drawing side |

## Paid-tool integration patterns (agent-drivable, not GUI-clicking)

An agent operates a paid tool through its **programmatic interface** or not at all:

- **DNV Sesam**: `dnv-sesam-commands` (PyPI) + OneWorkflow (DNV open source) — GeniE/
  HydroD/Sestra/code-checks as Python command chains; Sesam Manager batch mode.
- **DNV Nauticus Hull**: CSR rule checks with compliance documentation output.
- **Bentley Maxsurf**: community MCP server exists — hull modelling, tanks, intact+damage
  stability driven conversationally; verify its outputs against your ground truth like any
  other solver.
- **NAPA**: batch/manager scripting; **GHS**: run files (fully scriptable by design).
- **Orca3D**: Hull Assistant automation API.
- **Rhino**: rhino3dm (file I/O, free), Rhino.Compute / Rhino.Inside for headless geometry
  kernels; Grasshopper definitions as versioned parametric programmes.
- **AVEVA / CADMATIC / FORAN / Siemens NX**: .NET/vendor APIs; these platforms are where
  integrated-yard programmes live (e.g. the HD KSOE–Siemens single-3D-data-environment
  platform) — the agent's role is data-in/data-out and checks, not modelling by mouse.
- **STAR-CCM+ / ANSYS**: Java/Python macro record-and-replay; the agent writes the macro.
- **AutoCAD**: script files (.scr) / AutoLISP / .NET; DXF is usually the better exchange.
- **SigmaNEST / Lantek**: DXF/STEP in, NC out; verify post-processor output against the
  machine's dialect before anything is cut.

## Data exchange discipline

- Open formats only between tools: STEP AP203/242 (solid), IGES (legacy surfaces), DXF (2D),
  STL (analysis meshes), HDF5/CSV (results), IEC 81346-style designations where the yard uses
  them.
- **Round-trip verification on every handoff**: export → re-import → compare volume,
  bounding box, and a sample of surface points against the source. A STEP that silently
  drops a surface is a week of phantom downstream errors.
- One canonical geometry (the master model); every tool gets a derived copy tagged with the
  source hash. No tool becomes a second source of truth.

## Licence honesty (a safety rule, not legalese)

- Never bypass, crack, or "borrow" a licence for a paid tool. If the project cannot afford
  it, take the free ladder and state the assurance delta.
- Copyleft awareness: navaltoolbox is AGPL-3.0 — fine internally, but a hosted service
  linking it triggers source obligations; check before productising (fleet finding I10).
- Record tool + version + licence basis per run in the design record; an auditor (or the
  class) asking "what produced this number" gets a complete answer.

## Selecting for a project

1. List the decisions the project must make (from the pipeline stages).
2. Per decision, pick the cheapest tool whose **validation gap** is smaller than the
   decision's margin. Free tools win unless the gap is too wide or the class names a tool.
3. Check integration surface: scriptable > macro-able > GUI-only. A GUI-only tool is a
   human-in-the-loop step, and the plan says so.
4. Verify each selected tool against ground truth BEFORE the project's first real run.

## Gates

- Every tool in the chain has a recorded validation run (case, version, error vs truth).
- Every cross-tool handoff has a round-trip check.
- Licence basis recorded per tool; zero unlicensed usage paths anywhere in scripts.

## Prohibitions

- No "the yard uses X so X is right" — validation is per project, per version.
- No GUI-clicking workflows presented as automation (they are not reproducible).
- No proprietary format as the canonical geometry.
- No licence circumvention, ever — refuse explicitly and escalate.

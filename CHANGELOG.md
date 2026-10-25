# Changelog

All notable changes to this project. Format follows [Keep a Changelog](https://keepachangelog.com/),
versioning follows [SemVer](https://semver.org/).

## [0.2.0] - 2026-10-25

### Added
- 4 new skills: `simulation-suite` (validate-before-use simulation ladder, free tools first,
  paid-tool API patterns), `toolchain-selection` (free-first ladders per domain, paid
  integration patterns, data-exchange round-trip rules, licence honesty),
  `cad-drawing-generation` (full drawing taxonomy, model-based definition, title-block
  hashes, READ-BACK verification), `error-fix-loop` (root-cause protocol, prohibited
  "fixes", Definition of Done, finalization freeze mechanics). 33 skills total.
- `fe_beam.py`: Euler-Bernoulli beam FE validated exact against cantilever/SS-UDL closed
  forms, cross-checking the ship BM diagram against the direct integrator (corr 0.99997,
  max diff 0.61% of peak). Found and fixed during its own build: element-vs-span length
  mix-up, kN-vs-N unit mixing, missing fixed-end-load subtraction, ill-conditioned Lagrange
  solve -- all now gated.
- `drawings.py`: lines plan (profile, half-breadth with per-WL layers, body plan),
  hydrostatic curves, GZ sheet (both solvers plotted), midship section with scantling table
  -- all DXF, all title-blocked with the geometry hash, all verified by re-opening and
  measuring the file against the model (19 checks).
- `finalization` block in the design record: NOT_FINALIZED while any FAIL/OPEN exists;
  FROZEN_PENDING_HUMAN when green; RELEASED only via human gate; agents can never self-sign.
- Fleets extended: design 60 -> 64 (drawings consistency, FE cross-check, simulation
  validation status, finalization freeze), repo 52 -> 56 (v0.2 wiring, drawing artefacts,
  FE self-test, claim consistency). 120 reviewers total.

### Fixed (during v0.2 build, via error-fix-loop)
- `structure.load_curve` now separates distributed from lumped loads so any FE cross-check
  applies each faithfully (smearing point loads cost 25% of peak BM and broke equilibrium).
- Load-curve sign-convention field corrected and documented (BM negative = hogging under
  q = w - b positive-down).

## [0.1.0] - 2026-10-25

### Added
- 28 Agent Skills covering the full owner-brief → shipyard-package pipeline, spec-compliant
  with agentskills.io (frontmatter validated by CI).
- Reference implementation: parametric hull generator, independent mesh hydrostatics solver
  (divergence-theorem kernel, validated exact against an analytic prism), navaltoolbox
  cross-check harness, loading conditions with trim equilibrium, 2008 IS Code intact
  criteria (weather criterion refused pending Code tables), ITTC-57 powering with declared
  ESTIMATE tags, EEDI attained/required + 768-combination trade study with power-stress
  filter, SWBM by direct load-curve integration with equilibrium gates, steel take-off with
  plausibility bands, design-space exploration with a scored reviewer gate.
- 60-agent design verification fleet (`agents/run_fleet.py`) and 52-agent repo review fleet
  (`repo-review/review_fleet.py`), both publishing machine-readable findings.
- Full 48-item defect log with symptoms, costs, and the gate that caught each.
- Docs: pipeline, verification architecture, tool catalog, honest gaps/human-gates account,
  EEDI case study, roadmap.
- CI: ground-truth test, module self-tests, full pipeline run, both fleets, frontmatter lint,
  path/hygiene audit.
- Claude Code plugin marketplace manifest; install guides for Claude Code, Codex, Cursor,
  Gemini CLI, OpenClaw and generic harnesses.

### Known limitations (deliberate, tracked in ROADMAP)
- Wave bending moment: OPEN by refusal; requires rule text in force.
- Damage stability: process + data model only; probabilistic index needs supplied tables.
- Reviewer gate in the reference implementation cannot yet discriminate candidates on proxy
  metrics (flagged BLOCKER by agent I03); real per-candidate discipline runs are the fix.
- Ship-type coverage: bulk carrier tuned; other types need parent-ship bands.

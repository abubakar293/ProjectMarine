# Roadmap

Ordered by leverage, not by ease. Items marked **[needs domain data]** are blocked on
contributions, not on code — that is where naval architects can have the most impact.

## v0.2 — the rule unlock

- [ ] **Machine-readable rule-clause database schema** + loader + citation format.
      Sketch: `{clause_id, source, edition, applies_to, formula, limit, units, evidence_link}`.
      The single biggest unlock: until rules are data, compliance is prose. **[needs domain data]**
- [ ] **Damage stability** with supplied Code tables: SOLAS 2009 probabilistic (R/A/factor
      machinery) for cargo ships; deterministic floodable-length path; the skill currently
      defines the process and refuses the coefficients. **[needs domain data]**
- [ ] **2008 IS Code weather criterion** completed from transcribed-and-cited tables
      (X1, X2, k, T-roll), with the transcription unit-tested against a worked example.
- [ ] **CSR wave bending moment + hull-girder criterion** from the rule text in force,
      replacing the current OPEN refusal, with the parent-band gate kept as a backstop.

## v0.3 — ship-type coverage

- [ ] Ship-type profile packs (bands, load cases, rule stacks, typical systems):
      tanker (CSR-OT, IBC/IGC where relevant), container (lashing, GM-band, torsion),
      RoRo (vehicle decks, damage stability sensitivity), passenger (SOLAS II-1/II-2,
      safe return to port), offshore (DNV ST-0437/-0126 class paths), workboat/crew boat
      (ISO 12217 small-craft path), yacht (LY3/ISO), naval (bespoke, out of class scope).
      **[needs domain data per type]**
- [ ] Seakeeping + manoeuvring skill wired to an open solver path (strip theory / OpenFOAM
      case templates) with validation against KCS/KVLCC2/DTMB 5415 public data.

## v0.4 — tooling

- [x] Beam-FE cross-check of the hull-girder BM diagram (v0.2, `fe_beam.py`).
- [ ] OpenFOAM resistance recipe (case templates + validation against KCS public data) and
      CalculiX midship-hold FE recipe wired into `simulation-suite`.
- [ ] **MCP server** wrapping the reference solvers (hydrostatics, stability, SWBM, EEDI)
      so any MCP-capable agent gets them as tools without vendoring the code.
- [ ] FreeCAD Ship-workbench bridge and Rhino/Orca3D recipe notes; Maxsurf MCP integration
      notes (a community MCP server exists — see docs/TOOL-CATALOG.md).
- [x] Drawing generation: lines plan + curve sheets + midship section to DXF via ezdxf with
      read-back verification (v0.2). Still to do: GA line-work, shell expansion, booklet
      build via Typst, FreeCAD TechDraw projection recipes.
- [ ] Cost model: class 5 → class 3 driver tree with calibration hooks to yard data.

## v0.5 — the reviewer gate, for real

- [ ] Per-candidate full discipline runs (hull → hydrostatics → powering → structure) so the
      reviewer gate scores *computed* results, not proxies. The current gate is flagged
      BLOCKER by its own fleet (finding I03: three candidates all scored 88.51 — a gate that
      cannot discriminate is theatre).
- [ ] Fatigue and constructability axes with real inputs (yard crane/block limits as data).

## Community & distribution

- [ ] Submit to: anthropics/skills community listings, awesome-claude-code,
      awesome-agent-skills, agentskills.io directory, mcpservers.org, SKILL.md marketplaces.
- [ ] Maritime community outreach: SNAME, IMarEST, RINA forums; r/NavalArchitecture;
      MARIN/SVA model-test community for validation datasets.
- [ ] Translate the orchestrator + verification skills (es, zh, ko, ja, no, el) — shipbuilding
      is not an English-only industry.

## Non-goals (stated so they are not "missing")

- Physical shipyard automation (welding robots, erection) — different problem, different
  community.
- Class/flag approval itself — a human and a surveyor, always.
- Operation-phase optimisation (weather routing, CII monitoring in service) — adjacent, and
  better served by dedicated projects; a bridge skill may land later.

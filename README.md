# 🚢 ProjectMarine

**Agent Skills that let your AI agent run a real ship design process — owner's requirement in,
shipyard-ready design package out — with every number verified by two independent solvers and
every unverifiable number refused instead of invented.**

Built for the maritime engineering community — naval architects, shipyards, design offices and
agent engineers. The method that produced it caught **48 silently-plausible defects** in its own
reference implementation; the [defect log](docs/DEFECT-LOG.md) ships with the repo. Works with any agent that reads the open [Agent Skills](https://agentskills.io) standard:
**Claude Code, Codex, Cursor, Gemini CLI, OpenClaw**, and anything else that loads `SKILL.md`.

[![CI](https://github.com/abubakar293/ProjectMarine/actions/workflows/ci.yml/badge.svg)](https://github.com/abubakar293/ProjectMarine/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Agent Skills spec](https://img.shields.io/badge/Agent%20Skills-spec--compliant-blue)](https://agentskills.io/specification)
[![33 skills](https://img.shields.io/badge/skills-33-green)](./skills)
[![Reviewed by 120 agents](https://img.shields.io/badge/reviewed%20by-120%20agents-orange)](./docs/VERIFICATION-ARCHITECTURE.md)

---

## Why this repo exists

Anyone can prompt an LLM to "design a ship" and get confident nonsense: a hull whose block
coefficient is impossible, stability computed at zero heel, a wave bending moment off by a
factor of 74. **The output looks right. That is the problem.**

This repo was built the other way around. We wrote a working reference implementation of the
design pipeline, then threw chartered review-agent fleets at it — **64 on the design, 56 on
the repo itself**. They caught **48 defects —
every single one of which produced plausible output at the time**. The most dangerous:

> Heel had been implemented as a rotation about the **vertical** axis instead of the
> longitudinal axis. Every upright hydrostatic — volume, KB, Awp, BMt, BMl, LCF, LCB — was
> *exactly correct*. The entire stability assessment was silently computed at zero heel.
> Nothing in the upright output could reveal it. Only a second, independently written solver
> disagreeing about GZ did.

The skills in this repo encode that process: the stage machine, the four verification
mechanisms, the provenance discipline, the refusal mechanisms, and the human gates. The
[defect log](docs/DEFECT-LOG.md) is published in full, because the failure modes are the
curriculum.

**Read [DEFECT-LOG.md](docs/DEFECT-LOG.md) before writing a line of geometry code.** It is the
most useful file in this repository.

## What the pipeline produces

Given an owner's brief (ship type, trade, cargo, speed, dimensional limits, flag/class,
budget), the agent works stage by stage, and **each stage ends at a gate that stops the run
when it fails**:

```
S0 owner brief ──► S1 sizing ──► S2 hull form ──► S3 hydrostatics & stability
                                                        │
S9 documentation ◄── S8 cost & build ◄── S7 compliance ◄── S4 powering & EEDI
     package              strategy         matrix         │
                                                    S5 structure ──► S6 arrangement
```

The reference case — a **Handysize bulk carrier** (Lpp 180 m, B 29.8 m, T 10.5 m, Cb 0.845) —
runs end to end in ~45 seconds and produces a hashed, deterministic design record:

| Output | Reference-case result | Verified by |
|---|---|---|
| Hull form (watertight mesh + offsets table) | Cb 0.845, Cm 0.961, Cp 0.879 | postcondition suite + parent-ship bands |
| Hydrostatics at all drafts | volume, KB, BMt, BMl, Awp, LCF, LCB | **two independent solvers, 0.0000% apart** |
| 5 loading conditions with trim equilibrium | departure 46,730 t, T = 10.19 m, trim +0.68° | Newton solver + equilibrium identities |
| GZ curves | agrees with the independent solver to ≤0.25% at 60° heel | cross-check + small-angle identity vs GM |
| 2008 IS Code intact stability | all evaluated criteria PASS; weather criterion **OPEN by refusal** (needs the Code's coefficient tables) | cited clause by clause |
| Speed–power & installed MCR | 4,361 kW at 14 kn, Fn 0.171 | validity-band checks; ESTIMATE tags declared |
| **EEDI Phase 3** | **FAIL: attained 6.34 vs required 4.38** — with a full trade study of what closes the gap | [case study](docs/EEDI-TRADE-STUDY.md) |
| Still-water bending moment | −1.83e6 kN·m at midships | direct integration + Σq = 0 and Σq·x = 0 gates |
| Wave bending moment | **OPEN — refused.** Three memory-transcriptions gave 1.5e8 / 152 / 3.5e5 kN·m; all caught by plausibility gates | requires the rule text in force |
| Steel take-off, capacities, traceability | 7,068 t hull steel; 22 tanks; 7 requirements traced | plausibility bands + single-source tank model |

The EEDI failure is not a bug — it is the system working. It refuses to hide a real regulatory
problem, quantifies the trade (speed vs DWT vs ESD credit vs fuel across 768 combinations),
and stress-tests every "compliant" answer against a 1.25–2.0× error in installed power,
because the power estimate itself rests on declared ESTIMATE-class inputs.
**At nominal power, a conventional HFO ship tops out at ~10 kn; the 14 kn solution only
exists with zero margin against power uncertainty.** That is a finding an owner can act on.

## Install

<details>
<summary><b>Claude Code</b> (plugin marketplace or manual)</summary>

```bash
# as a plugin marketplace
/plugin marketplace add abubakar293/ProjectMarine
/plugin install ship-design

# or manually
git clone https://github.com/abubakar293/ProjectMarine
cp -r ProjectMarine/skills/* ~/.claude/skills/
```
</details>

<details>
<summary><b>Codex / Cursor / Gemini CLI / OpenClaw / generic</b></summary>

```bash
git clone https://github.com/abubakar293/ProjectMarine
# Codex:      cp -r ProjectMarine/skills/* ~/.codex/skills/
# Cursor:     reference the skills from .cursor/rules, or paste the relevant SKILL.md
# Gemini CLI: add to GEMINI.md context or your extensions directory
# OpenClaw:   drop the folders into your workspace skills directory
# Anything else that follows agentskills.io: point it at skills/<name>/SKILL.md
```
Full details, including running the reference implementation, in [INSTALL.md](INSTALL.md).
</details>

## The 33 skills

| Stage | Skills |
|---|---|
| **Run the project** | `ship-design-orchestrator` — the stage machine, gates, design record, escalation |
| **Intake** | `owner-brief-intake` · `regulatory-mapping` |
| **Concept** | `ship-sizing` · `hull-form-generation` · `hydrostatics-crosscheck` |
| **Naval architecture** | `stability-intact` · `stability-damage` · `resistance-powering` · `edi-trade-study` · `seakeeping-maneuvering` |
| **Structure** | `structural-loads` · `scantlings-midship` · `structural-fe-verification` |
| **Arrangement & systems** | `general-arrangement` · `machinery-layout` · `marine-systems` |
| **Compliance & weights** | `class-statutory-compliance` · `weight-control` · `cost-estimating` |
| **Build & delivery** | `shipyard-data-requirements` · `production-design-handoff` · `sea-trials-warranty` · `documentation-package` |
| **Simulate, draw, choose tools** | `simulation-suite` (CFD/FE validated on free tools first) · `cad-drawing-generation` (every sheet read back against the model) · `toolchain-selection` (free ladder + paid-API patterns) |
| **The discipline that makes it safe** | `verification-gates` · `provenance-discipline` · `defect-patterns` · `agent-fleet-review` · `error-fix-loop` (fix root causes; **never finalize with any error open**) · `human-gates-escalation` |

Start with **`ship-design-orchestrator`** — it drives everything else. The last row is not
optional decoration; it is what distinguishes this repo from "prompt an LLM to design a ship".

## The four verification mechanisms

Every skill is built on these (details in [docs/VERIFICATION-ARCHITECTURE.md](docs/VERIFICATION-ARCHITECTURE.md)):

1. **Closed-form ground truth.** Both solvers must reproduce an analytic prism *exactly*
   before touching a real hull.
2. **Two independent implementations.** Every hydrostatic value is computed twice, by
   different code, and the disagreement is printed — never averaged, never hidden.
3. **Physical plausibility bands.** Cm ≤ 1. Hull steel 55–95% of lightship. Wave BM inside a
   parent-ship band. A number outside its band stops the run.
4. **Equilibrium identities.** Σq = 0 and Σq·(x−LCG) = 0 on every load curve; ΣW = Δ·g
   exactly. One of these caught a quadrature bug that had silently halved every lumped mass
   while vertical force still "balanced" to 6 significant figures.

Plus the rule that makes refusal safe: **every constant is tagged VERIFIED / STANDARD /
ESTIMATE / NOT-IMPL**, and a rule constant that cannot be transcribed from the rule text in
force is *refused* — recorded as an OPEN item with an owner and an action, never estimated
into existence. See `provenance-discipline`.

## What this is NOT

Honesty is a feature; this repo ships with it.

- ❌ **Not class approval.** A surveyor signs drawings, not an agent. The pipeline targets a
  *class-submittable* package; Approval in Principle is the realistic external checkpoint.
- ❌ **Not rule text from memory.** LLM recall of SOLAS/CSR clauses is not a gate. You must
  supply the rule documents; the skills tell the agent how to encode and cite them.
- ❌ **Not vendor data.** Engine envelopes, pump curves, hatch covers: the agent requests
  datasheets and refuses to assume them.
- ❌ **Not the physical build.** Welding robots, block assembly and erection are industrial
  automation, a separate problem. The skills cover the *data* the yard needs (production
  design handoff, nesting inputs, weight control), not the robots.
- ❌ **Not a warranty.** Speed–consumption commitments need verified powering and sea trials.
  The skills make the agent carry uncertainty to that conversation instead of hiding it.

The full honest account, including what *is* automatable today and which commercial tools an
agent can actually drive, is in [docs/GAPS-AND-HUMAN-GATES.md](docs/GAPS-AND-HUMAN-GATES.md)
and [docs/TOOL-CATALOG.md](docs/TOOL-CATALOG.md).

## Simulate, draw, verify — and never finalize with an error open

- **Simulations** (`simulation-suite`): resistance/self-propulsion CFD, seakeeping, structural
  FE, buckling, flooding, manoeuvring — free tools first (OpenFOAM, CalculiX, Code_Aster,
  gmsh), paid shipyard tools (Sesam, Maxsurf MCP, NAPA, STAR-CCM+, AVEVA/CADMATIC APIs) via
  their scripting interfaces. Every tool reproduces a benchmark **before** project use: the
  shipped beam-FE is exact on cantilever and simply-supported closed forms, then confirms the
  ship's bending-moment diagram against the independent integrator (0.61% of peak).
- **CAD drawings** (`cad-drawing-generation`): lines plan, hydrostatic curves, GZ sheets,
  midship section — generated as DXF from the frozen model, title-blocked with the geometry
  hash, then **re-opened and measured back against the model** (19 automated checks in the
  reference case). Paid-CAD paths (AutoCAD scripts, Rhino.Compute, AVEVA/CADMATIC APIs)
  follow the same generate-then-verify contract.
- **The fix loop** (`error-fix-loop`): any error triggers freeze → reproduce → root-cause →
  fix → regression test → re-run cascade → re-run fleets → defect log. The record carries a
  `finalization` block: while any FAIL/OPEN item exists it reads **NOT_FINALIZED**; a fully
  green record stops at FROZEN_PENDING_HUMAN; only a human gate may write RELEASED, and an
  agent may never sign itself in.

## The repo reviews itself

This repository was reviewed by its own methodology: a **56-agent fleet** chartered against
the repo (README claims vs evidence, frontmatter spec compliance, install correctness, CI,
license hygiene, security, number consistency across docs, fresh-clone reproducibility,
drawings and FE artefacts), on top of the **64-agent fleet** that reviews the design itself. Findings are published in
[repo-review/](repo-review/). If you fork this repo, run the fleet — that is what it is for.

## Reference implementation

`reference-implementation/` contains the working pipeline that produced every number above:

```bash
cd reference-implementation/code
pip install numpy scipy navaltoolbox ezdxf  # navaltoolbox is AGPL; see LICENSE note
python3 test_solver_groundtruth.py          # both solvers vs an analytic prism: exact
python3 structure.py && python3 powering.py # module self-tests
python3 run_case.py                         # brief.json -> full design record (~45 s)
python3 agents/run_fleet.py                 # 64 reviewers -> findings.json
python3 edi_trade.py                        # 768-combination EEDI trade study
```

Deterministic and hashed: `run_case.py` regenerates the hull STL byte-identically and the
fleet re-verifies the SHA-256 against the record. CI runs all of it on every push.

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md). Highest-leverage next steps: a machine-readable
rule-clause database schema (the single biggest unlock), damage stability with supplied
Code tables, an MCP server wrapping the solvers, and ship-type profiles beyond bulk
carriers (tanker, container, RoRo, passenger, offshore, workboat, yacht).

## Contributing

Skills are Markdown; the bar is evidence. Every new skill needs: gates with numbers,
prohibitions, escalation criteria, and — if it computes anything — a self-test that *fails
when the formula is wrong*. See [CONTRIBUTING.md](CONTRIBUTING.md). Naval architects: your
parent-ship bands and rule citations are the most valuable thing you can add. Agent
engineers: your failure modes are the second most valuable.

## Citation

If this repo saves you from a silent defect, cite it:

```bibtex
@software{projectmarine,
  title  = {ProjectMarine: verified agent skills for ship design},
  year   = {2026},
  url    = {https://github.com/abubakar293/ProjectMarine}
}
```

## License

MIT for skills and docs. The reference implementation is MIT; its optional `navaltoolbox`
dependency is AGPL-3.0 — see [LICENSE](LICENSE).

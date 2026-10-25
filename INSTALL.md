# Install guide

The skills are plain Markdown following the open [Agent Skills specification](https://agentskills.io/specification)
(`skills/<name>/SKILL.md` with YAML frontmatter). Any agent harness that loads that format works.

## Claude Code

**Option A — plugin marketplace (recommended):**

```
/plugin marketplace add abubakar293/ProjectMarine
/plugin install ship-design
```

**Option B — manual, user-wide:**

```bash
git clone https://github.com/abubakar293/ProjectMarine
mkdir -p ~/.claude/skills
cp -r ProjectMarine/skills/* ~/.claude/skills/
```

**Option C — per project:**

```bash
mkdir -p .claude/skills && cp -r ProjectMarine/skills/* .claude/skills/
```

Verify: ask Claude to *"design a 25 m crew boat from this brief"* — it should activate
`ship-design-orchestrator` and start with `owner-brief-intake` questions, not drawings.

## Codex CLI

```bash
git clone https://github.com/abubakar293/ProjectMarine
mkdir -p ~/.codex/skills && cp -r ProjectMarine/skills/* ~/.codex/skills/
```

Alternatively reference the skill folder from your `AGENTS.md`:

```markdown
## Ship design
Follow the stage machine in ProjectMarine/skills/ship-design-orchestrator/SKILL.md.
Never skip a verification gate. Refuse rather than invent rule constants.
```

## Cursor

Cursor reads `.cursor/rules/*.mdc`. Two options:

1. Point a rule at the skill: create `.cursor/rules/ship-design.mdc` whose body says
   "For ship design tasks, read and follow `ProjectMarine/skills/<name>/SKILL.md`;
   start with ship-design-orchestrator."
2. Or paste individual SKILL.md bodies into rules for the disciplines you use most.

## Gemini CLI

Add to `GEMINI.md` (or your extension's context file):

```markdown
For ship design tasks, load and follow the SKILL.md files under
ProjectMarine/skills/, starting with ship-design-orchestrator.
Enforce its gates; refuse to invent rule constants.
```

## OpenClaw / other harnesses

Drop the skill folders into your workspace skills directory, or mount the repo and reference
`skills/<name>/SKILL.md` paths from your system context. The format is harness-neutral:
frontmatter `name` + `description`, Markdown body, optional `references/` and `scripts/`.

## Running the reference implementation

The skills reference a working pipeline you can run to see the method end to end:

```bash
cd reference-implementation/code
python3 -m pip install numpy scipy navaltoolbox ezdxf
python3 test_solver_groundtruth.py     # ~2 s, must print exact agreement
python3 structure.py                   # SWBM integrator self-tests
python3 powering.py                    # form-factor / ITTC-57 self-tests
python3 run_case.py                    # full design record, ~45 s
python3 agents/run_fleet.py            # 64 reviewers, ~45 s
python3 edi_trade.py                   # EEDI trade study, <1 s
```

Requirements: Python 3.10+, numpy, scipy, ezdxf (drawings). `navaltoolbox` (AGPL-3.0) is used as the second
solver in the cross-check; the independent solver in `hydrostatics.py` has no dependencies
beyond numpy, so the cross-check degrades to single-solver if you cannot accept AGPL — which
the skills explicitly flag as a reduced-assurance mode.

## Supply-chain note

Skills are **instructions your agent will follow**. Treat third-party skills like code:
read them before installing, pin a commit, and review diffs on update. See [SECURITY.md](SECURITY.md).

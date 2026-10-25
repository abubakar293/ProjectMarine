# Contributing

The bar is evidence. This repo's entire value proposition is that its numbers can be
recomputed and its failure modes are documented — contributions must keep that property.

## What we most need

1. **Naval architects: parent-ship bands and rule citations.** The plausibility gates are
   only as good as their bands. A pull request that adds "for a Panamax tanker, Z_deck net is
   typically X–Y cm³, source: <citation>" is worth more than any amount of prose.
2. **Rule engineers: machine-readable clause encodings.** See the schema sketch in
   `skills/class-statutory-compliance/references/rule-schema.md`. A clause encoded as
   `{id, source, edition, applies_to, formula, limit, units}` with a test is the single
   biggest unlock for the whole stack.
3. **Agent engineers: failure modes.** If you watched an agent do something dangerous or
   stupid with these skills, that is a defect report. The `defect-patterns` skill grows from
   real incidents only.
4. **Ship-type profiles.** The reference case is a bulk carrier. Tanker, container, RoRo,
   passenger, offshore, workboat, yacht profiles (bands, load cases, rule stacks) are the
   main coverage gap.

## Adding or changing a skill

A skill must have, or it will be asked for in review:

- Valid frontmatter per the [Agent Skills spec](https://agentskills.io/specification):
  `name` matching the directory (lowercase, hyphens), `description` ≤ 1024 chars that says
  *what it does and when to use it*.
- **Gates with numbers.** "Check the stability" is not a gate. "GM_fluid ≥ 0.15 m per
  2008 IS Code 2.1.2, and GZ(30°) ≥ 0.20 m per 2.1.3.1" is.
- **Prohibitions.** What the agent must never do in this domain, and why (a one-line war
  story is ideal — see how `hydrostatics-crosscheck` tells the zero-heel story).
- **Escalation criteria.** When to stop and hand to a human, with the owner role named.
- **Under 500 lines**; long material goes in `references/`.
- If it computes anything: **a self-test that fails when the formula is wrong.** A test that
  passes both ways is decoration (defect #41 in the log is exactly this).

## Process

1. Fork, branch from `main`, one skill or fix per PR.
2. Run the repo review fleet: `python3 repo-review/review_fleet.py` — it checks frontmatter,
   links, claims-vs-evidence, hygiene. Fix your findings.
3. If you touched `reference-implementation/`: CI must pass. Ground truth must stay exact;
   self-tests must pass; `run_case.py` must regenerate the record deterministically.
4. Numbers cited anywhere in prose must match the artefacts they come from
   (`design_record.json`, `findings.json`). Reviewer R34 checks this mechanically.

## Reviewers and conduct

Review is adversarial by design — reviewers are chartered to find defects, not to approve.
That is not hostility; it is the method that caught 48 defects. Be specific, cite evidence,
propose the fix.

Maintainers: see `CODEOWNERS`. Security reports: see [SECURITY.md](SECURITY.md).

## Where this repo should be listed

Help discoverability by submitting the repo to skills directories and awesome lists
(keep the list current in `docs/ROADMAP.md`):

- anthropics/skills community listings
- awesome-claude-code, awesome-agent-skills and similar lists
- agentskills.io directory
- mcpservers.org skills section and SKILL.md marketplaces
- maritime communities: SNAME/IMarEST/RINA forums, r/NavalArchitecture, Marine Insight

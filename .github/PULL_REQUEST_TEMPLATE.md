## What this changes

## Evidence
<!-- Numbers must come from an artefact (design_record.json, findings.json, a self-test).
     If the skill computes anything, the self-test must FAIL when the formula is wrong. -->

## Checklist
- [ ] `python3 repo-review/review_fleet.py` shows no new BLOCKER/MAJOR findings
- [ ] Frontmatter passes `repo-review/lint_skills.py`
- [ ] Gates have numbers; prohibitions say why; escalation names an owner role
- [ ] No rule constant transcribed from memory (VERIFIED/STANDARD/ESTIMATE/NOT-IMPL tags)
- [ ] CI green (ground truth exact, self-tests pass, pipeline deterministic)

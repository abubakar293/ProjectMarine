---
name: agent-fleet-review
description: Charters and runs fleets of narrow-scope reviewer agents against design output, code, or documents - with the findings schema, severity rules, and the anti-theatre checks (crashed reviewers are findings; gates that cannot discriminate are BLOCKERs against the gate). Use before any concept freeze, class submission, or release; and when reviewing any large artefact an agent produced.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: meta
  stage: cross-cutting
---

# Agent Fleet Review

One generalist reviewer agrees with prose. A fleet of narrow reviewers with deterministic
checks disagrees with numbers. The reference stack runs 60 design reviewers and 52 repo
reviewers; together they found 48 code/design defects and 3 repo-defects in the review layer
itself.

## Chartering rules

1. **Narrow scope.** One reviewer = one question it can answer deterministically. "Review the
   stability" is not a charter; "does fitted dGZ/dφ equal GM within 3%" is.
2. **Recompute, don't re-read.** Every reviewer gets tools to re-derive or cross-check
   something. A reviewer that only reads the report can only agree with the report.
3. **Cover every stage.** Unreviewed stages are where defects live. The reference fleet spans
   intake (4), naval architecture (12), structure (5), arrangement (4), compliance (4),
   verification (10), production (3), project (2), documentation (6), architecture (10).
4. **Structured findings**: {agent, severity BLOCKER|MAJOR|MINOR|INFO|PASS, title, evidence,
   action_required, owner}. Evidence is a number, a file, or a recomputation output — never
   an adjective.
5. **A crashed reviewer is a BLOCKER finding**, not a skip. The reference fleet counts
   crashes explicitly; two crashes (stale JSON keys) were fixed in the reviewers before the
   findings were trusted.

## Severity discipline

- BLOCKER: stops the run / blocks submission. Real example: attained EEDI 6.34 vs required
  4.38 — a genuine regulatory FAIL the fleet escalates with the trade study attached.
- MAJOR: must close before the next gate; has owner + action.
- MINOR: fix in cycle. INFO: context. PASS: explicit — silence is not agreement.
- Reviewers may be wrong: three early fleet findings were false positives (stale key, missed
  external self-test, a regex that flagged the literal `24 * 0.0216` as placeholder algebra).
  Adjudicate findings against artefacts; fix the reviewer when the reviewer is wrong, and
  record that too.

## Anti-theatre checks (the fleet reviews the fleet)

- **Discrimination**: a scoring gate whose candidates all land within 1 point is not a gate —
  the reference fleet flags its own reviewer gate as BLOCKER when three candidates scored
  identical 88.51 on proxy metrics. Either score real per-candidate computations or report
  the tie explicitly; never announce a "winner" of a photo finish you cannot see.
- **Saturation**: scoring axes pinned at 100 carry no information; re-anchor.
- **Gate enforcement**: count `raise` vs `WARNING` in the pipeline; more warnings than raises
  means gates are decoration.
- **Determinism**: re-run the generator, compare hashes.

## Running a fleet

```python
for agent in FLEET:                    # each returns findings[]
    try:    findings += agent.run(ctx)
    except Exception as e:             # crashed reviewer = BLOCKER finding
        findings += [crash_finding(agent, e)]
counts = tally(findings)
publish("findings.json")               # machine-readable, part of the record
```

Present to humans: BLOCKERs first with evidence and action, then MAJORs, then the PASS
summary — the PASS list matters because it shows what was checked and found sound.

## Gates

- Zero crashed reviewers (a crash is a BLOCKER finding, and the domain is unreviewed until fixed).
- Every BLOCKER/MAJOR finding has evidence (number/file/recomputation) and an owner.
- Gate-discrimination check whenever the fleet reviews a scoring gate: candidate composite
  spread >= 1 point, or the gate is reported as theatre.
- Findings published as machine-readable JSON alongside the artefact hash they reviewed.

## Prohibitions

- No reviewer without a deterministic check (opinion agents inflate MAJOR counts and train
  everyone to ignore findings).
- No fixing findings by editing the finding.
- No fleet run against a moving record — freeze the artefact (hash it), review the hash.

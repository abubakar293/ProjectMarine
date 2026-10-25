---
name: error-fix-loop
description: The fix-and-verify protocol that runs whenever ANY error appears - failed gate, fleet BLOCKER/MAJOR, solver disagreement, self-test failure, crash - and the finalization freeze that forbids completing, releasing or signing off anything while any error remains open. Enforces root-cause fixes with regression tests, never symptom-patching, fudge factors, or tolerance-loosening. Use on every error, before every finalization, and when tempted to adjust a number to make a check pass.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.2.0"
  domain: meta
  stage: cross-cutting
---

# Error-Fix Loop & Finalization Freeze

**Nothing is finalized while any error remains.** Not "almost done", not "pending one small
issue" — the freeze is binary and the only exits are: fix, or a named human accepts the item
in writing with an expiry. This skill is the protocol behind that sentence.

## Triggers (any one starts the loop)

Failed gate or assertion · fleet BLOCKER/MAJOR · solver disagreement beyond tolerance ·
self-test failure · non-convergence or clip-pinned output (round numbers like exactly
5.000° are fingerprints) · crash in pipeline or reviewer · round-trip mismatch after a data
handoff · drawing read-back mismatch · determinism check failure.

## The protocol

1. **Freeze the artefact.** Hash what failed. The investigation is against a frozen state,
   not a moving one.
2. **Reproduce minimally.** Shrink to the smallest failing case. A 12-triangle box beats a
   29k-triangle hull for finding integrator bugs (most of the reference defect log was
   located this way).
3. **Print every intermediate.** Do not reason algebraically at first — dump the terms.
   Two wrong hand-derivations of one rotation matrix were each "fixed" by a third
   derivation before a six-line numeric probe settled it in one shot.
4. **Classify against `defect-patterns`.** Frame/rotation, clipping/quadrature, mesh, units,
   convergence seed/sign, equilibrium, physical-design error. Most defects are in the
   catalogue; check it before inventing a theory.
5. **Find the root cause, not the proximate cause.** "The number is wrong" → "the moment was
   not divided by volume" → "the function returned a tuple whose second element changed
   meaning". Fix at the level where the invariant should have held.
6. **Fix the cause.** Symptom-patching is prohibited (below).
7. **Add the regression test.** A test that FAILS on the old code and passes on the new.
   A test that passes both ways is decoration (defect #41: the free-free-beam self-test
   asserted a simply-supported formula and failed the correct integrator).
8. **Re-run the cascade.** Upstream fixes invalidate downstream results: geometry changed →
   hydrostatics, stability, loads, structure, EEDI, drawings all re-run. The record's hashes
   make staleness mechanical, not memorial.
9. **Re-run the fleets.** Both the design fleet and (if repo code changed) the repo fleet.
   Zero crashed reviewers before their findings count.
10. **Log it.** Defect-log format: symptom (what looked plausible), exposure (how it was
    caught), root cause, fix, and *the gate that will catch this class next time*. If no
    gate would catch it, build one — that is part of the fix.

## Prohibitions — banned "fixes" (each has happened; each is a BLOCKER if found)

- Tuning a coefficient until the output looks plausible (the mis-transcribed wave-BM formula
  invited exactly this; it was deleted instead — defect #36–38).
- Loosening a tolerance or band to make a check pass. Bands are cited; changing one is a
  design decision with a source, not a debugging step.
- Deleting, skipping, or `xfail`-ing a failing test.
- Converting a `raise` into a `warning` to unblock a run — that deletes the gate (I09).
- Editing a fleet finding instead of the artefact it describes.
- Re-running a nondeterministic step until it passes — flake-hiding; fix the
  nondeterminism.
- Marking an OPEN item N/A to clean the matrix.
- Averaging two disagreeing solvers.

## Gates — Definition of Done (the finalization gate)

A stage, package, or project may be marked complete ONLY when ALL of:

- [ ] zero failed gates; zero BLOCKER findings; zero crashed reviewers;
- [ ] zero MAJOR findings, or each carries a named human acceptance + expiry date;
- [ ] all self-tests and ground-truth checks green in one clean run;
- [ ] all cross-checks within declared tolerances (two-solver table printed in the record);
- [ ] determinism check passes (regenerate → identical hashes);
- [ ] drawings read back against the frozen model;
- [ ] OPEN items consolidated, each with owner + action, rendered into the package
      (`documentation-package` ships them visibly);
- [ ] defect log updated with every defect this cycle produced.

If any box is unchecked, the artefact status is **NOT FINALIZED** and says so on its face.

## Finalization freeze mechanics

- Status field in the record: `finalization: {status: NOT_FINALIZED|FROZEN_PENDING_HUMAN|
  RELEASED, blockers: [...], accepted_by: null|{name, date, expiry}}`.
- Only a human gate (`human-gates-escalation`) can move FROZEN_PENDING_HUMAN → RELEASED.
- A RELEASED artefact whose inputs changed (hash mismatch) automatically reverts to
  NOT FINALIZED — releases are hashes, not vibes.
- The agent may never write itself into `accepted_by`.

## The loop is the product

48 defects were found and fixed this way in the reference build, including one (zero-heel
stability) that no output inspection could have caught. The loop's real output is not fixed
code — it is the growing set of gates that make each defect class unrepeatable.

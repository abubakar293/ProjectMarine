---
name: provenance-discipline
description: Tags every constant, formula and coefficient as VERIFIED, STANDARD, ESTIMATE or NOT-IMPL, and enforces the refuse-rather-than-invent rule for rule constants and regressions. Use when writing or reviewing ANY code, calculation, or document that contains numbers - especially rule formulas, empirical regressions, conversion factors, and regulatory coefficients.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: verification
  stage: cross-cutting
---

# Provenance Discipline

Every constant in a computation carries a tag. The tag travels with the number into every
downstream artefact, because an estimate wearing a citation is more dangerous than a gap.

## The four tags

| Tag | Meaning | May it gate a decision? |
|---|---|---|
| **VERIFIED** | closed-form physics, or re-derived and unit-tested here (e.g. divergence theorem, ITTC-57 line checked against its definition) | yes |
| **STANDARD** | published industry standard form, transcribed and range-checked (e.g. C_w curve shape, P_AE = 0.025·P_ME + 250) | yes, with the edition cited |
| **ESTIMATE** | declared planning allowance with a band (e.g. 1+k = 1.45 ± 0.15; wave resistance = 15% ± 8 pts of R_F; sea margin 15%) | no — never a warranty, never a filing |
| **NOT-IMPL** | deliberately absent; the function raises or returns OPEN | the absence itself is the signal |

## The refuse-rather-than-invent rule

When a quantity requires rule text, regulatory tables, or a published regression you do not
have verbatim:

1. **Do not transcribe from memory.** In the reference build this was attempted three times
   for one wave-BM formula: 1.52e8 kN·m, then (after a "units fix") 152 kN·m, then 3.52e5
   against a true ~2e6. A form factor came out 279.7. Each looked like arithmetic until a
   band gate fired. Memory-transcription of rule constants is the single highest-yield
   failure mode of LLM engineering code.
2. **Return a structured OPEN item**, not a placeholder number:
   `{"implemented": false, "status": "OPEN", "reason": ..., "gates_that_caught_it": ...,
   "action_required": "read <formula> from <rule edition> or obtain from <class tool>",
   "context_only": {...}}`
3. **Split the boundary into separate functions** so it cannot be crossed by accident. The
   reference `iscode.py` computes the unambiguous weather-criterion parts (PW1, PW2, areas)
   and refuses K; a *separate* function accepts a roll angle **supplied by an authoritative
   source**. An agent computing K itself has no path to the second function.
4. If you must proceed for scheduling reasons, proceed with the ESTIMATE tag, a band, and a
   named human who accepts the risk in writing.

## Deletion over tuning

When a mis-transcribed formula is caught, **delete it**; do not adjust coefficients until
the output looks plausible. Tuning a wrong formula until believable produces a number
carrying the authority of a citation it does not deserve — the worst possible artefact.
The reference powering module deleted a half-implemented Holtrop–Mennen wave-resistance
block (~30 lines of self-cancelling placeholder algebra) and replaced it with a declared
15%±8 allowance. The deletion is recorded in the defect log (#42).

## Carrying tags downstream

- Every result dict includes its inputs' tags (`"confidence": "PRELIMINARY — wave
  resistance and propulsor efficiency are declared estimates"`).
- A gate may **pass on VERIFIED/STANDARD**, may **pass provisionally on ESTIMATE with the
  band stated**, and must **refuse to evaluate on NOT-IMPL**.
- Stress-test decisions against ESTIMATE uncertainty: the EEDI study only calls an option
  OFFERABLE if it still complies at 1.25× installed power, because the power chain is
  ESTIMATE-tagged. Options with margins thinner than their uncertainty are hopes, not
  options (the 14 kn "solutions" had +0.5–4.1% margins).
- Warranty language, regulatory filings and owner offers may cite only VERIFIED/STANDARD
  numbers; where ESTIMATEs are unavoidable, the document says so in the same sentence.

## Gates

- Every constant in new computation code carries one of the four tags; a reviewer sweep
  counts untagged numeric literals in physics modules and treats each as ESTIMATE-by-default.
- Every NOT-IMPL function returns the structured OPEN record (reason, gates, action) — never
  a bare exception with no path forward.
- Every decision document states which tags its inputs carry; an offer/warranty/filing built
  on an ESTIMATE input says so in the same sentence.

## Prohibitions

- Never tune a caught mis-transcription until the output looks plausible — delete it.
- Never let an ESTIMATE cross into warranty, filing or owner-offer language untagged.
- Never implement a "temporary" recalled constant with a to-do note promising replacement; such notes rot. Refuse now.
- Never accept a number whose provenance nobody can name, including your own from last week.

## Reviewer behaviour

When reviewing someone else's calculation: list every constant, demand its tag, and treat
an untagged constant as ESTIMATE by default. Untagged constants inside rule-compliance code
are a BLOCKER, not a style note.

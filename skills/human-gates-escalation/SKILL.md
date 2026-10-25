---
name: human-gates-escalation
description: Defines the five fixed human sign-off points in the ship design pipeline and how to present open items, uncertainty and evidence at each - brief freeze, concept freeze, class submission, contract design, production release. Use whenever a stage ends at a human gate, when anything is refused or OPEN, and before any externally-binding statement.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: meta
  stage: cross-cutting
---

# Human Gates & Escalation

The agent prepares; a named human signs. Five gates are fixed — they are not configurable by
the agent, and no urgency justifies skipping one.

## The five gates

| # | Gate | Human | What the agent presents |
|---|---|---|---|
| 1 | **Brief freeze** | Owner + lead designer | brief.json, contradictions quantified, assumptions with consequences, open questions with what each blocks |
| 2 | **Concept freeze** | Naval architect of record | ≥3 candidates with scores AND why losers lost, gate discrimination status, all ESTIMATE tags, the OPEN list |
| 3 | **Class submission** | Engineer of record signs; class receives | compliance matrix incl. OPEN items, evidence links, the package from documentation-package |
| 4 | **Contract design** | Owner + yard + engineer | spec with provenance tags intact, warranty chain status, cost class and basis |
| 5 | **Production release** | Yard + class (plan approval) | production-design-handoff outputs, DR items closed or interim-assumed with acceptance |

## Escalation triggers (outside the gates — stop and ask)

- Novel hull type or configuration with no parent data.
- Anything requiring a model test the project has not commissioned.
- Rule interpretation not covered by the supplied rule set.
- Any safety-critical margin that cannot be verified deterministically.
- Commercial trade-offs: speed vs capacity vs fuel vs CAPEX (the EEDI tier table is exactly
  this — present tiers, never pick one silently).
- A gate that keeps failing after honest iteration: two failed attempts means escalate with
  the diagnosis, not a third silent retry.

## How to present (the format is the discipline)

1. **The question**, one sentence, with the decision it unblocks.
2. **Options**, each with: computed consequences, uncertainty and its tag, cost, what must
   still be verified. Tier tables beat paragraphs.
3. **The recommendation**, with the confidence it deserves — "recommended, contingent on
   replacing the ESTIMATE-tagged wave resistance before warranty" is a complete sentence.
4. **What you need from them**: signature, data, a decision between named options, or access
   (to class, to the yard, to the rule text).
5. **The OPEN register diff**: what opened/closed since the last gate.

Never minimise uncertainty at a gate. The moment an agent rounds a ±25% into a point value
to look decisive, the human's job becomes impossible — and the failure arrives later, at sea,
with interest.

## Records

Each gate produces: the presentation artefact, the decision, the decider, the date, and the
conditions attached ("approved subject to DR-014 closing before block division"). Conditions
become tracked OPEN items with owners. A gate passed without its record is a gate not passed.

## Prohibitions

- No externally-binding statement (to class, flag, owner, yard, vendor) issued by the agent
  as principal — always as preparation for a human signature.
- No gate skipped for schedule; a provisional pass is recorded as provisional, with the
  conditions and the expiry.
- No presenting a single option when a trade exists ("the answer is 12 kn" is malpractice
  when the tier table says 9–12.5 kn depending on risk appetite).

---
name: edi-trade-study
description: Resolves an EEDI/EEXI/CII failure into a quantified owner decision - grids speed x DWT/hull-stretch x ESD credit x fuel x waste-heat recovery, stress-tests every compliant option against installed-power uncertainty, and ranks by technology-risk tier. Use whenever attained EEDI exceeds required, when the owner asks what a fuel/ESD/speed change buys, or before fixing contract speed.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: naval architecture
  stage: S4
---

# EEDI Trade Study

"FAIL" is not a deliverable. The owner needs: which combinations close the gap, what each
costs, and how sure we are. The reference case (Handysize, attained 6.34 vs required 4.38,
−44.8%) grids 768 combinations; the method generalises.

## Model

- attained = [P_ME·C_ME·SFC_ME·(1−whr) + (P_AE−aux_esd)·C_AE·SFC_AE] · f_esd / (DWT · 0.75·V)
  with P_AE = 0.025·P_ME + 250 kW for bulk carriers (STANDARD, confirm for the type).
- required = a · DWT^(−c) · (1 − phase reduction); bulk carrier a = 961, c = 0.4778,
  Phase 3 = 30% (STANDARD — cite the resolution in force; the register from
  `regulatory-mapping` decides the phase by contract/keel/delivery dates).
- Power scaling across the grid: P₂ = P₁·(∇₂/∇₁)^(2/3)·(V₂/V₁)^n with **n swept over
  {2.6, 2.9, 3.2}** — an option compliant at only one n is FRAGILE and is labelled so.
- Hull-stretch variants at constant B/T/Cb: displacement ∝ length, lightship ∝ length^0.85
  (ESTIMATE — replace per variant with a real weight estimate before an offer).
- C_f: HFO/MDO/MGO 3.206, LNG 2.750 (STANDARD). **Methanol/ammonia/hydrogen: NOT-IMPL —
  refused**; read C_f from the amended guidelines.

## The two filters that make it honest

1. **ESD credit reality check.** f_esd is a parameter, not an entitlement. Any credit below
   0.90 requires model-test/CFD validation and Administration acceptance under the ESD
   framework — such options are REJECTED at concept stage, not banked. Credits 0.90–0.97
   carry a hard flag: "validation evidence required; not available at concept stage."
2. **Power stress.** The baseline MCR rests on ESTIMATE-class wave resistance, form factor
   and propulsor efficiency — worth ~25% easily. An option is OFFERABLE only if it still
   complies at 1.25× installed power, and the ceiling is reported across stress
   {1.00, 1.25, 1.50, 1.75, 2.00}. In the reference case this moved the offerable ceiling
   from 14 kn to 12.5 kn and exposed the decision cliff: **HFO-only tops out at ~10 kn
   nominal and ~9 kn stressed; beyond 1.5× power error there is NO conventional compliant
   option at any speed in the grid.** Margins of +0.5–4.1% (the 14 kn solutions) are inside
   the estimate's error band — hopes, not options.

## Output: the tier table (what the owner decides from)

For each technology-risk tier (0 = conventional HFO no credits → 5 = LNG + aggressive ESD +
WHR), the fastest OFFERABLE speed, the variant, cargo, fuel burn and margin. Tier 0 is
certifiable today; tiers 4–5 bet schedule on validation and bunkering availability. Then the
Pareto frontier on (speed, cargo, fuel, risk) — and the sentence every row carries: LNG
methane slip is not EEDI-visible and undermines the GHG case; EEXI and CII are separate
obligations NOT checked here.

## Gates

- Every "compliant" row also reports compliance across the full n range (robust/fragile).
- Offerable ≠ compliant: offerable requires surviving the declared power stress.
- DWT changes flow through BOTH attained and required (DWT is in both) — a stretch that only
  helps one side is a modelling bug.
- Sea-trial condition ≠ EEDI V_ref condition: the engine must satisfy both; say so.
- Caveats list is part of the JSON artefact, not just the chat.

## Prohibitions

- No C_f from memory for fuels outside the unambiguous set.
- No ESD credit assumed without the validation flag.
- No single-n recommendation.
- Never present the frontier without the tier-0 row — the owner is entitled to see the
  no-technology-bet option first.

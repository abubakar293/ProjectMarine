---
name: ship-sizing
description: Determines principal dimensions, displacement budget, weight groups and initial KG/VCG from the frozen brief and parent-ship data, with sensitivity analysis on which constraint binds first. Use at concept stage S1, and whenever the owner changes capacity, draft limits or speed.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: concept
  stage: S1
---

# Ship Sizing

Start from the mission and the parent ship, not from a template. Every number here is a
hypothesis that S2–S5 will verify; the point of S1 is to make the hypotheses explicit and
inside parent-ship bands.

## Procedure

1. **Gather parent data** (sister ship if the owner has one; else published series/statistics
   for the type). Record the source per value — this table is the calibration for every band
   you will use.
2. **Displacement budget**: Δ = lightship(steel + outfit + machinery, per `weight-control`)
   + deadweight(cargo + fuel + lube + fresh + ballast as required + crew/stores) + margin.
   Iterate: lightship depends on dimensions, which depend on Δ.
3. **Dimension drivers, in the usual order of brutality**:
   - draft/beam/air-draft limits (terminal, canal, bridge) — hard;
   - cargo volume vs stowage factor (holds, tanks, TEU cells, lane metres) — often governing;
   - required GM band and subdivision — governs beam and depth on many types;
   - speed vs length (Fn) and EEDI — governs Lpp for a given power budget;
   - structural bay lengths and standard plate/section sizes — nudge dimensions to
     buildable values (whole bay counts, standard widths).
4. **Coefficient selection** from the type's band (bulk carrier Cb 0.80–0.87, Cm 0.96–0.995;
   containership Cb 0.55–0.68; tanker 0.78–0.86; ferry/RoRo by deck-area driver; workboats by
   Fn and deck load). LCB near the type norm (bulk carrier ~50–51% Lpp); Cp = Cb/Cm must land
   in band — check the identity, do not pick coefficients independently.
5. **Freeboard and reserve buoyancy** early: Load Line often governs before stability does.
6. **Sensitivity output**: which constraint binds first if the owner pushes DWT +5%? Speed
   +0.5 kn? Draft −0.3 m? One page, quantified — this is what the owner actually needs.
7. **Initial KG** by weight-group build-up (`weight-control`), and a first GM check against
   the type's band. A GM wildly outside the band means KG or beam is wrong — bulk carriers
   loaded with dense ore run high GM (5–7 m) with short, snappy roll; container ships run
   low GM with long roll; both are deliberate, and both have operational consequences to
   flag.

## Gates

- Displacement budget closes within ±2% after iteration.
- All coefficients inside the parent band with the band's source cited.
- Cm·Cp = Cb identity holds to 1e-3.
- DWT/Δ, lightship/DWT inside type bands (bulk carrier lightship/DWT ≈ 0.19–0.28).
- Freeboard at the governing condition ≥ Load Line requirement (provisional until S7).
- LCG vs LCB within ~1–2 m at the main conditions, else compartmentation or cargo plan must
  move (defect #32: a cargo zone starting at 0.23·Lpp left LCG 8.5 m forward of LCB —
  no achievable trim).

## Prohibitions

- No silent template reuse: a "standard Handysize" is a starting hypothesis with its source
  stated, not an answer.
- Do not size to satisfy EEDI by derating speed without telling the owner — that is the
  `edi-trade-study` decision, made visibly.
- Do not report principal dimensions without the binding constraint named.

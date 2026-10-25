---
name: scantlings-midship
description: Sizes the midship section and local scantlings against supplied rule requirements - hull-girder section modulus, plate and stiffener sizing, utilisation reporting with clause citations - refusing rule constants that are not in hand. Use at S5 after structural loads, and for every structural revision loop with weight-control.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: structure
  stage: S5
---

# Scantlings & Midship Section

## Inputs (all from the record, none recalled)

- M_sw envelope from `structural-loads` (per condition), M_vw from rule text or OPEN,
  material grades (k-factors) per zone, corrosion additions per rule/owner, net vs gross
  convention declared on every number.

## Procedure

1. **Section modulus requirement**: Z_req = M_total / σ_allow with the rule's allowable and
   safety factors — from the supplied rule text, cited with edition. Report deck and bottom
   separately once the neutral axis is known; they differ unless NA is at mid-depth.
2. **Build the midship section transparently**: strength-deck stringer + deck longitudinals
   with effective attached plating, side shell, hopper/topside slopes, bottom longitudinals,
   girders/floors, inner bottom, coamings. Every item carries area, z, thickness, and an
   ESTIMATE tag until rule-derived. Effective width and shear lag per the rule — neglecting
   them overstates Z (the reference flags this explicitly).
3. **Local scantlings** by the rule formulas for the zone (bottom slamming zones, side load
   frames, deck cargo/bulkhead stool, hatch covers and coamings per their own rules), with
   corrosion additions and the rule's minimums; standardise to available plate/profile sizes
   (this feeds `production-design-handoff` — odd sizes cost money).
4. **Iterate with `weight-control`**: scantlings → steel weight → lightship → displacement →
   drafts/stability → loads → scantlings. Two or three passes usually; log each pass.

## Gates

- Utilisation < 1.0 everywhere with the clause cited per check; ≥ 0.85 somewhere, or you are
  carrying dead steel (cost finding, not just elegance).
- Z_deck inside the parent-ship band for the type and size (Handysize bulk carrier ~1.4e7–
  2.0e7 cm³ net — cite your band's source) AND consistent with the loads: if Z_req from your
  loads falls outside the band, ONE OF YOUR INPUTS IS WRONG — in the reference build, the
  allowable stress and the parent band were mutually inconsistent until the load model was
  fixed (defect #39).
- Steel weight from the section is plausible against the lightship (`weight-control` gates);
  strength area and mass are different quantities — holds are transversely framed, so the
  midship girder area must NOT be extrapolated along the length for steel weight (defect #44).
- Buckling and fatigue: screened with the rule's methods where available; where the rule
  requires direct calculation (spectral fatigue on critical details), flag the OPEN item —
  do not clear fatigue by neglect.

## Refusals

Rule formulas not in hand → OPEN with owner (structural engineer + class), exactly the
`structural-loads` pattern. No "typical" scantlings presented as rule compliance.

## Prohibitions

- No net/gross mixing within one utilisation.
- No thickness below rule minimums because "the FE says it works".
- No section-modulus victory lap before buckling and fatigue are screened — a girder that
  passes utilisation and fails buckling is a redesign, not a tweak.

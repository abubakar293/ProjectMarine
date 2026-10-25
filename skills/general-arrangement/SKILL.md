---
name: general-arrangement
description: Lays out the ship as constrained optimisation - longitudinal zoning, compartmentation, cargo interface, capacities and tank list from ONE geometry model shared with stability - with rule-driven checks on subdivision, escape, visibility and access. Use at S6, and re-entered whenever structure, stability or machinery moves a boundary.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: arrangement
  stage: S6
---

# General Arrangement

Arrangement is constrained layout, not freehand drawing. Every check here is computable:
volumes, areas, clearances, escape lengths, rule-mandated separations.

## Procedure

1. **Longitudinal zoning** consistent with the FROZEN subdivision from damage stability —
   moving a bulkhead after the damage analysis invalidates it (one geometry, hashed).
   Cargo zone placement decides trim feasibility: check LCG vs LCB immediately after zoning
   (defect #32: cargo starting at 0.23·Lpp left LCG 8.5 m forward of LCB — no achievable
   trim, caught only by the equilibrium solver pinning at its clip).
2. **Cargo interface**: holds/tanks/cells/lane metres vs the brief; hatch covers and crane
   envelope; lashing points and loads; grain fittings; vehicle deck clearances and ramp
   geometry; heavy-lift deck strength; stowage factors vs the capacity target; cargo access
   (grab reach, forklift routes, container cell guides).
3. **Compartmentation & watertight integrity**: bulkhead positions per Load Line/SOLAS
   (collision, after-peak), watertight doors/hatches/penetrations with indication,
   cross-flooding arrangements with equalisation times matching the damage model's assumptions.
4. **Fire & escape**: zones and A/B/C divisions per the supplied rule set; two escape paths,
   dead-end limits, widths; machinery-space protection; dangerous-goods segregation; for gas
   fuels the IGF/IGC safety zones and hazardous-area classification — which are ARRANGEMENT
   objects, decided here, not in systems.
5. **Capacities & tanks**: the tank list IS the stability model's tank list — same boxes/
   surfaces, same hash. Capacities plan, sounding tables, free-surface data, vent/overflow/
   sounding pipes, coatings, heating. A capacities plan that disagrees with the stability
   model by "a few cubic metres" is a document-control BLOCKER (fleet checks name-set and
   volume equality).
6. **Visibility & deck working**: bridge visibility per SOLAS V/22 (the blind-sector
   computation is geometry — compute it); pilot transfer arrangements; mooring equipment
   per the class guidance in force; towing/escort; liferaft launching zones clear of
   obstructions.
7. **Reserves**: stowage factor margin, future-refit space and weight margins, documented —
   owners always ask later; the ask is cheaper now.

## Fuel & ballast placement (hard-won)

Fuel capacity must deliver the brief's range with the consumption from `resistance-powering`
— the reference design's first tank list carried 790 t for a 12,000 nm trade needing ~2,800 t
(defect #33): a ship that cannot carry its own fuel is not a design. Fuel tanks do not sit
inside the cargo zone (breach risk on grounding/collision; MARPOL protective-location rules
apply by type and date). Ballast capacity must give the ballast-condition drafts the propeller
immersion, bow visibility and slamming checks require — verify against the actual ballast
departure condition, not a guess.

## Gates

- Capacity ≥ brief target with the stowage factor stated; holds do not overlap; tanks inside
  hull envelope, above baseline, clear of cargo zone.
- Range from tank capacity ≥ brief range (feeds R-07 traceability).
- LCG−LCB within trim feasibility at all governing conditions.
- One tank model, verified by name-set and volume equality between capacities and stability.
- Escape, visibility, fire-zone checks computed, with the rule basis cited or OPEN.

## Prohibitions

- No layout drawn before subdivision is frozen.
- No vendor envelope assumed (see `machinery-layout`).
- No "we'll route it later" through a structural member without a penetration schedule.

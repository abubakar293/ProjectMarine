---
name: cost-estimating
description: Produces cost estimates with declared basis, exclusions and confidence class - steel and equipment quantities from the design record, labour by zone, yard overhead, owner's items - from class-5 screening to class-3 budget. Use at S8, for EEDI/owner trade studies, and whenever a design change needs a price tag.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: compliance
  stage: S8
---

# Cost Estimating

An estimate without a basis is a number with amnesia. Declare class, basis date, exclusions,
and what would move it.

## Structure

- **Materials**: hull steel (from `weight-control` take-off) at quoted plate/profile prices
  per size class; main engine and gensets (vendor budget quotes — REQUEST, never catalogue
  memory); major equipment list (cranes, hatch covers, windlass, BWMS, scrubber/SCR if
  fitted — the emission-package decision from `edi-trade-study` is a COST decision: an ESD
  credit that needs a validated duct is capex); outfitting by zone factors calibrated to the
  yard.
- **Labour**: man-hours by zone (hull assembly, erection, outfitting, painting, commissioning)
  from the yard's standards — which is why `shipyard-data-requirements` exists; without them
  you are quoting another yard's productivity.
- **Yard**: dock/berth occupancy against the build strategy, overhead, margin.
- **Owner's items**: separate section, always — crew, spares, first fill, supervision.
- **Escalation & currency**: basis date, steel index reference, FX assumptions.

## Confidence classes

Say which one you are in: class 5 (factored, ±30–50%) at concept; class 4 at preliminary
with vendor quotes landing; class 3 (±10–20%) for budget with real quotations and the yard's
labour standards. The design record states the class next to the number, and the EEDI/EEXI/
trade studies carry it too — an owner comparing a tier-0 and tier-5 EEDI option is comparing
CAPEX as well, and the ESD validation cost belongs to the option.

## Trade-study coupling

Every option table you produce (`edi-trade-study`, speed-vs-size, fuel choice) should carry a
delta-cost column once class 4 data exists: Δsteel from the stretch variants, Δengine from
re-rating, Δcapex from LNG tanks/bunkering vs ESD hardware. The cheapest compliant tonne is
the decision; EEDI alone is half of it.

## Gates

- Steel quantity traces to the weight record (no parallel quantity).
- Every equipment line has a quote, a budget price with date, or an ESTIMATE tag with the
  band — never a recalled "market price".
- Sum of parts reconciles with the total (a rounding drift > 0.5% means a line was dropped).
- Exclusions listed as prominently as inclusions.

## Prohibitions

- No single-point number without a class and a date.
- No yard labour standards invented — request them (`shipyard-data-requirements`).
- No hiding the ESD/fuel capex in "miscellaneous" — it is the owner's decision variable.

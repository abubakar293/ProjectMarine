---
name: machinery-layout
description: Lays out the engine room and machinery - main engine envelope, shaft line, auxillaries, uptake, fuel and alternative-fuel systems, maintainability - driven by VENDOR DATA requests, never assumed envelopes. Use at S6 once propulsion is selected, and again at every vendor data drop.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: arrangement
  stage: S6
---

# Machinery Layout

## The vendor-data rule

Every envelope in this skill is a REQUEST until a datasheet arrives: main engine (dimensions,
mass, MCR/derating curves, turbocharger clearance, crankthrow access), gearbox, shaft line
(bearings, sterntube, coupling), propeller (diameter, boss, pull-out), thrusters, rudder and
steering gear, generators, switchboard, boilers, purifiers, cranes, hatch hydraulics, HVAC
units, exhaust treatment (scrubber/SCR volumes are enormous and arrive late — reserve them
from day one), BWMS (UV/reactor volumes), fuel-gas systems (compressors, vaporisers,
water/glycol, safety zones).

**Assumed envelopes are the machinery-layout failure mode**: the engine fits on paper, then
the datasheet arrives and the ER is 1.5 m short, the pull-out hits a frame, and the crane
cannot lift the liner. Record each assumption as an OPEN item with the datasheet request ID
and a due date; re-run the layout checks on every data drop; log which checks changed verdict.

## Layout checks (computable)

- Envelope + clearances: turbocharger top clearance, crane hook path over every lift item,
  working clearances per maker/class, escape routes from every working platform (two ways out).
- **Pull-out lengths**: engine components, purifiers, heat exchangers, pump rotors — to the
  ER hatch or a removal route. This check catches more redesigns than any other.
- Shaft line: bearing count and spacing, alignment (hot/cold), sterntube length vs rule,
  aperture and bossing clearances, propeller immersion at ALL approved drafts (ballast
  governs — link to the stability conditions), rudder area/horn clearances.
- Uptake & funnel: exhaust routing with maker bends/velocities, SCR/scrubber integration,
  uptake gas temperature at boundaries, soot-blower discharge clearances, spark arrest where
  the trade requires (e.g., grain, timber).
- Air & ventilation: ER supply/extract sizing against heat rejection at the service point,
  engine air demand including derating for temperature, intake/exhaust separation,
  gas-fuel ER ventilation regimes and hazardous-zone classification for alternative fuels.
- Fuel systems: service/settling capacity for the consumption profile, overflow/quick-
  closing arrangements per rule, gas-fuel systems per IGF (bunker station location,
  compressor room separation, gas detection, ESD logic — arrangement objects per the code,
  from supplied text).
- Acoustics/vibration: cabin limits (from owner spec / comfort class), isolation on
  generators and pumps under accommodation, shaft alignment excitation screening.
- Maintainability: workshop, spares stowage (owner's list), lube-oil drain/transfer,
  bilge arrangements, machinery control room position and sightlines.

## Electrical interface

The load balance (`marine-systems`) decides generator count/size; layout must then fit them
plus switchboard room (with the rule's separation from fire zones) plus cable routes. A
generator set changed after layout is a re-run of everything above — freeze the load balance
before detailed ER layout.

Typical clearance starting points (verify against maker/class requirements; all ESTIMATE
until then): 600 mm working access around auxiliaries, 450 mm minimum escape-route width at
obstructions, 1.9-2.0 m headroom on escape routes, >= 300 mm pipe-to-cable-tray separation
where heat is a factor, turbocharger rotor-extraction clearance per maker (commonly >= 1.5 m
to the hatch coaming).

## Gates

- Every envelope in the layout cites its datasheet revision, or is flagged ASSUMED with a
  request ID and date.
- Pull-out, hook-path and escape checks pass at every equipment revision.
- Propeller immersion ≥ maker minimum at ballast and scantling conditions.
- Ventilation flow matches heat rejection at the service point with the declared derating.

## Prohibitions

- No "standard ER" reuse across different engines — the envelope IS the design driver.
- No safety-zone sketching for gas fuels from memory: IGF/IGC zone geometry from supplied text.
- No layout frozen while a governing datasheet is outstanding; freeze provisional and say so.

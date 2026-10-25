---
name: marine-systems
description: Designs and checks marine systems - piping and hydraulics, electrical load balance and distribution, HVAC, fire-fighting, ballast and bilge, automation and navigation - with rule-based checks on capacities, redundancy and separation. Use at S6 for all systems design, and whenever machinery or arrangement changes.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: arrangement
  stage: S6
---

# Marine Systems

Systems are where arrangement becomes physics: flows, heads, loads, capacities. Every check
below is computable from the model and the rule set.

## Piping & hydraulics

- Line sizing by flow/velocity limits per service (cargo, ballast, fuel, fire, bilge,
  sanitary); pressure-drop calculations to the terminal equipment; pump duties (head + flow
  + NPSH margin against actual tank levels and temperatures).
- Ballast/bilge capacities per rule: pumping rates and times from supplied clause text;
  ballast system must achieve the loading conditions' sequencing (BWM treatment integration
  — USCG/IMO approval status of the unit is vendor data).
- Fuel service: transfer, settling/service, overflow, quick-closing valves, venting per rule;
  gas-fuel piping per IGF (double-walled/bunded routing, gas detection, ventilation
  interlocks, ESD philosophy) — from supplied text, zones coordinated with `machinery-layout`.
- Cargo systems by type: tank heating (coil sizing against the cargo's viscosity/temperature
  profile), stripping, PV valves and inert gas/nitrogen for tankers, grain aeration, hold
  drainage and bilge wells for bulk carriers, CO2 for vehicle decks.
- Materials per service and rule (cargo-compatible, low-temp for LNG, cupro-nickel/duplex
  where seawater rules require); penetration scheduling against the structural model —
  every penetration in one schedule, checked against scantlings and fatigue details.

## Electrical

- **Load balance** first: consumers by mode (sea, harbour, cargo, emergency, blackout
  recovery), diversity applied per class guidance, generator sets sized so the largest-unit-
  out condition still covers the mode — this is the rule's redundancy requirement, compute it.
- Emergency source: location (above the bulkhead deck, outside machinery space per rule),
  capacity and duration per ship type, transient behaviour.
- Single-line diagram, cable routing with separation of redundant paths (DP and passenger
  ships have hard separation rules — from supplied text), short-circuit levels vs breaker
  ratings, voltage drop checks, hazardous-area equipment categories per the zone map.
- Shore power where the trade/port requires (AMP-ready is cheap now, retrofit is not).

## HVAC & accommodation systems

- Cabin/ER/control-room loads; pressurisation strategy for gas-fuelled ships (accommodation
  positive to hazardous zones); fresh water make/storage against the crew count and the
  range; sanitary and grey/black water per MARPOL IV + discharge restrictions of the trade;
  refrigeration and provisions per crew/owner spec.

## Fire-fighting (compute against the supplied FSS Code)

- Fire main: ring capacity, hydrant coverage (every location reachable by two jets from
  different hydrants — a coverage computation on the GA), pump capacity and redundancy,
  isolation valves.
- Fixed systems by space type: machinery (CO2/water mist/foam per rule and owner), cargo
  (holds: CO2 or inerting for bulk; sprinkler/drencher for vehicle/RoRo; container deck
  provisions), accommodation (detection zoning + portable).
- Detection & alarm coverage per space category; alarm philosophy to the automation system.
- Fire control plan is a deliverable of THIS stage (it is the systems model rendered).

## Automation & navigation

- Alarm/monitoring coverage list; bridge layout per `general-arrangement` visibility results;
  navigational equipment per SOLAS V by GT (from supplied text); DP/position-reference
  redundancy where the notation applies; cybersecurity per class notation (IACS UR E26/E27
  apply to newbuilds by date — check the register).

## Gates

- Pump/breaker/ventilation sizing traces to a computed duty with the rule clause cited.
- Largest-unit-out and blackout-recovery cases pass in every operating mode.
- One penetration schedule, zero un-scheduled penetrations against the structural model.
- Fire coverage computed on the actual GA, per hydrant.

## Prohibitions

- No system capacities from "sister ship" without the duty calculation on THIS ship.
- No FSS/IGF/SOLAS-V equipment lists recalled from memory — supplied text or OPEN.
- No redundancy claim without the failure case computed.

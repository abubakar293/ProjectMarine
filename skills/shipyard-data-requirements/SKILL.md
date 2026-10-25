---
name: shipyard-data-requirements
description: Specifies and requests the yard, vendor and class data the design pipeline cannot invent - crane and dock limits, panel-line capabilities, labour standards, weld procedures, vendor envelopes and datasheets - turning each gap into a tracked request with a due date. Use at project start and whenever a gate reports missing external data.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: production
  stage: S0-S8
---

# Shipyard Data Requirements

The pipeline refuses to invent external data; this skill is how the refusals become
procurement. Every OPEN item that says "yard/vendor/class data required" turns into a
tracked request with an owner, a due date, and the design decision it blocks.

## The standard request list

**Yard capability (blocks `production-design-handoff` and constructability scoring):**
- crane capacities (dock, berth, assembly shop) and radii; dock/berth dimensions and
  load-bearing; maximum block weight and size; panel-line dimensions and throughput;
  CNC cutting/ marking capability (max plate thickness, bevel types); bending capacity
  (cold/hot, max section); welding processes qualified (WPS/PQR list) — one-side welding,
  FCB, vertical; painting shop limits; ERP/planning system interfaces and data formats.

**Yard standards (blocks production design):**
- standard plate widths/lengths stocked; standard profile list; typical stiffener spacings;
- bracket and lug standards; weld-groove standards; block-division philosophy and joint
  locations; tolerance standards (build margins, compensation practice); nesting software
  and its input formats (DXF/STEP conventions, layer standards).

**Vendor data (blocks `machinery-layout` and `marine-systems`):**
- datasheets per the equipment list, with the revision that the layout cites; masses and
  CoG for the weight record; maintenance access and pull-out dimensions; utility demands
  (power, cooling, air, drains) feeding the load balance.

**Class/flag (blocks `class-statutory-compliance`):**
- rule documents and editions in force; unified interpretations and circulars; AIP
  requirements for novel features; plan-approval submission formats.

**Owner (blocks `owner-brief-intake` completeness):**
- operating profile details, spares philosophy, crew documentation, any parent-ship data
  they hold — owners sitting on a sister ship's inclining test and sea-trial report are
  sitting on your best calibration data; ask early.

## Tracking

A `data_requests.json` in the design record:

```json
{"id": "DR-014", "to": "yard", "item": "crane capacity chart, dock 2",
 "blocks": ["production-design-handoff:block-division", "cost-estimating:labour"],
 "requested": "2026-10-01", "due": "2026-11-01", "status": "outstanding",
 "interim_assumption": {"value": "600 t @ 30 m", "tag": "ESTIMATE", "risk_if_wrong": "block division rework"}}
```

Where the schedule forces progress before the data lands, record the interim assumption
WITH its tag and its risk-if-wrong — that is how an assumption stays visible instead of
becoming concrete.

## Gates

- Every OPEN item whose action names external data has a DR id.
- No layout freeze while a governing DR is outstanding without a recorded interim assumption
  and an owner acceptance.
- The constructability reviewer may only score against real yard data — scoring against
  invented limits is a BLOCKER (fleet finding G03).

## Prohibitions

- No "typical yard" values presented as this yard's.
- No vendor envelope from a sister ship's memory of a datasheet.

---
name: regulatory-mapping
description: Maps flag, class, ship type, trade and fuel to the complete set of applicable statutory instruments, class rules and codes, and builds the applicable-rule inventory with editions. Use after the owner brief is frozen, before any compliance claim, and whenever flag, class, trade or fuel changes.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: intake
  stage: S0
---

# Regulatory Mapping

A compliance matrix against the wrong instrument list is worse than none: it manufactures
confidence. Map first, cite editions, and mark applicability per clause.

## Build the inventory

For {flag, class, ship type, GT/DWT, trade (incl. polar waters?), fuel, build date}:

- **SOLAS** chapters applicable by ship type and size (II-1 subdivision & stability —
  probabilistic damage for cargo ships above threshold; II-2 fire — check which fire
  integrity regime; V navigation incl. bridge visibility; carriage of cargoes — IMSBC/IGC/
  IGF as relevant).
- **MARPOL** annexes: I (oil — check double-hull/protection-of-fuel-tank requirements by
  build date), IV/V (sewage/garbage), VI (NOx Tier by keel date and ECA trading, SOx/EGCS,
  **EEDI phase by contract/keel/delivery dates, EEXI, CII**).
- **Load Line** (freeboard, zone/seasonal, timber if applicable), **Tonnage** (GT drives
  manning, fees, and which rules apply — a TONNAGE-driven threshold crossed by a design
  change is a classic late-project shock).
- **2008 IS Code** (intact; weather criterion), **CSR** (IACS Common Structural Rules for
  bulk carriers/oil tankers — confirm which, and the edition + unified interpretations in
  force), Polar Code (if polar), HSSC/IMSBC/IBC/IGC/IGF by cargo/fuel, HSC Code if fast,
  small-craft regime (ISO 12217 series / Recreational Craft Directive) if applicable, AFS/
  BWM systems.
- **Flag circulars and class guidance** — these change; request the current list rather than
  recalling it.
- **Shipyard's build standard** and the owner's extra requirements (they can exceed rules).

## Output: applicable-instrument register

```json
{"instrument": "MARPOL Annex VI", "chapter": "4", "applies": true,
 "basis": "cargo ship >= 400 GT, contract date after <phase 3 threshold>",
 "edition": "as amended by MEPC.xxx(YY) — CONFIRM with flag",
 "requirements_flowdown": ["R-05 EEDI Phase 3"], "evidence_target": "EEDI technical file"}
```

Each row: applies (true/false/conditional), the *basis* for applicability (the size/date/type
threshold that triggers it), edition **to be confirmed against the documents in force** —
you cite what the user supplies or what you fetch with permission; you never cite an edition
from memory.

## Gates

- 100% of instruments have an applies true/false/conditional verdict WITH the basis
  (threshold + edition) written down; zero "probably applies".
- EEDI phase determined from contract/keel/delivery dates and stated numerically.
- Every flowdown requirement maps to at least one brief requirement ID (or is added to the
  traceability matrix).

## Feeds

- `class-statutory-compliance` builds the clause-level matrix from this register.
- The EEDI phase in the register drives `edi-trade-study` (phase 2 vs 3 changes required by
  30 points).
- Fuel policy drives IGF/IGC applicability and therefore arrangement safety zones — mapping
  must happen BEFORE `general-arrangement`, not after.

## Prohibitions

- No "standard for this type" hand-waving: applicability is a threshold check with the
  threshold written down.
- No rule text quoted from memory anywhere downstream; this register records *what applies*,
  the clause database records *what it says*, both from supplied documents.
- Do not mark an instrument N/A without the basis field.

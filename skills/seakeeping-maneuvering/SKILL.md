---
name: seakeeping-maneuvering
description: Assesses motions, accelerations, slamming, green water, operability and manoeuvring - RAOs against operational sea spectra, MSI/VSI limits, IMO manoeuvring criteria for the manoeuvring booklet. Use when the brief includes crew transfer, helicopter operations, cargo-weather limits, comfort class, polar operation, or any IMO manoeuvring requirement.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: naval architecture
  stage: S3-S4
---

# Seakeeping & Manoeuvring

Only in scope when the mission needs it — but when it does, it governs (crew transfer vessels,
offshore, passenger comfort, high-freeboard RoRos in beam seas). Scope it from the brief's
operational profile, not from habit.

## Seakeeping

- Method ladder: strip theory / 3D panel (frequency domain) for screening → CFD or model
  test where the decision is expensive. State the method per result.
- RAOs for heave/pitch/roll at the operational headings; roll damping is the weak link —
  Ikeda-style components or test data, declared.
- Against sea spectra (JONSWAP/Pierson–Moskowitz) for the ACTUAL trade: North Atlantic
  for most, but a coastal CTV lives in operational sea states, not scatter diagrams of the
  North Atlantic.
- Criteria with sources: MSI/VSI limits (crew comfort, typically MSI < 0.2 for sustained
  operations — cite the standard the owner contracted to); motion limits for cargo ops and
  helicopter (from the operator's documentation); slamming (STAW-2 or class criterion) and
  green water where flare/bow shape says it is credible; parametric roll screening for
  containerships in following/quartering seas; second-generation intact stability criteria
  where the flag applies them — **level-1/level-2 assessment procedures come from the MSC
  circular in force: encode from supplied text or OPEN, never recall.**
- Deliverable: operability matrix (Hs × Tz × heading → allowed/not, with the limiting
  criterion named per cell).

## Manoeuvring

- IMO manoeuvring criteria apply per the ship's rule set (turning ability, initial turning/
  course-keeping, yaw checking, stopping, crash-stop). The thresholds and the test programme
  come from the resolution in force — cite it.
- Prediction: MMG-style or class-accepted empirical method for the booklet draft; **sea
  trials validate**; the booklet is a controlled document — version it against the trial data.
- Rudder and thruster sizing flows from here and from `machinery-layout`; DP classes (if any)
  change the whole redundancy conversation — catch it in `owner-brief-intake`, not here.

## Gates

- Every criterion cites its source document + edition or is OPEN.
- Roll damping method declared; results flagged sensitive to it (they always are).
- Operability matrix cells name the limiting criterion.
- Manoeuvring booklet draft marked DRAFT-PENDING-TRIALS until trials data replaces predictions.

## Prohibitions

- No comfort/operability claim without the criterion's source (marketing "smooth ride" is
  not a criterion).
- No model-test data cited that nobody ran.
- No parametric-roll dismissal for a containership because "GM is fine" — that is the
  condition under which it happens.

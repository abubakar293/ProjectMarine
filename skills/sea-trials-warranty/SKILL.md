---
name: sea-trials-warranty
description: Plans sea trials and manages the speed-consumption warranty chain - trial programme, ISO 15016 correction plan, measurement uncertainty, exclusion clauses, and the evidence chain from prediction to trial to in-service. Use at S9, before contract signature on any performance warranty, and when trial results arrive.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: delivery
  stage: S9
---

# Sea Trials & Warranty

The warranty is where preliminary design meets contract law. Everything upstream tagged
ESTIMATE comes due here.

## Trial programme

- Speed trial: measured mile/run per ITTC and the class procedure; displacement and draft
  measured (draft survey ±1% flows straight into the power correction — say so in the plan);
  water temperature/salinity measured; wind and current logged for exclusion decisions;
  shaft power/torque and RPM measured (not inferred); GPS/Doppler speed difference recorded
  (±0.1 kn is the usual instrumentation reality).
- Consumption: measured over the trial window against the declared auxiliary load state.
- Other trials: stopping, turning, crash-stop, bow-thrust tests per the manoeuvring booklet;
  inclination test (closes the weight record); anchor, steering, alarm/blackout, ESD function
  tests; noise and vibration measurements against the owner spec/comfort class.
- The correction plan BEFORE the trial: ISO 15016 method declared (which roughness/wind
  correction, what fouling allowance, what trial-condition conversion) — agreeing the method
  after results arrive is how disputes start.

## Warranty chain discipline

- Warranty curves derive from the VERIFIED powering chain only. If the chain still carries
  ESTIMATE links (form factor, R_W allowance, η₀) at contract time, either replace them
  (model test — for a series this pays for itself) or the warranty language carries explicit
  exclusion clauses and a weather/fouling allowance with numbers.
- The record links: prediction (with margins per column) → trial result (with corrections
  per the declared method) → warranty statement. A warranty number without that chain is a
  bet.
- Under-speed diagnosis playbook in the trial report: fouling, displacement error, shallow
  water, fuel LCV, pitch setting, engine derate, air temperature — apply corrections before
  blame.

## In-service feedback

- First-year consumption vs prediction; CII rating trajectory against the `edi-trade-study`
  assumptions; the delta calibrates the parent-ship bands for the next vessel — feed it back
  into `weight-control` and `resistance-powering` bands. This loop is what turns one ship
  into a series advantage.

## Gates

- Trial programme covers every warranty item and every rule-required trial (class and flag).
- ISO 15016 method and exclusion clauses agreed IN THE CONTRACT, cited by clause.
- Measurement uncertainty propagated into the pass/fail band — a warranty met by 0.05 kn
  inside a ±0.1 kn measurement is not met, it is unresolved; say which.
- Inclining result within the weight record's margin, else the stability booklet re-runs
  BEFORE delivery documents sign.

## Prohibitions

- No warranty built on an ESTIMATE-tagged link without the exclusion language.
- No post-hoc choice of correction method.
- No trial report without the measurement conditions (they are the report).

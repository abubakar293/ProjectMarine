# Case study: the EEDI trade, done properly

This is what "refuse to hide a failure, quantify the trade" looks like in practice. It is the
worked example behind the `edi-trade-study` skill.

## The failure

The reference Handysize bulk carrier (DWT 37,669 t, 14 kn, HFO) **fails EEDI Phase 3**:

```
attained 6.342  vs  required 4.379 gCO2/(t·nm)   margin −44.8%   → BLOCKER
required = 961 · DWT^(−0.4778) · (1 − 0.30)          [MEPC.215(63) reference line, Phase 3]
```

Reporting "FAIL" is not engineering. The owner needs: *which combination of speed, size and
technology closes the gap, what does each cost, and how sure are we?*

## The model

- Installed power scales as `P₂ = P₁ · (∇₂/∇₁)^(2/3) · (V₂/V₁)^n`. The displacement exponent
  is standard low-Fn scaling; **n is not exactly 3** at Fn ≈ 0.17, so every option is
  evaluated across n ∈ {2.6, 2.9, 3.2}. An option compliant only at one n is flagged
  *fragile* (37 of 768 grid points were).
- `P_AE = 0.025·P_ME + 250 kW` (bulk-carrier form).
- Hull stretch variants: Lpp × {1.00, 1.05, 1.10, 1.15} at constant B/T/Cb — displacement
  scales linearly, lightship with exponent 0.85 (ESTIMATE, tagged).
- Fuels: HFO (C_f 3.206) and LNG (C_f 2.750). Methanol/ammonia C_f values are **NOT-IMPL —
  refused**, because they must be read from the amended guidelines, not recalled.
- ESD credits: parameterised `f_esd ∈ [0.85, 1.00]` with a hard screen — any credit below
  0.90 requires model-test/CFD validation and Administration acceptance, so such options are
  rejected at concept stage rather than banked.
- The grid: 4 variants × 8 speeds × 6 ESD factors × 2 fuels × 2 WHR options = **768
  combinations**.

## The filter that matters: power stress

The baseline MCR (4,361 kW) rests on ESTIMATE-class wave resistance (15% ± 8 pts of R_F), an
ESTIMATE form factor (1+k = 1.45, band 1.30–1.60) and ESTIMATE wake/thrust-deduction/η₀.
Together those are easily worth 25% on installed power. So an option is only **OFFERABLE** if
it still complies when MCR is multiplied by a stress factor:

| Power stress | Compliant | Offerable | Ceiling (any tech) | HFO-only ceiling |
|---:|---:|---:|---:|---:|
| 1.00× | 413 | 413 | 14.0 kn | 10.0 kn |
| 1.25× | 413 | 201 | 12.5 kn | 9.0 kn |
| 1.50× | 413 | 95 | 11.0 kn | — |
| 1.75× | 413 | 48 | 10.0 kn | — |
| 2.00× | 413 | 15 | 9.0 kn | — |

The 14 kn "solutions" have margins of **+0.5% to +4.1%** — entirely inside the error band of
the power estimate. They are hopes, not options. **The headline for the owner: at nominal
power a conventional HFO ship tops out at ~10 kn; 14 kn exists only with zero margin.**

## Fastest offerable speed by technology-risk tier (1.25× stress)

| Risk tier | Speed | Config | Cargo | Margin |
|---|---:|---|---:|---:|
| 0 — conventional: HFO, no credits | 9.0 kn | stretch-15% | 41,029 t | +28.2% |
| 1 — HFO + small validated ESD | 9.0 kn | + WHR 5% | 41,029 t | +31.1% |
| 2 — LNG, or larger ESD credit | 11.0 kn | LNG | 41,029 t | +27.3% |
| 3 — LNG + ESD | 11.0 kn | LNG + WHR | 41,029 t | +30.3% |
| 4 — LNG + ESD + WHR | 12.0 kn | f_esd 0.97 | 41,029 t | +22.7% |
| 5 — all three, aggressive credit | 12.5 kn | f_esd 0.92 | 41,029 t | +21.8% |

Every tier is a real decision with a real owner: tier 0 is certifiable today; tiers 4–5 bet
the schedule on an ESD validation and LNG bunkering availability at every port on the trade.

## What the study refuses to claim

- LNG's methane slip is **not** credited by EEDI and undermines the GHG case — stated on
  every LNG row.
- EEXI and CII are separate obligations and are **not checked** — stated, not silently
  omitted.
- Lightship scaling (0.85 exponent) is ESTIMATE-class; a real weight estimate per variant is
  required before any of this becomes an offer.
- The sea-trial speed condition ≠ the EEDI V_ref condition; the MCR must satisfy both.

## Reproduce

```bash
cd reference-implementation/code && python3 edi_trade.py
# -> reference-case/edi_trade_study.json  (grid, frontier, tiers, stress sweep, caveats)
```

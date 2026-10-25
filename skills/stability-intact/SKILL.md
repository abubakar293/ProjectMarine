---
name: stability-intact
description: Runs intact stability for all loading conditions - load cases, free-surface corrections, GZ curves, and 2008 IS Code criteria cited clause by clause, with the weather criterion refused until Code tables are supplied. Use for every vessel at S3 and whenever weights, tanks or KG change.
license: MIT
metadata:
  author: ProjectMarine contributors
  version: "0.1.0"
  domain: naval architecture
  stage: S3
---

# Intact Stability

## Load cases (minimum set; the type adds more)

departure / arrival full cargo; full and partial ballast departure/arrival; heavy weather;
cargo-specific cases (grain heeling per the Grain Code, timber deck cargo per the Timber
Code, containers with wind pressure on deck cargo, vehicle decks with water accumulation,
liquid sloshing where relevant); crane-lift and Ro-Ro loading cases where fitted; worst-case
slack-tank combination — the FSC-maximising tank set, not the first one that occurs to you.

## Compute, never estimate

- KG by weight-group build-up (`weight-control`), VCG per tank from actual geometry.
- Free-surface correction per actual tank fluid surface at the sounding — not a guessed
  "0.1 m". Rectangular approximation only where the tank is a box; report the method.
- GZ at constant displacement (sinkage re-solved per heel — see `hydrostatics-crosscheck`),
  0–90° at ≤5° steps to 40° then ≤10°.
- Downflooding angle from actual openings; the areas to 40° are cut at flooding if earlier.

## 2008 IS Code Part A criteria (cite clause, computed value, verdict)

| Clause | Criterion | Limit |
|---|---|---|
| 2.1.1.1 | Area 0–30° | ≥ 0.055 m·rad |
| 2.1.1.2 | Area 0–40° (or flooding) | ≥ 0.090 m·rad |
| 2.1.1.3 | Area 30–40° (or flooding) | ≥ 0.030 m·rad |
| 2.1.2 | GM_fluid | ≥ 0.15 m |
| 2.1.3.1 | **GZ at φ = 30°** | ≥ 0.20 m |
| 2.1.3.2 | φ at GZmax | ≥ 25° |
| 2.2 | Weather criterion K = area(b)/area(a) | ≥ 1.0 |

Note 2.1.3.1 is GZ **at 30°** — taking max GZ beyond 30° over-credits the design and can
pass a hull whose arm has already collapsed (this was a live defect in the reference build).
Small craft follow ISO 12217 categories instead; HSC follow the HSC Code; passenger ships
add their own regimes — the `regulatory-mapping` register says which stack applies.

## The weather criterion: refused, not recalled

K needs the Code's tabulated wave-slope coefficients X1/X2, roll-radius k, and the standard
roll-period formula. **Compute the unambiguous parts (PW1 = p·A_T·z/(g·Δ), PW2 = 1.5·PW1, the
area integrals) and return the criterion OPEN** with the action "run in class-approved tool
or encode tables from a licensed Code copy". A separate function may accept a roll angle
**supplied by an authoritative source** — keep that boundary structural so an agent cannot
compute K itself by accident. Windage area A_T comes from the silhouette model, not from
0.35·B·(T+6) — that crude form is for early screening only and must be tagged ESTIMATE.

## Gates

- All evaluated criteria PASS in ALL load cases, or the condition is rejected/limited and
  the limitation is written into the stability booklet language.
- GZ(0) = 0 within 1e-3 m; dGZ/dφ|₀ = GM within 3% (cross-checks against upright hydrostatics).
- Angle of loll distinguished from list wherever GM_fluid < 0.5 m; no condition shipped with
  negative GM_fluid without an explicit operational restriction and owner acceptance.
- Slack-tank count and FSC reported per condition; FSC > 20% of GM triggers a re-ballast study.

## Prohibitions

- No criterion evaluated against a recalled limit without the clause ID + edition in the record.
- No "GM is large so it's safe" — high GM means short roll period, cargo/gear loads, crew
  comfort and possible parametric-roll exposure (container ships); report the operational side.
- No stability booklet generated from a different tank/weight model than the analysis
  (single source of truth; booklet carries the geometry hash).

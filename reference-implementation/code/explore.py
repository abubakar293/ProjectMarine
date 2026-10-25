"""
Design-space exploration and the automated reviewer gate.

The pattern this implements is the one that has been shown to work in agentic marine /
offshore engineering: generate several structurally different candidates, score each with
deterministic piecewise-linear functions on a fixed set of axes, and stop only when a
candidate clears a composite threshold with no sub-score below its floor. Without the
floor, an optimiser simply trades a failing axis away against a passing one.

Scores here are computed only from quantities the pipeline actually produces. Axes that
would need data the pipeline does not have (fatigue life, real constructability from yard
limits) are reported as NOT SCORED rather than being given a flattering proxy -- an
unscored axis is visible, a fabricated one is not.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np

import hull_parametric as H


@dataclass(frozen=True)
class ReviewerConfig:
    composite_threshold: float = 70.0
    subscore_floor: float = 55.0
    axes: tuple = ("capacity", "steel_intensity", "power_intensity", "constructability")
    note: str = ("calibration is provisional: piecewise-linear anchors should be fitted to "
                 "real ships of this type before the gate is used to reject a design")


def plscore(value: float, anchors: list[tuple[float, float]], higher_is_better: bool = True):
    """Piecewise-linear score from (value, score) anchors, clamped to [0, 100]."""
    pts = sorted(anchors, key=lambda a: a[0]) if higher_is_better else \
        sorted(anchors, key=lambda a: -a[0])
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return float(np.clip(np.interp(value, xs, ys), 0.0, 100.0))


def steel_takeoff(p, lightship_t: float, steel_fraction: float = 0.78,
                  structural_steel_area_m2: float | None = None) -> dict:
    """Hull steel quantity, derived from the weight group, NOT from the midship section.

    Two defects were fixed here, and both are worth recording:

    1. A stray /1000 in the unit chain gave 279 t of hull steel against a 9,062 t lightship.
    2. More fundamentally, the take-off was built by extending the MIDSHIP HULL-GIRDER AREA
       along the length. That conflates a strength quantity with a mass quantity. Cargo holds
       are transversely framed with web frames, the double bottom and the ends have entirely
       different structural density, and the midship section is by construction the most
       heavily structured station on the ship. Extrapolating it over 180 m gives roughly twice
       the real steel weight. The midship area is reported alongside as a consistency check,
       never as the basis of the quantity.

    Basis: lightship weight group x steel fraction, which is how a class-5 estimate is
    actually done at this stage.
    """
    rho_steel = 7.85                                     # t/m3, VERIFIED
    if lightship_t <= 0 or not (0.55 <= steel_fraction <= 0.95):
        raise ValueError(f"implausible inputs: lightship {lightship_t} t, "
                         f"steel fraction {steel_fraction}")
    hull_steel_t = lightship_t * steel_fraction
    outfitting_t = lightship_t * (1.0 - steel_fraction) * 0.62   # ESTIMATE split
    machinery_t = lightship_t * (1.0 - steel_fraction) * 0.38
    # tonnes / (t/m3 * m) = m2. A stray *1000 here turned 5.0 m2 into 5,002 m2 and was
    # caught by the range gate below, not by reading the number.
    mean_area_m2 = hull_steel_t / (rho_steel * p.lpp)
    out = {
        "hull_steel_t": hull_steel_t,
        "outfitting_t": outfitting_t,
        "machinery_t": machinery_t,
        "lightship_t": lightship_t,
        "steel_fraction_of_lightship": steel_fraction,
        "steel_density_t_m3": rho_steel,
        "implied_mean_structural_area_m2": mean_area_m2,
        "midship_girder_area_m2": structural_steel_area_m2,
        "midship_to_mean_ratio": (structural_steel_area_m2 / mean_area_m2
                                  if structural_steel_area_m2 else None),
        "provenance": {"steel_fraction": "ESTIMATE (bulk carriers 0.72-0.82)",
                       "outfitting_split": "ESTIMATE"},
        "accuracy": "class 5 order-of-magnitude; +/-20% until calibrated on a parent ship",
        "action_required": "calibrate the steel fraction against a built sister ship before "
                           "quoting cost, and build the quantity from a real structural model "
                           "at contract design",
    }
    # plausibility gates: both the fraction and the implied mean area
    if not (2.0 <= mean_area_m2 <= 12.0):
        raise AssertionError(
            f"implied mean structural area {mean_area_m2:.2f} m2 over Lpp is outside 2-12 m2 "
            f"for a merchant hull of this size; steel {hull_steel_t:,.0f} t, Lpp {p.lpp} m"
        )
    if structural_steel_area_m2:
        ratio = out["midship_to_mean_ratio"]
        if not (0.8 <= ratio <= 3.0):
            raise AssertionError(
                f"midship girder area is {ratio:.2f}x the implied mean structural area; "
                "expected roughly 1.0-2.0x. One of the two quantities is wrong."
            )
    return out


@dataclass
class Candidate:
    tag: str
    params: H.HullParams
    metrics: dict
    displacement_t: float
    dwt_t: float
    lightship_t: float
    mcr_kw: float
    speed_kn: float
    hull_steel_t: float
    scores: dict
    composite: float
    passed: bool
    reasons: list


def build_candidates(base: H.HullParams, lightship_base_t: float, dwt_target_t: float,
                     speed_kn: float, cfg: ReviewerConfig = ReviewerConfig(),
                     structural_area_m2: float = 4.0):
    """Three structurally different candidates, not three perturbations of one idea.

    A single-point design is design fixation. These vary the LONGITUDINAL DISTRIBUTION, which
    changes the run, the entrance and the parallel-middle-body length together -- the axis
    that actually trades resistance against capacity and build cost.
    """
    variants = [
        ("A-baseline", dict(run_frac=0.220, ent_frac=0.180)),
        ("B-long-pmb", dict(run_frac=0.245, ent_frac=0.205)),
        ("C-full-ends", dict(run_frac=0.190, ent_frac=0.160)),
    ]
    out = []
    for tag, deltas in variants:
        p0 = replace(base, **deltas)
        try:
            p, cb = H.solve_for_cb(p0)
        except H.HullGenerationError as exc:
            out.append(Candidate(tag, p0, {"error": str(exc)}, float("nan"), float("nan"),
                                 float("nan"), float("nan"), speed_kn, float("nan"),
                                 {}, float("nan"), False,
                                 [f"candidate not realisable: {exc}"]))
            continue
        cm = H.midship_coeff(p)
        cp = cb / cm
        vol_design = H.displaced_volume(p)
        disp_design = vol_design * 1.025
        am = H.midship_area(p)
        # Lightship scaled from the baseline by the midship section area (a proxy for hull
        # steel) with a correction for the total length of shaped ends, which carry more
        # structure per metre than the parallel middle body. Both factors are ESTIMATE-class.
        lightship = (lightship_base_t * (am / H.midship_area(base)) ** 0.5
                     * (1.0 + 0.10 * ((p.run_frac + p.ent_frac)
                                      - (base.run_frac + base.ent_frac))))
        st = steel_takeoff(p, lightship, steel_fraction=0.78,
                           structural_steel_area_m2=structural_area_m2
                           * am / H.midship_area(base))
        dwt = disp_design - lightship
        cargo = min(dwt_target_t, dwt * 0.94)
        # powering proxy: wetted surface and Cp drive it at low Fn
        ldisp = p.lpp / vol_design ** (1.0 / 3.0)
        ws = (1.025 * vol_design) ** 0.6667 * p.lpp ** 0.5 * 3.4   # crude, tagged below
        mcr = 4361.0 * (ws / 8071.0) * (cp / 0.8794) ** 2.0
        scores = {
            "capacity": plscore(100.0 * cargo / dwt_target_t,
                                [(85.0, 20.0), (95.0, 60.0), (100.0, 90.0), (105.0, 100.0)]),
            "steel_intensity": plscore(1000.0 * lightship / max(dwt, 1.0),
                                       [(280.0, 20.0), (240.0, 60.0), (215.0, 85.0),
                                        (195.0, 100.0)], higher_is_better=False),
            "power_intensity": plscore(mcr / max(dwt, 1.0) * 1000.0,
                                       [(160.0, 20.0), (130.0, 60.0), (115.0, 85.0),
                                        (100.0, 100.0)], higher_is_better=False),
            "constructability": plscore(cp, [(0.90, 40.0), (0.87, 75.0), (0.84, 90.0),
                                            (0.80, 70.0)]),
        }
        not_scored = ["fatigue_life", "constructability_from_yard_limits"]
        composite = float(np.mean(list(scores.values())))
        reasons = [f"{k} = {v:.1f}" for k, v in scores.items()]
        below = [k for k, v in scores.items() if v < cfg.subscore_floor]
        if below:
            reasons.append(f"sub-score floor breached by {below}")
        passed = bool(composite >= cfg.composite_threshold and not below)
        out.append(Candidate(tag, p, {"Cb": cb, "Cm": cm, "Cp": cp,
                                      "LCB_pct": 100.0 * H.lcb(p) / p.lpp,
                                      "displaced_volume_m3": vol_design,
                                      "wetted_surface_proxy_m2": ws,
                                      "length_displacement_ratio": ldisp,
                                      "not_scored_axes": not_scored},
                             disp_design, dwt, lightship, mcr, speed_kn,
                             st["hull_steel_t"], scores, composite, passed, reasons))
    return out


def select(cands: list[Candidate], cfg: ReviewerConfig = ReviewerConfig()) -> dict:
    real = [c for c in cands if math.isfinite(c.composite)]
    if not real:
        return {"selected": None, "reason": "no candidate was realisable",
                "candidates": [_as_dict(c) for c in cands], "config": cfg.__dict__}
    best = max(real, key=lambda c: c.composite)
    return {
        "selected": best.tag if best.passed else None,
        "best_composite": best.composite,
        "gate_passed": best.passed,
        "threshold": cfg.composite_threshold, "subscore_floor": cfg.subscore_floor,
        "reason": ("selected: clears the composite threshold with every sub-score above its "
                   "floor" if best.passed else
                   f"NO candidate clears the gate; best is {best.tag} at "
                   f"{best.composite:.1f} ({'; '.join(best.reasons)}). Iterate the design "
                   "space rather than relaxing the gate."),
        "why_the_losers_lost": [
            {"tag": c.tag, "composite": round(c.composite, 2),
             "deficit_vs_best": round(best.composite - c.composite, 2),
             "worst_axis": min(c.scores.items(), key=lambda kv: kv[1])[0] if c.scores else None,
             "worst_score": round(min(c.scores.values()), 1) if c.scores else None}
            for c in real if c is not best
        ],
        "candidates": [_as_dict(c) for c in cands],
        "config": cfg.__dict__,
        "caveat": ("capacity, steel intensity and power intensity use proxy measures "
                   "(section-area scaling and a crude wetted-surface estimate); fatigue life "
                   "and yard-limit constructability are NOT SCORED. The ranking is "
                   "directional until those are real computations."),
    }


def _as_dict(c: Candidate) -> dict:
    return {"tag": c.tag, "composite": round(c.composite, 2), "passed": c.passed,
            "scores": {k: round(v, 2) for k, v in c.scores.items()},
            "principal": {"Lpp": c.params.lpp, "B": c.params.breadth,
                          "T": c.params.draft, "run_frac": c.params.run_frac,
                          "ent_frac": c.params.ent_frac,
                          "fullness_exponent": round(c.params.fullness_exponent, 4)},
            "metrics": {k: (round(v, 4) if isinstance(v, float) else v)
                        for k, v in c.metrics.items()},
            "displacement_t": round(c.displacement_t, 1), "dwt_t": round(c.dwt_t, 1),
            "lightship_t": round(c.lightship_t, 1), "MCR_kW": round(c.mcr_kw, 1),
            "hull_steel_t": round(c.hull_steel_t, 1), "reasons": c.reasons}

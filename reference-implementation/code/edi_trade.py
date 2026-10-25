"""
EEDI Phase 3 trade study: speed x DWT x energy-saving measures x fuel.

Why this exists
---------------
The reference case FAILS EEDI Phase 3: attained 6.34 against required 4.38 gCO2/(t.nm), a
-44.8% margin. Reporting "FAIL" is not engineering. The owner needs to know which combination
of speed, size and technology closes the gap, what each costs, and how confident the answer is.

Honesty rules this module follows
---------------------------------
1. Every constant is tagged VERIFIED / STANDARD / ESTIMATE / NOT-IMPL.
2. Regulatory credit factors (f_w for wind assistance, f_ESD, f_i for ice class) are NOT
   invented. They are modelled as an explicit parameter with a range, and the record states
   that the credit must be established under the IMO ESD credit framework with model test or
   CFD evidence and accepted by the Administration.
3. Fuel conversion factors are given for the fuels whose factors are unambiguous in
   MEPC.215(63). For methanol, ammonia and hydrogen the factors must be read from the
   amended guidelines -- see FUEL and the `provenance` field.
4. The dominant uncertainty (the power exponent n in P ~ V^n) is carried explicitly: every
   recommendation is re-evaluated across a range of n, and a recommendation that only holds
   for one value of n is flagged as fragile.
"""
from __future__ import annotations

import itertools
import json
import math
import os
from dataclasses import dataclass, asdict

import numpy as np

# --------------------------------------------------------------------------- #
# constants
# --------------------------------------------------------------------------- #
# IMO MEPC.215(63) fuel conversion factors, gCO2/g fuel
FUEL = {
    "HFO":     {"cf": 3.206, "sfc_g_kWh": 165.0, "provenance": "STANDARD (MEPC.215(63))"},
    "MDO":     {"cf": 3.206, "sfc_g_kWh": 175.0, "provenance": "STANDARD (MEPC.215(63))"},
    "MGO":     {"cf": 3.206, "sfc_g_kWh": 175.0, "provenance": "STANDARD (MEPC.215(63))"},
    "LNG":     {"cf": 2.750, "sfc_g_kWh": 136.6, "provenance": "STANDARD (MEPC.215(63)); "
                                                               "methane slip is NOT accounted "
                                                               "for by EEDI and is a real "
                                                               "GHG penalty -- see caveats"},
    # The factors below are NOT stated from memory. MEPC.245(66) and later amendments
    # introduce C_f values for methanol, ethanol, ammonia and hydrogen, and ammonia additionally
    # raises NOx and toxicity questions that change the whole rule path.
    "methanol": {"cf": None, "sfc_g_kWh": None,
                 "provenance": "NOT-IMPL: read C_f from the amended guidelines"},
    "ammonia":  {"cf": None, "sfc_g_kWh": None,
                 "provenance": "NOT-IMPL: read C_f from the amended guidelines; NOx and "
                               "toxicity rules apply in addition"},
}

# Reference-line coefficients for bulk carriers, MEPC.215(63)
REFLINE = {"bulk carrier": {"a": 961.0, "c": 0.4778},
           "container ship": {"a": 1984.0, "c": 0.489}}
# Phase reduction factors
PHASE = {1: 0.00, 2: 0.00, 3: 0.30, "2030 target": 0.50}


class FuelDataMissing(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Baseline:
    """The reference case as computed by run_case.py -- not assumed."""
    mcr_kw: float
    speed_kn: float
    dwt_t: float
    displacement_t: float
    lightship_t: float
    cargo_t: float
    draft_m: float
    lpp_m: float
    breadth_m: float


@dataclass(frozen=True)
class SizeVariant:
    """A hull-size variant. Length is the lever; B/T/D held, so the terminal and channel
    constraints from the owner's brief still bind."""
    tag: str
    lpp_scale: float          # >1 lengthens the parallel middle body
    cb: float
    note: str = ""

    def dwt(self, base: Baseline, steel_fraction: float = 0.78) -> dict:
        """DWT and lightship for this variant.

        Lengthening a bulk carrier adds cargo hold length. Steel grows roughly with the
        wetted structural area (length x perimeter), cargo volume grows with length, so the
        lightship/DWT ratio improves -- which is exactly why "make it bigger" is the first
        lever every owner reaches for. The exponents here are ESTIMATE-class and must be
        replaced by a real weight estimate per variant.
        """
        s = self.lpp_scale
        disp = base.displacement_t * s                      # volume scales with length at
        lightship = base.lightship_t * s ** 0.85            # constant B, T, Cb
        dwt = disp - lightship
        cargo = dwt * (base.cargo_t / max(base.dwt_t, 1.0))
        return {"dwt_t": dwt, "lightship_t": lightship, "displacement_t": disp,
                "cargo_t": cargo, "lpp_m": base.lpp_m * s,
                "steel_fraction": steel_fraction,
                "provenance": {"disp_scale": "linear in length (B, T, Cb constant)",
                               "lightship_exponent": "ESTIMATE 0.85 (structural area grows "
                                                    "slower than length)",
                               "cargo_share": "held at the baseline cargo/DWT ratio"}}


def power_required(base: Baseline, speed_kn: float, disp_scale: float,
                   n_exp: float) -> float:
    """Installed MCR for a speed and displacement, kW.

        P2 = P1 * (D2/D1)^(2/3) * (V2/V1)^n

    The (2/3) displacement exponent is the standard low-Froude-number scaling for a
    geometrically similar hull (VERIFIED as a scaling law). The exponent n is NOT 3 exactly:
    at Fn ~ 0.17 the wave-making share is small but not negligible, and the propulsor
    re-matching shifts it. n is therefore carried as a parameter and every recommendation is
    tested across its plausible range.
    """
    if speed_kn <= 0 or disp_scale <= 0:
        raise ValueError("speed and displacement scale must be positive")
    return base.mcr_kw * disp_scale ** (2.0 / 3.0) * (speed_kn / base.speed_kn) ** n_exp


def aux_power(mcr_kw: float) -> float:
    """P_AE per MEPC.215(63) for a bulk carrier: 0.025 * P_ME + 250 kW. STANDARD."""
    return 0.025 * mcr_kw + 250.0


def attained_eedi(mcr_kw: float, speed_kn: float, dwt_t: float, main_fuel: str,
                  aux_fuel: str = "MDO", esd_factor: float = 1.0,
                  whr_saving_frac: float = 0.0, aux_esd_kw: float = 0.0) -> dict:
    """Attained EEDI with explicit, tagged technology factors.

        EEDI = [P_ME C_ME SFC_ME (1 - whr) + (P_AE - aux_esd) C_AE SFC_AE] * f_esd
               / (DWT * 0.75 * V)

    `esd_factor` multiplies the whole numerator. It is a PLACEHOLDER for whatever credit the
    Administration accepts under the ESD framework -- it is not a number this module is
    entitled to choose.
    """
    fm = FUEL[main_fuel]
    fa = FUEL[aux_fuel]
    if fm["cf"] is None:
        raise FuelDataMissing(f"C_f for {main_fuel!r} is not available: {fm['provenance']}")
    if not (0.60 <= esd_factor <= 1.0):
        raise ValueError(f"esd_factor {esd_factor} outside 0.60-1.00; a credit larger than "
                         "40% has no basis in the ESD framework and would not be accepted")
    if not (0.0 <= whr_saving_frac <= 0.25):
        raise ValueError(f"waste-heat-recovery saving {whr_saving_frac} outside 0-25%")
    v_ref = 0.75 * speed_kn
    if v_ref <= 0 or dwt_t <= 0:
        raise ValueError("speed and DWT must be positive")
    p_ae = max(aux_power(mcr_kw) - aux_esd_kw, 0.0)
    num = (mcr_kw * fm["cf"] * fm["sfc_g_kWh"] * (1.0 - whr_saving_frac)
           + p_ae * fa["cf"] * fa["sfc_g_kWh"]) * esd_factor
    return {"attained": num / (dwt_t * v_ref), "P_ME_kW": mcr_kw, "P_AE_kW": p_ae,
            "V_ref_kn": v_ref, "DWT_t": dwt_t, "main_fuel": main_fuel,
            "esd_factor": esd_factor, "whr_saving_frac": whr_saving_frac,
            "aux_esd_kw": aux_esd_kw}


def required_eedi(dwt_t: float, ship_type: str = "bulk carrier", phase=3) -> dict:
    rl = REFLINE[ship_type]
    ref = rl["a"] * dwt_t ** (-rl["c"])
    red = PHASE[phase]
    return {"reference_line": ref, "reduction": red, "required": ref * (1.0 - red),
            "formula": f"{rl['a']} * DWT^(-{rl['c']}) * (1 - {red})",
            "provenance": "STANDARD (MEPC.215(63)); confirm the phase and any amendment in "
                          "force at the contract date"}


# --------------------------------------------------------------------------- #
# feasibility screens -- a compliant ship that cannot trade is not an answer
# --------------------------------------------------------------------------- #
def feasibility(speed_kn: float, variant: dict, base: Baseline, mcr_kw: float,
                fuel: str, esd_factor: float) -> dict:
    """Hard and soft screens. Each returns a reason, not just a boolean."""
    out = {"hard": [], "soft": []}

    if speed_kn < 9.0:
        out["hard"].append(f"service speed {speed_kn} kn is below the practical minimum for a "
                           "bulker trade (~10-11 kn); charterers will not accept it and the "
                           "voyage economics collapse")
    if speed_kn < 11.0:
        out["soft"].append(f"service speed {speed_kn} kn is at the slow-steaming end of the "
                           "bulker market; acceptable on long-haul ore/coal but not on "
                           "time-charter trades")

    # engine minimum load: a 2-stroke slow-speed engine must not be loaded below ~25-30% MCR
    # in continuous service, or it glazes and fouls. If the required power is far below the
    # installed MCR the engine is the wrong engine, not the ship.
    if mcr_kw < 0.25 * base.mcr_kw:
        out["soft"].append(f"MCR {mcr_kw:,.0f} kW is below 25% of the baseline engine; "
                           "select a smaller-bore engine rather than running a large one "
                           "at part load")

    # propeller immersion in the ballast condition: lengthening helps, raising the design
    # draft helps, neither is free
    if variant.get("lpp_scale", 1.0) < 1.0:
        out["soft"].append("shortening the hull reduces ballast-condition propeller immersion "
                           "and bow visibility; check the Load Line and bridge-visibility "
                           "requirements again")

    if fuel == "LNG":
        out["soft"].append("LNG: bunkering availability on the intended trade must be confirmed; "
                           "tank volume roughly doubles for the same energy, which costs cargo "
                           "space; methane slip is NOT credited by EEDI and undermines the "
                           "GHG case at high engine loads")
    if fuel in ("methanol", "ammonia"):
        out["hard"].append(f"{fuel}: the C_f value is not available in this module and the "
                           "rule path is different (ammonia additionally carries NOx and "
                           "toxicity requirements). Cannot be evaluated here.")

    if esd_factor < 0.90:
        out["hard"].append(f"an ESD credit of {1-esd_factor:.0%} requires model-test or CFD "
                           "validation and Administration acceptance under the ESD framework; "
                           "it is not available at concept stage and must not be assumed in a "
                           "contract offer")
    elif esd_factor < 1.0:
        out["soft"].append(f"an ESD credit of {1-esd_factor:.0%} needs validation evidence "
                           "(typically a propeller boss cap fins / rudder bulb combination, "
                           "hull optimisation, or an advanced wake-equalising duct)")
    return out


# --------------------------------------------------------------------------- #
# the trade study
# --------------------------------------------------------------------------- #
def run_trade(base: Baseline, variants: list[SizeVariant],
              speeds=(9.0, 10.0, 11.0, 12.0, 12.5, 13.0, 13.5, 14.0),
              esd_factors=(1.00, 0.97, 0.95, 0.92, 0.90, 0.85),
              fuels=("HFO", "LNG"),
              whr_options=(0.0, 0.05),
              n_exps=(2.6, 2.9, 3.2),
              min_cargo_t: float | None = None,
              power_uncertainty: float = 1.25) -> dict:
    """`power_uncertainty` is the stress factor applied to MCR before an option may be called
    OFFERABLE.

    This is the filter that makes the study usable. The baseline MCR rests on ESTIMATE-class
    wave resistance (declared as 15% +/- 8 points of R_F), an ESTIMATE form factor (1+k = 1.45,
    band 1.30-1.60) and ESTIMATE wake, thrust deduction and propeller efficiency. Those
    together are easily worth 20-25% on installed power. An option whose EEDI margin is thinner
    than that is not a solution, it is a hope -- and 14 kn solutions in this grid have margins
    of +0.5% to +4.1%, i.e. entirely inside the error band.
    """
    """Grid the design space, screen for feasibility, and return the Pareto frontier."""
    rows = []
    for var, v, esd, fuel, whr in itertools.product(variants, speeds, esd_factors, fuels, whr_options):
        sz = var.dwt(base)
        feas = feasibility(v, {"lpp_scale": var.lpp_scale}, base,
                           power_required(base, v, var.lpp_scale, 2.9), fuel, esd)
        if feas["hard"]:
            rows.append({"variant": var.tag, "speed_kn": v, "esd_factor": esd, "fuel": fuel,
                         "whr": whr, "compliant": False, "rejected": feas["hard"]})
            continue
        dwt = sz["dwt_t"]
        req = required_eedi(dwt)
        # evaluate across the whole range of the power exponent
        per_n = {}
        for n in n_exps:
            mcr = power_required(base, v, var.lpp_scale, n)
            att = attained_eedi(mcr, v, dwt, fuel, "MDO", esd, whr)
            per_n[n] = {"mcr_kw": mcr, "attained": att["attained"],
                        "compliant": att["attained"] <= req["required"],
                        "margin_pct": 100.0 * (req["required"] - att["attained"]) / req["required"],
                        "P_AE_kW": att["P_AE_kW"],
                        "fuel_t_per_day": (mcr * FUEL[fuel]["sfc_g_kWh"] * 24 / 1e6
                                           + att["P_AE_kW"] * FUEL["MDO"]["sfc_g_kWh"] * 24 / 1e6)}
        all_ok = all(p["compliant"] for p in per_n.values())
        any_ok = any(p["compliant"] for p in per_n.values())
        # stress test: does it still comply if installed power is 25% higher than estimated?
        stressed_ok = True
        for n in n_exps:
            mcr_s = power_required(base, v, var.lpp_scale, n) * power_uncertainty
            att_s = attained_eedi(mcr_s, v, dwt, fuel, "MDO", esd, whr)
            if att_s["attained"] > req["required"]:
                stressed_ok = False
                break
        mid = per_n[2.9]
        cargo = sz["cargo_t"]
        rows.append({
            "variant": var.tag, "lpp_scale": var.lpp_scale, "speed_kn": v,
            "esd_factor": esd, "fuel": fuel, "whr": whr,
            "dwt_t": dwt, "cargo_t": cargo, "lightship_t": sz["lightship_t"],
            "required_edi": req["required"],
            "compliant_all_n": all_ok, "compliant_any_n": any_ok,
            "robust": all_ok,
            "fragile": (any_ok and not all_ok),
            "offerable": bool(all_ok and stressed_ok),
            "stressed_compliant": stressed_ok,
            "power_uncertainty_factor": power_uncertainty,
            "mcr_kw": mid["mcr_kw"], "attained_edi": mid["attained"],
            "margin_pct": mid["margin_pct"], "fuel_t_per_day": mid["fuel_t_per_day"],
            "per_n": {str(n_): {kk: (round(vv, 4) if isinstance(vv, float) else vv)
                                for kk, vv in p_.items()}
                      for n_, p_ in per_n.items()},
            "soft_flags": feas["soft"],
            "cargo_ok": (cargo >= min_cargo_t) if min_cargo_t else True,
            "annual_cargo_nm_per_year": v * 24 * 330,     # 330 operating days, ESTIMATE
        })
    ok = [r for r in rows if r.get("compliant_all_n") and r.get("cargo_ok")]
    fragile = [r for r in rows if r.get("fragile") and r.get("cargo_ok")]
    return {"rows": rows, "compliant": ok, "fragile": fragile,
            "n_exps": list(n_exps), "n_evaluated": len(rows)}


def pareto(study: dict, base: Baseline, cargo_target_t: float) -> dict:
    """Rank compliant options by what the owner actually trades away.

    Axes:
      * speed given up (kn below the owner's 14 kn) -- schedule and charter revenue
      * cargo given up or gained (t against the target)
      * fuel burn (t/day) -- OPEX
      * technology risk (fuel + ESD credit + WHR) -- schedule and certification risk
    No single "best": report the frontier and the cheapest point on each axis.
    """
    cands = [r for r in study["compliant"] if r.get("offerable")]
    compliant_but_thin = [r for r in study["compliant"] if not r.get("offerable")]
    if not cands:
        return {"frontier": [],
                "reason": "no combination is compliant once installed power is stressed by "
                          "the declared uncertainty",
                "compliant_but_margin_thinner_than_power_uncertainty": len(compliant_but_thin)}

    def risk(r):
        s = 0
        if r["fuel"] == "LNG":
            s += 2
        if r["esd_factor"] < 0.95:
            s += 2
        elif r["esd_factor"] < 1.0:
            s += 1
        if r["whr"] > 0:
            s += 1
        return s

    def key_speed(r):    return (-r["speed_kn"], risk(r), r["fuel_t_per_day"])
    def key_cargo(r):    return (-r["cargo_t"], -r["speed_kn"], risk(r))
    def key_fuel(r):     return (r["fuel_t_per_day"], -r["speed_kn"], risk(r))
    def key_risk(r):     return (risk(r), -r["speed_kn"], -r["cargo_t"])

    picks = {
        "max_speed": min(cands, key=lambda r: (-r["speed_kn"], risk(r))),
        "max_cargo": min(cands, key=key_cargo),
        "min_fuel": min(cands, key=key_fuel),
        "min_technology_risk": min(cands, key=key_risk),
    }
    # Pareto frontier on (speed, cargo, fuel, risk)
    frontier = []
    for r in cands:
        dominated = any(
            (o["speed_kn"] >= r["speed_kn"] and o["cargo_t"] >= r["cargo_t"]
             and o["fuel_t_per_day"] <= r["fuel_t_per_day"] and risk(o) <= risk(r))
            and (o["speed_kn"] > r["speed_kn"] or o["cargo_t"] > r["cargo_t"]
                 or o["fuel_t_per_day"] < r["fuel_t_per_day"] or risk(o) < risk(r))
            for o in cands if o is not r)
        if not dominated:
            frontier.append(r)
    frontier.sort(key=lambda r: (-r["speed_kn"], -r["cargo_t"]))

    def slim(r):
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()
                if k not in ("per_n", "soft_flags", "rejected")} | {"risk": risk(r),
                                                                    "soft_flags": r["soft_flags"]}

    return {"frontier": [slim(r) for r in frontier],
            "picks": {k: slim(v) for k, v in picks.items()},
            "n_offerable": len(cands),
            "n_compliant_total": len(study["compliant"]),
            "n_compliant_but_thin": len(compliant_but_thin),
            "thin_examples": [{"variant": r["variant"], "speed_kn": r["speed_kn"],
                               "fuel": r["fuel"], "esd_factor": r["esd_factor"],
                               "whr": r["whr"], "margin_pct": round(r["margin_pct"], 2),
                               "dwt_t": round(r["dwt_t"], 0)}
                              for r in sorted(compliant_but_thin,
                                              key=lambda x: -x["speed_kn"])[:10]],
            "n_fragile": len(study["fragile"]),
            "cargo_target_t": cargo_target_t,
            "power_uncertainty_factor": study["compliant"][0]["power_uncertainty_factor"]
            if study["compliant"] else None}


def risk_tier_table(study: dict, base: Baseline) -> list[dict]:
    """For each technology risk tier, the fastest OFFERABLE option and what it costs.

    This is the table an owner can actually decide from. A Pareto frontier of 40 points where
    the fastest ones all carry the highest technology risk is not a recommendation; the
    question is always "what is the fastest I can go WITHOUT betting the schedule on an
    unvalidated ESD credit or on LNG bunkering at every port?"
    """
    def risk(r):
        s_ = 0
        if r["fuel"] == "LNG":
            s_ += 2
        if r["esd_factor"] < 0.95:
            s_ += 2
        elif r["esd_factor"] < 1.0:
            s_ += 1
        if r["whr"] > 0:
            s_ += 1
        return s_

    tiers = {
        0: "conventional: HFO/LFO, no credit, no WHR -- certifiable today",
        1: "one modest measure: HFO + a small validated ESD credit",
        2: "LNG fuel, or a larger ESD credit",
        3: "LNG plus an ESD credit",
        4: "LNG plus ESD plus waste-heat recovery",
        5: "all three, with the ESD credit at the aggressive end",
    }
    rows = []
    pool = [r for r in study["compliant"] if r.get("offerable")]
    for tier in sorted(tiers):
        cands = [r for r in pool if risk(r) == tier]
        if not cands:
            rows.append({"risk": tier, "description": tiers[tier], "available": False})
            continue
        fastest = max(cands, key=lambda r: (r["speed_kn"], r["cargo_t"]))
        most_cargo = max(cands, key=lambda r: (r["cargo_t"], r["speed_kn"]))
        rows.append({
            "risk": tier, "description": tiers[tier], "available": True,
            "n_options": len(cands),
            "fastest_speed_kn": fastest["speed_kn"],
            "fastest_variant": fastest["variant"],
            "fastest_cargo_t": round(fastest["cargo_t"], 0),
            "fastest_fuel_t_day": round(fastest["fuel_t_per_day"], 2),
            "fastest_mcr_kw": round(fastest["mcr_kw"], 0),
            "fastest_margin_pct": round(fastest["margin_pct"], 1),
            "fastest_config": f"{fastest['fuel']}, esd={fastest['esd_factor']:.2f}, "
                              f"whr={fastest['whr']:.2f}",
            "max_cargo_t": round(most_cargo["cargo_t"], 0),
            "max_cargo_speed_kn": most_cargo["speed_kn"],
            "max_cargo_variant": most_cargo["variant"],
            "speed_lost_vs_brief_kn": round(base.speed_kn - fastest["speed_kn"], 1),
        })
    return rows


def stress_sweep(base: Baseline, variants: list[SizeVariant], cargo_target_t: float,
                 factors=(1.00, 1.25, 1.50, 1.75, 2.00)) -> list[dict]:
    """How the offerable speed ceiling moves with the assumed error in installed power.

    This is the most decision-relevant sensitivity in the whole study, because the baseline
    MCR rests on ESTIMATE-class wave resistance, form factor, wake, thrust deduction and
    propeller efficiency. If the true installed power is 75% above the estimate, every
    recommendation in the grid moves, and the owner should know that before choosing a speed.
    """
    out = []
    for fac in factors:
        st = run_trade(base, variants, min_cargo_t=cargo_target_t, power_uncertainty=fac)
        pool = [r for r in st["compliant"] if r.get("offerable")]

        def risk(r):
            s_ = 0
            if r["fuel"] == "LNG":
                s_ += 2
            if r["esd_factor"] < 0.95:
                s_ += 2
            elif r["esd_factor"] < 1.0:
                s_ += 1
            if r["whr"] > 0:
                s_ += 1
            return s_

        tier0 = [r for r in pool if risk(r) == 0]
        anyrisk = pool
        out.append({
            "power_stress_factor": fac,
            "n_compliant": len(st["compliant"]),
            "n_offerable": len(pool),
            "offerable_ceiling_kn": max((r["speed_kn"] for r in anyrisk), default=None),
            "conventional_hfo_ceiling_kn": max((r["speed_kn"] for r in tier0), default=None),
            "conventional_best_cargo_t": round(
                max((r["cargo_t"] for r in tier0
                     if r["speed_kn"] == max((x["speed_kn"] for x in tier0), default=-1)),
                    default=0), 0),
            "note": ("ceiling is the fastest speed that still complies when installed power "
                     "is multiplied by the stress factor"),
        })
    return out


def sensitivity(study: dict) -> dict:
    """How much does the answer depend on the power exponent n?

    This is the single most influential uncertainty in the whole study, because attained EEDI
    scales with V^(n-1). A recommendation that is only compliant at n = 2.6 must not be
    offered to an owner as a solution.
    """
    frag = [r for r in study["rows"] if r.get("fragile")]
    out = {"n_exps": study["n_exps"], "n_fragile_options": len(frag),
           "fragile_examples": []}
    for r in frag[:8]:
        out["fragile_examples"].append({
            "variant": r["variant"], "speed_kn": r["speed_kn"], "fuel": r["fuel"],
            "esd_factor": r["esd_factor"],
            "compliant_at": [n for n, p in r["per_n"].items() if p["compliant"]],
            "attained_range": [round(min(p["attained"] for p in r["per_n"].values()), 3),
                               round(max(p["attained"] for p in r["per_n"].values()), 3)],
            "required": round(r["required_edi"], 3)})
    robust = [r for r in study["compliant"]]
    offerable = [r for r in robust if r.get("offerable")]
    if robust:
        out["robust_speed_ceiling_kn"] = max(r["speed_kn"] for r in robust)
        out["robust_note"] = (f"{len(robust)} grid points are compliant across the whole "
                              f"n range {study['n_exps']}; the fastest is "
                              f"{out['robust_speed_ceiling_kn']} kn")
    if offerable:
        out["offerable_speed_ceiling_kn"] = max(r["speed_kn"] for r in offerable)
        out["offerable_note"] = (
            f"only {len(offerable)} of {len(robust)} compliant points survive a "
            f"{study['compliant'][0]['power_uncertainty_factor']:.2f}x stress on installed "
            f"power. The fastest OFFERABLE speed is {out['offerable_speed_ceiling_kn']} kn -- "
            f"anything faster is compliant only on an unverified power estimate."
        )
    out["n_offerable"] = len(offerable)
    return out


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    ref = os.path.normpath(os.path.join(here, "..", "reference-case"))
    with open(f"{ref}/design_record.json") as f:
        rec = json.load(f)
    pw = rec["powering"]
    dep = rec["stability"]["conditions"]["departure_full_cargo"]
    base = Baseline(mcr_kw=pw["installed_MCR_kW"], speed_kn=rec["brief"]["service_speed_kn"],
                    dwt_t=pw["DWT_t"], displacement_t=dep["displacement_t"],
                    lightship_t=pw["lightship_t"], cargo_t=pw["cargo_t"],
                    draft_m=rec["stability"]["equilibrium_draft_m"],
                    lpp_m=rec["hull"]["Lpp_m"], breadth_m=rec["hull"]["B_m"])
    variants = [
        SizeVariant("S0-as-is", 1.00, 0.845, "the reference hull"),
        SizeVariant("S1-stretch-5pct", 1.05, 0.845, "Lpp 189 m; check the berth and canal limits"),
        SizeVariant("S2-stretch-10pct", 1.10, 0.845, "Lpp 198 m; LOA ~209 m"),
        SizeVariant("S3-stretch-15pct", 1.15, 0.845, "Lpp 207 m; a different ship size class"),
    ]
    study = run_trade(base, variants, min_cargo_t=rec["brief"]["cargo_capacity_target_t"])
    par = pareto(study, base, rec["brief"]["cargo_capacity_target_t"])
    sens = sensitivity(study)
    tiers = risk_tier_table(study, base)
    sweep = stress_sweep(base, variants, rec["brief"]["cargo_capacity_target_t"])

    print(f"baseline: MCR {base.mcr_kw:,.0f} kW @ {base.speed_kn} kn, DWT {base.dwt_t:,.0f} t, "
          f"cargo {base.cargo_t:,.0f} t")
    print(f"grid evaluated: {study['n_evaluated']} combinations")
    print(f"robustly compliant: {len(study['compliant'])}   fragile: {len(study['fragile'])}")
    print(f"\nrobust speed ceiling: {sens.get('robust_speed_ceiling_kn')} kn")
    print("\nPareto picks:")
    for k, v in par["picks"].items():
        print(f"  {k:24s} variant={v['variant']:16s} speed={v['speed_kn']:5.1f} kn  "
              f"cargo={v['cargo_t']:8,.0f} t  fuel={v['fuel_t_per_day']:5.2f} t/day  "
              f"fuel_type={v['fuel']:4s} esd={v['esd_factor']:.2f} whr={v['whr']:.2f} "
              f"risk={v['risk']}  attained={v['attained_edi']:.3f} vs "
              f"required={v['required_edi']:.3f}")
    print("\nFASTEST OFFERABLE SPEED BY TECHNOLOGY RISK TIER")
    print(f"  {'risk':>4} {'speed':>6} {'variant':17s} {'cargo t':>8} {'fuel t/d':>9} "
          f"{'margin':>7}  config")
    for t in tiers:
        if not t["available"]:
            print(f"  {t['risk']:>4} {'--':>6} {t['description'][:60]}")
            continue
        print(f"  {t['risk']:>4} {t['fastest_speed_kn']:5.1f}  {t['fastest_variant']:17s} "
              f"{t['fastest_cargo_t']:8,.0f} {t['fastest_fuel_t_day']:9.2f} "
              f"{t['fastest_margin_pct']:+6.1f}%  {t['fastest_config']}")
    print(f"\n  offerable speed ceiling: {sens.get('offerable_speed_ceiling_kn')} kn "
          f"({sens.get('n_offerable')} of {len(study['compliant'])} compliant points survive "
          f"the {base and 1.25:.2f}x power stress)")
    print("\nSENSITIVITY OF THE OFFERABLE CEILING TO INSTALLED-POWER ERROR")
    print(f"  {'stress':>7} {'compliant':>10} {'offerable':>10} {'ceiling kn':>11} "
          f"{'HFO-only kn':>12}")
    for sw in sweep:
        print(f"  {sw['power_stress_factor']:7.2f} {sw['n_compliant']:10d} "
              f"{sw['n_offerable']:10d} {str(sw['offerable_ceiling_kn']):>11} "
              f"{str(sw['conventional_hfo_ceiling_kn']):>12}")
    print(f"\nPareto frontier size: {len(par['frontier'])}")
    for r in par["frontier"][:12]:
        print(f"  {r['variant']:16s} {r['speed_kn']:5.1f} kn  cargo {r['cargo_t']:8,.0f} t  "
              f"fuel {r['fuel_t_per_day']:5.2f} t/day  {r['fuel']:4s} esd={r['esd_factor']:.2f} "
              f"whr={r['whr']:.2f} risk={r['risk']} margin={r['margin_pct']:+.1f}%")

    out = {"baseline": asdict(base), "variants": [asdict(v) for v in variants],
           "pareto": par, "sensitivity": sens,
           "risk_tiers": tiers,
           "power_stress_sweep": sweep,
           "compliant_count": len(study["compliant"]),
           "grid_size": study["n_evaluated"],
           "compliant_all": [{k: (round(v, 4) if isinstance(v, float) else v)
                              for k, v in r.items() if k != "per_n"}
                             for r in study["compliant"]],
           "caveats": [
               "the power exponent n is the dominant uncertainty; only options compliant "
               "across the full n range 2.6-3.2 are reported as robust",
               "ESD credit factors are parameters, not entitlements; each must be validated "
               "under the IMO ESD framework and accepted by the Administration",
               "LNG methane slip is not accounted for by EEDI and is a genuine GHG penalty",
               "lightship scaling exponent 0.85 is ESTIMATE-class; a real weight estimate per "
               "variant is required before any of these become an offer",
               "installed MCR must also satisfy the sea-trial speed at the trial displacement "
               "and draft, which is a different condition from the EEDI V_ref point",
               "EEXI and CII are separate obligations and are NOT checked here",
               "options are called OFFERABLE only if they still comply when installed power "
               "is stressed by 1.25x, because the baseline MCR rests on ESTIMATE-class wave "
               "resistance, form factor and propulsor efficiency; 14 kn solutions in this "
               "grid have margins of +0.5% to +4.1%, i.e. entirely inside that error band",
           ]}
    with open(f"{ref}/edi_trade_study.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nwrote {ref}/edi_trade_study.json")

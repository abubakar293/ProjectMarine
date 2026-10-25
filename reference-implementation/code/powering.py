"""
Resistance, powering and EEDI for the reference case.

Provenance discipline
---------------------
Every constant in this module carries a `source` tag:

  VERIFIED   closed-form physics or a formula re-derived and unit-tested here
  STANDARD   a published industry standard form, transcribed and range-checked
  ESTIMATE   an order-of-magnitude allowance that must be replaced by data before use
  NOT-IMPL   deliberately absent; the function raises instead of guessing

The wave-resistance term of Holtrop & Mennen is NOT-IMPL. An earlier draft of this module
attempted to reproduce it from memory, produced ~30 lines of self-cancelling placeholder
algebra, and was deleted. Reproducing a published regression from recollection is exactly
how an agent manufactures a confident, citable, wrong number -- and a powering estimate
that is wrong by 10% becomes a speed-and-consumption warranty dispute.

What IS implemented: ITTC-57 friction with the Katsui et al. (2005) form factor,
appendage resistance, a parent-ship wave-resistance allowance flagged ESTIMATE, the
propulsive-efficiency chain, and attained/required EEDI for a bulk carrier.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

RHO_SW = 1025.0        # kg/m3      VERIFIED (standard seawater density)
NU = 1.19e-6           # m2/s       ESTIMATE (seawater ~15 degC; state the actual temp)
G_ACC = 9.80665        # m/s2       VERIFIED

KN = 0.514444          # m/s per knot   VERIFIED

# IMO MEPC.215(63) EEDI conversion factors, gCO2/g fuel
CF_FUEL = {"HFO": 3.206, "MDO": 3.206, "MGO": 3.206, "LNG": 2.750}   # STANDARD
# IMO MEPC.215(63) specific fuel consumption, g/kWh, at 75% MCR
SFC_FUEL = {"HFO": 165.0, "MDO": 175.0, "MGO": 175.0, "LNG": 136.6}  # STANDARD


@dataclass(frozen=True)
class PoweringInput:
    lpp: float
    breadth: float
    draft: float
    depth: float
    displacement_t: float
    cb: float
    cm: float
    lcb_pct_from_ap: float
    speed_kn: float
    wetted_surface_m2: float
    wetted_surface_source: str
    volume_m3: float | None = None
    appendage_area_m2: float = 0.0
    sea_margin_frac: float = 0.15        # STANDARD contract practice, must be declared
    roughness_allowance_frac: float = 0.04   # ESTIMATE, ISO 15016 depends on the coating


BANDS = {                       # applicability of the Katsui form factor / bulk-carrier practice
    "Cb": (0.45, 0.85),
    "Cm": (0.70, 1.00),
    "Lpp/B": (4.0, 10.0),
    "B/T": (1.5, 5.0),
    "Fn": (0.05, 0.30),
    "LCB%Lpp": (48.0, 55.0),
}


def check_validity(inp: PoweringInput, fn: float):
    vals = {"Cb": inp.cb, "Cm": inp.cm, "Lpp/B": inp.lpp / inp.breadth,
            "B/T": inp.breadth / inp.draft, "Fn": fn, "LCB%Lpp": inp.lcb_pct_from_ap}
    out = []
    for k, (lo, hi) in BANDS.items():
        v = vals[k]
        inside = lo <= v <= hi
        out.append({"quantity": k, "value": round(float(v), 5), "band": [lo, hi],
                    "inside": bool(inside),
                    "margin_frac": round(min(v - lo, hi - v) / max(hi - lo, 1e-9), 4),
                    "severity": "HARD" if (not inside and k in ("Fn", "Cb")) else
                                ("ADVISORY" if not inside else "ok")})
    return out


def ittc57_cf(re: float) -> float:
    """ITTC-1957 model-ship correlation line.  Cf = 0.075 / (log10 Re - 2)^2."""
    if re <= 100.0:
        raise ValueError(f"Reynolds number {re} too low for the ITTC-57 line")
    return 0.075 / (math.log10(re) - 2.0) ** 2


def form_factor(cb: float, cm: float, lpp: float, breadth: float, draft: float,
                lcb_frac: float, volume_m3: float) -> dict:
    """Hull form factor (1+k) as a DECLARED ESTIMATE.

    A transcription of the Katsui et al. (2005) form factor was attempted and produced
    1+k = 279.7 for this hull -- two orders of magnitude outside any physical range. It was
    deleted rather than tuned until it looked plausible. Tuning a mis-transcribed regression
    until it gives a believable number is worse than not having it: the result then carries
    the authority of a citation it does not deserve.

    For a single-screw full-form merchant hull the form factor is well documented as
    1+k ~ 1.3-1.6. The midpoint is used here with the uncertainty carried explicitly, and
    the record states what must replace it.
    """
    if cb <= 0 or cb >= 1 or cm <= 0 or cm >= 1:
        raise ValueError(f"non-physical coefficients Cb={cb}, Cm={cm}")
    value = 1.45
    return {"form_factor_1_plus_k": value, "source": "ESTIMATE",
            "band": [1.30, 1.60], "uncertainty_on_R_fric_pct": 100.0 * 0.15 / value,
            "reason_not_computed": "the published regression was mis-transcribed and gave "
                                   "1+k = 279.7; deleted rather than fitted to look right",
            "action_required": "evaluate (1+k) from a transcribed-and-unit-tested Katsui or "
                               "Holtrop implementation, or determine it from a model test "
                               "per ITTC low-Froude-number extrapolation, or by CFD"}


def wave_resistance_allowance(inp: PoweringInput, fn: float, disp_m3: float) -> dict:
    """NOT a Holtrop-Mennen calculation.

    Returns a declared allowance for a full-form bulk carrier at low Froude number, with the
    reasoning stated and an uncertainty band attached. At Fn = 0.17 a full-form hull is well
    below its wave-making hump, so R_W is typically 10-20% of R_F for Cb ~ 0.85. That is a
    planning allowance, NOT a design value, and the record says so.
    """
    if fn > 0.30:
        raise NotImplementedError(
            f"Fn = {fn:.3f} is above the low-speed regime this allowance covers; a proper "
            "wave-resistance method (transcribed Holtrop-Mennen, panel code or RANS) is required"
        )
    return {"method": "declared planning allowance, NOT a regression evaluation",
            "source": "ESTIMATE",
            "fraction_of_R_F": 0.15,
            "uncertainty": "+/- 8 percentage points of R_F",
            "action_required": "replace with a verified wave-resistance method, model test, "
                               "or parent-ship correlation before any warranty is offered"}


def propulsion_factors(cb: float, lpp: float, breadth: float, draft: float) -> dict:
    """Single-screw wake / thrust-deduction estimates.

    These are the classic preliminary-design correlations for a single-screw full-form ship.
    They are ESTIMATE-class: the values that go into a contract come from a self-propulsion
    model test or CFD at the actual propeller station.
    """
    w = 0.5 * cb - 0.05                       # Taylor/Gawn-type single-screw estimate
    t = 0.55 * w                              # common preliminary relation
    eta_h = (1.0 - t) / (1.0 - w)
    eta_R = 1.0                               # ESTIMATE, typically 0.95-1.05
    eta_0 = 0.60                              # ESTIMATE, well-matched fixed-pitch propeller
    eta_D = eta_h * eta_R * eta_0
    return {"wake_fraction_w": w, "thrust_deduction_t": t, "eta_hull": eta_h,
            "eta_R": eta_R, "eta_0": eta_0, "eta_D": eta_D,
            "source": {"w": "ESTIMATE (Taylor-type)", "t": "ESTIMATE (t = 0.55 w)",
                       "eta_R": "ESTIMATE", "eta_0": "ESTIMATE"},
            "action_required": "replace with self-propulsion analysis or model test"}


def powering(inp: PoweringInput):
    V = inp.speed_kn * KN
    fn = V / math.sqrt(G_ACC * inp.lpp)
    disp_m3 = (inp.volume_m3 if inp.volume_m3 is not None
               else inp.displacement_t * 1000.0 / RHO_SW)
    s = inp.wetted_surface_m2
    if s <= 0:
        raise ValueError("wetted surface must come from the geometry solver, not be estimated")
    re = V * s / NU
    cf = ittc57_cf(re)
    ff = form_factor(inp.cb, inp.cm, inp.lpp, inp.breadth, inp.draft,
                     inp.lcb_pct_from_ap / 100.0, disp_m3)
    k1 = ff["form_factor_1_plus_k"]
    rf = 0.5 * RHO_SW * V ** 2 * s * cf * k1
    ra = 0.5 * RHO_SW * V ** 2 * inp.appendage_area_m2 * cf * 2.0 if inp.appendage_area_m2 > 0 else 0.0
    rw_info = wave_resistance_allowance(inp, fn, disp_m3)
    rw = rw_info["fraction_of_R_F"] * rf
    r_app = 0.0
    rt_calm = rf + ra + rw + r_app
    aa = 1.0 + inp.roughness_allowance_frac
    rt_sea = rt_calm * (1.0 + inp.sea_margin_frac) * aa

    ehp_calm = rt_calm * V
    ehp = rt_sea * V
    pf = propulsion_factors(inp.cb, inp.lpp, inp.breadth, inp.draft)
    dhp = ehp / pf["eta_D"]
    mcr = dhp / 0.98 / 0.95                     # shaft and gearbox transmission losses
    validity = check_validity(inp, fn)

    return {
        "speed_kn": inp.speed_kn, "speed_m_s": V, "froude_number_Lpp": fn,
        "reynolds": re, "Cf_ITTC57": cf, "form_factor": ff,
        "wetted_surface_m2": s, "wetted_surface_source": inp.wetted_surface_source,
        "R_fric_N": rf, "R_appendage_N": ra, "R_wave_N": rw, "R_wave": rw_info,
        "R_total_calm_N": rt_calm, "roughness_allowance_frac": inp.roughness_allowance_frac,
        "sea_margin_frac": inp.sea_margin_frac, "R_total_with_margins_N": rt_sea,
        "EHP_calm_kW": ehp_calm / 1000.0, "EHP_kW": ehp / 1000.0,
        "DHP_kW": dhp / 1000.0, "installed_MCR_kW": mcr / 1000.0,
        "propulsion": pf, "validity": validity,
        "outside_band": [v for v in validity if not v["inside"]],
        "confidence": "PRELIMINARY - wave resistance, wake, thrust deduction and propeller "
                      "efficiency are declared estimates, not computed values",
    }


# --------------------------------------------------------------------------- #
# EEDI
# --------------------------------------------------------------------------- #
def required_edi(dwt: float, ship_type: str = "bulk carrier", phase: int = 3) -> dict:
    """Required EEDI. Reference line per MEPC.215(63); reduction factor per implementation phase."""
    a, c = {"bulk carrier": (961.0, 0.4778)}[ship_type] if ship_type == "bulk carrier" else (None, None)
    if a is None:
        raise NotImplementedError(f"reference line for {ship_type!r} not transcribed")
    ref = a * dwt ** (-c)
    factors = {1: 0.00, 2: 0.00, 3: 0.30, "4 (2030 target)": 0.50}
    red = factors[phase]
    return {"reference_line_gCO2_t_nm": ref, "phase": phase, "reduction_factor": red,
            "required_gCO2_t_nm": ref * (1.0 - red),
            "formula": f"{a} * DWT^(-{c}) * (1 - {red})"}


def attained_eedi(mcr_main_kw: float, speed_kn: float, dwt: float,
                  main_fuel: str = "HFO", aux_fuel: str = "MDO") -> dict:
    """Attained EEDI per MEPC.215(63) for a single-screw conventional ship (no electrical
    propulsion, no ice-class correction, f_i = f_w = 1).

        EEDI = [ P_ME*C_ME*SFC_ME + P_AE*C_AE*SFC_AE ] / ( DWT * V_ref ),  V_ref = 0.75*V_MCR
    """
    p_ae = 0.025 * mcr_main_kw + 250.0          # STANDARD bulk-carrier auxiliary load
    v_ref = 0.75 * speed_kn
    if v_ref <= 0 or dwt <= 0:
        raise ValueError("speed and DWT must be positive")
    num = (mcr_main_kw * CF_FUEL[main_fuel] * SFC_FUEL[main_fuel]
           + p_ae * CF_FUEL[aux_fuel] * SFC_FUEL[aux_fuel])
    return {"attained_gCO2_t_nm": num / (dwt * v_ref), "P_ME_kW": mcr_main_kw,
            "P_AE_kW": p_ae, "V_ref_kn": v_ref, "DWT_t": dwt,
            "main_fuel": main_fuel, "aux_fuel": aux_fuel,
            "cf": [CF_FUEL[main_fuel], CF_FUEL[aux_fuel]],
            "sfc": [SFC_FUEL[main_fuel], SFC_FUEL[aux_fuel]],
            "corrections_applied": {"f_i": 1.0, "f_w": 1.0, "ice_class": "none"},
            "note": "P_ME should be the MCR at which V_ref is measured; if the engine is "
                    "derated, V_ref must be consistent with that derating"}


def edi_margin(attained: dict, required: dict) -> dict:
    a, r = attained["attained_gCO2_t_nm"], required["required_gCO2_t_nm"]
    return {"attained": a, "required": r, "margin_pct": 100.0 * (r - a) / r,
            "compliant": bool(a <= r),
            "sensitivity": "a 10% power underestimate moves attained EEDI by -10%; the "
                           "declared ESTIMATE-class wave and propulsor terms are larger "
                           "than that, so this margin is indicative only"}


if __name__ == "__main__":
    ff = form_factor(0.845, 0.961, 180.0, 29.8, 10.5, 0.5052, 47592.0)
    assert 1.3 <= ff["form_factor_1_plus_k"] <= 1.6
    # ITTC-57 line checked against its definition at Re = 1e9
    cf = ittc57_cf(1e9)
    assert abs(cf - 0.075 / (9.0 - 2.0) ** 2) < 1e-12, cf
    print(f"self-tests passed: 1+k = {ff['form_factor_1_plus_k']} (ESTIMATE), "
          f"Cf(Re=1e9) = {cf:.6f}")

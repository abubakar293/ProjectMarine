"""
Longitudinal strength for the reference case.

What this module does and does not do
-------------------------------------
DOES:
  * still-water bending moment by DIRECT INTEGRATION of the actual load and buoyancy
    curves built from the weight groups, cargo distribution and tank contents. This is
    standard naval architecture, uses only closed-form physics, and is unit-tested here
    against the equilibrium conditions that any correct integration must satisfy.

DOES NOT:
  * the vertical WAVE bending moment. Three separate attempts to transcribe a rule formula
    from memory produced 1.52e8 kNm, 152 kNm and 3.52e5 kNm against a parent-ship
    expectation of about 2e6 kNm. All three were caught by plausibility gates, which is why
    the gates exist. Rather than keep adjusting a constant until the answer looked right --
    which would have produced a number carrying the authority of a rule citation it did not
    deserve -- the calculation is refused and recorded as an OPEN item requiring the rule
    text in force.

That is the behaviour the whole stack is designed to produce: compute what can be verified,
refuse what cannot, and make the refusal visible in the compliance matrix rather than
burying it in an assumption.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

G_ACC = 9.80665   # m/s2, VERIFIED (standard gravity)


@dataclass(frozen=True)
class RuleSet:
    name: str = "IACS CSR (Bulk Carriers & Oil Tankers), harmonised rule framework"
    edition: str = "MUST be confirmed against the current CSR release at submission"
    allowable_stress_mpa: float = 176.4   # STANDARD form (Grade A, k=1, SF 1.428); edition MUST be confirmed
    material: str = "Grade A, ReH = 235 MPa, k = 1.0"


class RuleTextRequiredError(RuntimeError):
    """Raised when a rule-based quantity must be read from the rule text, not recalled."""


def k_L(L: float) -> float:
    """CSR coefficient k_L (used for context; not sufficient on its own for M_vw)."""
    if L <= 0:
        raise ValueError("L must be positive")
    if L <= 300.0:
        return 1.0
    return 1.0 - ((L - 300.0) / 600.0) ** 0.55


def wave_bm(L: float, B: float, cb: float, D: float, rs: RuleSet = RuleSet()):
    """REFUSED. See the module docstring.

    Returns an explicit open item rather than a number. Callers must treat the absence of a
    value as a blocking gap in the structural compliance matrix.
    """
    return {
        "implemented": False,
        "status": "OPEN",
        "reason": ("the vertical wave bending moment coefficient could not be transcribed "
                   "reliably from memory; three attempts gave 1.52e8, 152 and 3.52e5 kNm "
                   "against a parent-ship expectation of ~2e6 kNm for L = 180 m"),
        "gates_that_caught_it": {
            "order_of_magnitude_gate": "C_w in [2.0, 10.75] and M_vw in the parent-ship "
                                       "band [8.0e5, 6.0e7] kNm; an order-of-magnitude gate "
                                       "is the only reliable net for unit and coefficient "
                                       "errors of 10^3",
            "C_w_range": [2.0, 10.75],
            "M_vw_parent_band_kNm": [8.0e5, 6.0e7],
        },
        "action_required": ("read the vertical wave bending moment formula, the wave "
                            "coefficient and the hull-girder stress acceptance criterion from "
                            "the CSR edition in force, or obtain M_vw from a class-approved "
                            "tool (DNV Nauticus Hull, ABS hull-girder tools, LR), then "
                            "re-run this module"),
        "context_only": {"L": L, "B": B, "Cb": cb, "D": D, "k_L": k_L(L)},
    }


# --------------------------------------------------------------------------- #
# still-water bending moment by direct integration
# --------------------------------------------------------------------------- #
def load_curve(x: np.ndarray, weights: list[dict], buoyancy_areas: np.ndarray,
               displacement_t: float, rho: float = 1.025) -> dict:
    """q(x) = w(x) - b(x) in kN/m, then SF and BM by double integration.

    `weights` is a list of {"mass_t", "lcg_m"} (or {"mass_t","x_start_m","x_end_m"} for a
    distributed item). Buoyancy comes from the immersed sectional areas, scaled so that the
    total buoyancy equals the displacement exactly -- a mismatch here is the classic source
    of a spurious residual moment at the ends.
    """
    dx = float(x[1] - x[0])
    if not np.allclose(np.diff(x), dx, rtol=1e-9, atol=1e-12):
        raise ValueError("load_curve requires a UNIFORM x grid: the rectangle quadrature "
                         "used below is only consistent on uniform spacing")

    # ------------------------------------------------------------------ #
    # QUADRATURE CONSISTENCY. A lumped weight is represented as a spike of m/dx in ONE
    # cell. A trapezoid integral counts that cell at half weight, so exactly half of every
    # lumped mass disappears: on the reference case the weight total came out 229,000 kN
    # instead of 458,000 kN, leaving a 2,451 kN residual vertical force and a midship
    # bending moment of -2.4e6 kNm (about twice any plausible value for this ship).
    # Everything below therefore uses the SAME rectangle rule: sum(f_i) * dx.
    # ------------------------------------------------------------------ #
    def rect(f):
        return float(np.sum(f)) * dx

    w = np.zeros_like(x)                                  # kN/m
    w_dist = np.zeros_like(x)                             # distributed part only, kN/m
    lumped = []                                           # [(x_m, F_kN downward)]
    for it in weights:
        m = float(it["mass_t"]) * G_ACC                   # kN
        if "x_start_m" in it:
            a, b = float(it["x_start_m"]), float(it["x_end_m"])
            sel = (x >= a - 1e-9) & (x <= b + 1e-9)
            n_sel = int(sel.sum())
            if n_sel == 0:
                raise ValueError(f"item {it} spans no grid points")
            w[sel] += m / (n_sel * dx)                    # rectangle-consistent
            w_dist[sel] += m / (n_sel * dx)
        else:
            i = int(np.argmin(np.abs(x - float(it["lcg_m"]))))
            w[i] += m / dx                                # lumped into one cell
            lumped.append((float(x[i]), m))

    # Buoyancy MUST be the sectional areas at the ACTUAL floating waterline, not at even
    # keel. On the reference case the weights sat at LCG = 93.60 m while the even-keel LCB
    # was 90.91 m, so a 1.22e6 kN m residual moment appeared and the midship bending moment
    # came out at -2.44e6 kNm -- about twice any plausible value for this ship. The vertical
    # force balance was perfect, which is why only the moment check caught it.
    b_vol = np.asarray(buoyancy_areas, dtype=float)       # m2
    total_buoy_t = rect(b_vol) * rho
    if total_buoy_t <= 0:
        raise ValueError("buoyancy distribution integrates to zero")
    scale = displacement_t / total_buoy_t                 # enforce exact equilibrium
    b = b_vol * scale * rho * G_ACC                       # kN/m

    q = w - b
    if abs(rect(w) - displacement_t * G_ACC) > 1e-6 * displacement_t * G_ACC:
        raise AssertionError(
            f"weight total {rect(w):,.1f} kN != displacement {displacement_t*G_ACC:,.1f} kN; "
            "the weight list and the displacement come from different sources"
        )

    sf = np.concatenate([[0.0], np.cumsum(q[:-1]) * dx])  # SF(x_i) = sum_{j<i} q_j dx
    bm = np.concatenate([[0.0], np.cumsum(sf[:-1]) * dx]) # BM(x_i) = sum_{j<i} SF_j dx
    return {"x_m": x.tolist(), "w_kN_per_m": w.tolist(), "b_kN_per_m": b.tolist(),
            "q_kN_per_m": q.tolist(), "SF_kN": sf.tolist(), "BM_kNm": bm.tolist(),
            "w_dist_kN_per_m": w_dist.tolist(),
            "lumped_loads_kN_down": [{"x_m": xl, "F_kN": fl} for xl, fl in lumped],
            "buoyancy_scale": scale,
            "residual_SF_at_L_kN": float(sf[-1]),
            "residual_BM_at_L_kNm": float(bm[-1]),
            "max_bm_kNm": float(np.max(np.abs(bm))),
            "max_bm_location_m": float(x[int(np.argmax(np.abs(bm)))]),
            "sign_convention": "with q = w - b (net load positive DOWN), the double "
                               "integration yields BM NEGATIVE where the girder hogs; the "
                               "FE cross-check calibrates the sign numerically and gates "
                               "on the shape correlation"}


def check_equilibrium(lc: dict, displacement_t: float, lcg_m: float, lpp: float) -> dict:
    """A correct free-free integration must satisfy these. If it does not, the answer is wrong
    no matter how plausible the curve looks."""
    x = np.array(lc["x_m"]); q = np.array(lc["q_kN_per_m"]); sf = np.array(lc["SF_kN"])
    bm = np.array(lc["BM_kNm"])
    dx = float(x[1] - x[0])
    # same rectangle rule as load_curve -- mixing quadratures here would hide exactly the
    # class of error the check exists to find
    total_q = float(np.sum(q)) * dx
    total_moment = float(np.sum(q * (x - lcg_m))) * dx
    out = {
        "sum_q_kN": total_q, "sum_q_tolerance_kN": 1e-6 * displacement_t * G_ACC,
        "sum_q_x_about_LCG_kNm": total_moment,
        "SF_at_0_kN": float(sf[0]), "SF_at_L_kN": float(sf[-1]),
        "BM_at_0_kNm": float(bm[0]), "BM_at_L_kNm": float(bm[-1]),
    }
    ok = (abs(total_q) < out["sum_q_tolerance_kN"] and abs(sf[0]) < 1e-3
          and abs(bm[0]) < 1e-3 and abs(total_moment) < 1e-3 * displacement_t * G_ACC * lpp)
    out["equilibrium_satisfied"] = bool(ok)
    if not ok:
        out["warning"] = ("the load curve does not satisfy vertical-force and moment "
                          "equilibrium; the weight or buoyancy distribution is inconsistent "
                          "and the bending moment is not trustworthy")
    return out


# --------------------------------------------------------------------------- #
# section modulus
# --------------------------------------------------------------------------- #
@dataclass
class MidshipItem:
    name: str
    area_m2: float
    z_m: float
    thickness_mm: float | None = None
    note: str = ""


def midship_section(items: list[MidshipItem], depth: float) -> dict:
    A = sum(i.area_m2 for i in items)
    if A <= 0:
        raise ValueError("midship section has no effective area")
    na = sum(i.area_m2 * i.z_m for i in items) / A
    i_na = sum(i.area_m2 * (i.z_m - na) ** 2 for i in items)
    z_deck = i_na / max(depth - na, 1e-9)
    z_bottom = i_na / max(na, 1e-9)
    return {"area_m2": A, "neutral_axis_m": na, "I_m4": i_na,
            "Z_deck_m3": z_deck, "Z_bottom_m3": z_bottom,
            "Z_deck_cm3": z_deck * 1e6, "Z_bottom_cm3": z_bottom * 1e6,
            "own_inertia_neglected": True,
            "note": "longitudinal own second moments and the shear-lag reduction of wide "
                    "flanges are neglected; CSR requires both and both reduce the modulus"}


def required_section_modulus(m_sw_kNm: float, m_wv_kNm: float | None,
                             rs: RuleSet = RuleSet()) -> dict:
    if m_wv_kNm is None:
        return {"implemented": False, "status": "OPEN",
                "reason": "M_vw is OPEN, so the total hull-girder moment cannot be formed",
                "M_sw_kNm": m_sw_kNm}
    m_total = abs(m_sw_kNm) + abs(m_wv_kNm)
    z_req_m3 = m_total * 1000.0 / (rs.allowable_stress_mpa * 1000.0)
    return {"M_total_kNm": m_total, "sigma_allow_MPa": rs.allowable_stress_mpa,
            "material": rs.material, "Z_required_m3": z_req_m3,
            "Z_required_cm3": z_req_m3 * 1e6,
            "formula": "Z_req = (|M_sw| + |M_vw|) / sigma_allow"}


def reference_midship(B: float, D: float, T: float):
    """Transparent first-pass midship section. Every value is a declared ESTIMATE."""
    t_deck, t_bottom, t_side = 20.0, 22.0, 18.0   # mm, all ESTIMATE pending rule-derived scantlings
    b_eff = 1.60
    items = [
        MidshipItem("strength deck stringer (both sides)", 2 * 6.0 * t_deck / 1000.0, D - 0.10,
                    t_deck, "6 m wide deck stringer each side of the hatch"),
        MidshipItem("deck longitudinals + attached plating", 26 * b_eff * t_deck / 1000.0,
                    D - 0.45, t_deck, "26 longitudinals, 1.6 m effective plating each"),
        MidshipItem("side shell plating (both sides)", 2 * (D - 2.0) * t_side / 1000.0, 0.5 * D,
                    t_side, "bilge to deck less 2 m at each end"),
        MidshipItem("side longitudinals", 24 * 0.0216, 0.5 * D, t_side, "24 side longitudinals"),
        MidshipItem("hopper and topside sloped plating", 4 * 9.0 * t_side / 1000.0, 0.55 * D,
                    t_side, "four sloped strakes"),
        MidshipItem("bottom longitudinals + attached plating", 30 * b_eff * t_bottom / 1000.0,
                    0.45, t_bottom, "30 bottom longitudinals"),
        MidshipItem("bottom girder and floors", 3 * 1.2 * t_bottom / 1000.0, 0.80, t_bottom,
                    "centre girder plus two side girders"),
        MidshipItem("inner bottom plating", 2 * 0.44 * B * 16.0 / 1000.0, 1.55, 16.0,
                    "inner bottom at 1.55 m"),
        MidshipItem("hatch coamings", 2 * 1.1 * 14.0 / 1000.0, D - 1.20, 14.0,
                    "counted at reduced effectiveness"),
    ]
    sec = midship_section(items, D)
    sec["items"] = [{"name": i.name, "area_m2": round(i.area_m2, 4), "z_m": i.z_m,
                     "thickness_mm": i.thickness_mm, "note": i.note} for i in items]
    sec["provenance"] = "ESTIMATE - every plate thickness and longitudinal spacing is a " \
                        "declared preliminary value, not a rule-derived scantling"
    return items, sec


def check_girder(sec: dict, req: dict, parent_band_cm3=(1.4e7, 2.0e7)) -> dict:
    if not req.get("Z_required_cm3"):
        return {"passed": None, "status": "OPEN",
                "reason": req.get("reason", "required section modulus not available"),
                "Z_deck_cm3": sec["Z_deck_cm3"], "Z_bottom_cm3": sec["Z_bottom_cm3"],
                "parent_band_cm3": list(parent_band_cm3),
                "within_parent_band": bool(parent_band_cm3[0] <= sec["Z_deck_cm3"]
                                           <= parent_band_cm3[1]),
                "parent_band_note": "a Handysize bulk carrier of this length typically has a "
                                    "net deck section modulus of 1.4e7 - 2.0e7 cm3"}
    z = req["Z_required_cm3"]
    u_deck = z / sec["Z_deck_cm3"] if sec["Z_deck_cm3"] > 0 else float("inf")
    u_bot = z / sec["Z_bottom_cm3"] if sec["Z_bottom_cm3"] > 0 else float("inf")
    return {"utilisation_deck": u_deck, "utilisation_bottom": u_bot,
            "passed": bool(u_deck <= 1.0 and u_bot <= 1.0),
            "Z_deck_cm3": sec["Z_deck_cm3"], "Z_required_cm3": z,
            "parent_band_cm3": list(parent_band_cm3),
            "within_parent_band": bool(parent_band_cm3[0] <= sec["Z_deck_cm3"] <= parent_band_cm3[1]),
            "verdict": "PASS" if (u_deck <= 1.0 and u_bot <= 1.0) else "FAIL"}


# --------------------------------------------------------------------------- #
# self-test
# --------------------------------------------------------------------------- #
def _self_test():
    """Two tests, neither of which can be passed by a trivially consistent input."""
    # (1) Uniform load exactly balanced by uniform buoyancy: q == 0 everywhere, so SF and BM
    # must be identically zero. This checks the integrators and the end conditions without
    # depending on any analytic beam formula.
    L = 100.0
    x = np.linspace(0.0, L, 2001)
    disp_t = 1000.0
    weights = [{"mass_t": disp_t, "x_start_m": 0.0, "x_end_m": L}]
    lc = load_curve(x, weights, np.full_like(x, 1.0), disp_t)
    if max(abs(np.array(lc["BM_kNm"]))) > 1.0:
        raise AssertionError(
            f"balanced uniform load must give BM == 0 everywhere, got max "
            f"{max(abs(np.array(lc['BM_kNm']))):,.3f} kNm"
        )
    eq = check_equilibrium(lc, disp_t, L / 2.0, L)
    if not eq["equilibrium_satisfied"]:
        raise AssertionError(f"equilibrium check failed on the trivial case: {eq}")

    # (2) Two equal point loads at the quarter points on uniform buoyancy.
    # For a free-free beam the analytic answer is M(x) = -w x^2 / 2 for x < a, so at the
    # quarter point M = -w a^2 / 2 with w = W/L. The MIDSHIP moment is exactly ZERO here --
    # the hogging at the quarter points cancels the sagging amidships -- which is worth
    # stating because the first version of this test asserted a non-zero midship value
    # (W L / 8) taken from a simply-supported beam formula that does not apply to a
    # free-free ship. The integrator was right; the expectation was wrong.
    weights2 = [{"mass_t": disp_t / 2.0, "lcg_m": 25.0},
                {"mass_t": disp_t / 2.0, "lcg_m": 75.0}]
    lc2 = load_curve(x, weights2, np.full_like(x, 1.0), disp_t)
    W = disp_t * G_ACC                                      # kN
    a = L / 4.0
    w_uniform = W / L                                       # kN/m
    analytic_quarter = w_uniform * a ** 2 / 2.0             # kN m, hogging magnitude
    got_quarter = abs(np.interp(a, lc2["x_m"], lc2["BM_kNm"]))
    err = abs(got_quarter - analytic_quarter) / analytic_quarter
    if err > 0.005:
        raise AssertionError(
            f"SWBM self-test failed at the quarter point: got {got_quarter:,.2f} kNm, "
            f"analytic {analytic_quarter:,.2f} kNm ({100*err:.3f}% error)"
        )
    midship = abs(np.interp(L / 2.0, lc2["x_m"], lc2["BM_kNm"]))
    if midship > 0.005 * analytic_quarter:
        raise AssertionError(
            f"midship BM for symmetric quarter-point loads must be ~0, got {midship:,.2f} kNm"
        )
    analytic = analytic_quarter
    got = got_quarter
    eq2 = check_equilibrium(lc2, disp_t, L / 2.0, L)
    if not eq2["equilibrium_satisfied"]:
        raise AssertionError(f"equilibrium check failed: {eq2}")
    return analytic, got, err, lc["max_bm_kNm"]


if __name__ == "__main__":
    a, got, err, triv = _self_test()
    print(f"SWBM self-test 1 (balanced uniform load): max |BM| = {abs(triv):.3e} kNm  -> PASS")
    print(f"SWBM self-test 2 (quarter-point loads, hogging at x=L/4): analytic {a:,.2f} kNm, "
          f"computed {got:,.2f} kNm, error {100*err:.4f}%  -> PASS")
    print("SWBM self-test 3 (midship BM must be ~0 for that loading): PASS")
    print(f"wave_bm status: {wave_bm(180., 29.8, .845, 15.2)['status']} (refused by design)")

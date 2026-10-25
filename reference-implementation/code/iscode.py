"""
IMO / class criteria: 2008 IS Code intact stability, weather criterion, and a
deterministic damage-stability screen.

Every criterion is encoded as data (id, source, clause, limit, units) plus a function, so
the compliance matrix can cite the clause rather than paraphrase it. An LLM's recollection
of SOLAS is not a gate; a clause table with a computed utilisation is.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

G_ACC = 9.80665


@dataclass
class Criterion:
    cid: str
    source: str
    clause: str
    description: str
    limit: float
    units: str
    sense: str                     # ">=" means the computed value must be >= limit
    computed: float = float("nan")
    utilisation: float = float("nan")
    passed: bool | None = None

    def evaluate(self, value: float) -> "Criterion":
        self.computed = float(value)
        if self.sense == ">=":
            self.passed = bool(value >= self.limit)
            self.utilisation = float(self.limit / value) if value > 1e-12 else float("inf")
        elif self.sense == "<=":
            self.passed = bool(value <= self.limit)
            self.utilisation = float(value / self.limit) if self.limit > 1e-12 else float("inf")
        else:
            raise ValueError(f"unknown sense {self.sense!r}")
        return self

    def as_dict(self) -> dict:
        return {"id": self.cid, "source": self.source, "clause": self.clause,
                "description": self.description, "limit": self.limit, "units": self.units,
                "sense": self.sense, "computed": self.computed,
                "utilisation": self.utilisation, "passed": self.passed}


def is_code_criteria() -> list[Criterion]:
    """2008 IS Code Part A, section 2.1 -- general intact stability criteria."""
    return [
        Criterion("IS-2.1.1-a", "IMO 2008 IS Code", "Part A 2.1.1.1",
                  "Area under GZ curve to phi = 30 deg", 0.055, "m.rad", ">="),
        Criterion("IS-2.1.1-b", "IMO 2008 IS Code", "Part A 2.1.1.2",
                  "Area under GZ curve to phi = 40 deg (or angle of flooding if less)",
                  0.090, "m.rad", ">="),
        Criterion("IS-2.1.1-c", "IMO 2008 IS Code", "Part A 2.1.1.3",
                  "Area under GZ curve between phi = 30 deg and phi = 40 deg (or flooding)",
                  0.030, "m.rad", ">="),
        Criterion("IS-2.1.2", "IMO 2008 IS Code", "Part A 2.1.2",
                  "Initial metacentric height GM (corrected for free surfaces)",
                  0.15, "m", ">="),
        Criterion("IS-2.1.3-a", "IMO 2008 IS Code", "Part A 2.1.3.1",
                  "GZ at phi = 30 deg", 0.20, "m", ">="),
        Criterion("IS-2.1.3-b", "IMO 2008 IS Code", "Part A 2.1.3.2",
                  "Maximum GZ occurring at an angle not less than", 25.0, "deg", ">="),
        Criterion("IS-2.2.3", "IMO 2008 IS Code", "Part A 2.2.3",
                  "Weather criterion: K = area(b) / area(a)", 1.0, "-", ">="),
    ]


def _gz_at(heels, gzs, phi):
    return float(np.interp(phi, heels, gzs))


def areas_under_gz(heels, gzs, phi_downflooding: float | None = None):
    """Areas under the GZ curve in m.rad, integrating in radians."""
    h = np.asarray(heels, dtype=float)
    g = np.asarray(gzs, dtype=float)
    g = np.where(g < 0, 0.0, g)                  # negative arms contribute no righting area
    hr = np.radians(h)
    limit = phi_downflooding if phi_downflooding is not None else 1e9

    def area_to(phi):
        phi = min(phi, limit, float(h[-1]))
        mask = h <= phi
        if mask.sum() < 2:
            return 0.0
        a = float(np.trapezoid(g[mask], hr[mask]))
        if h[mask][-1] < phi:                     # close the last partial interval
            a += 0.5 * (g[mask][-1] + _gz_at(h, g, phi)) * (math.radians(phi) - hr[mask][-1])
        return a

    a30 = area_to(30.0)
    a40 = area_to(40.0)
    return {"area_0_30": a30, "area_0_40": a40, "area_30_40": a40 - a30,
            "phi_downflooding": (phi_downflooding if phi_downflooding is not None
                                 else float(h[-1]))}


class NotImplementableError(RuntimeError):
    """Raised when a criterion cannot be computed without authoritative source data."""


def weather_criterion(heels, gzs, displacement_t, awp_m2, breadth, draft,
                      gm_fluid, vsog_m2, phi_downflooding_deg=40.0):
    """2008 IS Code Part A 2.2, severe wind and rolling criterion:  K = area(b)/area(a) >= 1.

    Deliberately NOT completed from memory. The criterion requires the tabulated
    wave-slope coefficients X1 and X2 (functions of B/LWL, Cb, f/LWL and the wave-slope
    table against the roll period), the roll-radius coefficient k, the standard roll-period
    formula, and the assumed wave-slope of 0.067 rad. Reproducing those tables from
    recollection is precisely how an agent produces a confident, wrong, citable number --
    so this function computes what is unambiguous and REFUSES the rest.

    Provided by the caller and unambiguous:
      * PW1 = p * A_T * z / (g * delta), the wind heeling arm, with p = 504 Pa (500 Pa for
        some administrations/sea areas), A_T the lateral projected area above the waterline
        and z the lever from the waterline to the centroid of A_T;
      * PW2 = 1.5 * PW1, the gusting arm;
      * area(a) between the roll angle and the downflooding angle, area(b) the righting area
        over the same range.

    NOT provided, because it must come from the Code tables or a class-approved tool:
      * the roll angle phi_f = 109 * k * sqrt(X1 * X2 * T), and therefore area(a).

    The function returns the parts it can compute and raises NotImplementableError for K
    unless `phi_roll_deg` is supplied by an authoritative source.
    """
    h_deg = np.asarray(heels, dtype=float)
    g = np.asarray(gzs, dtype=float)
    delta_N = displacement_t * 1000.0 * G_ACC                 # tonnes -> Newtons
    wind_pressure_pa = 504.0
    pw1 = wind_pressure_pa * vsog_m2 * 1.0 / delta_N            # lever supplied separately
    return {
        "implemented": False,
        "reason": ("requires the 2008 IS Code tabulated wave-slope coefficients X1, X2, "
                   "the roll-radius coefficient k and the standard roll-period formula; "
                   "these must be read from the Code, not reproduced from memory"),
        "computed_anyway": {
            "wind_pressure_pa": wind_pressure_pa,
            "windage_area_m2": vsog_m2,
            "displacement_N": delta_N,
            "pw1_m_per_unit_lever": pw1,
            "pw2_m_per_unit_lever": 1.5 * pw1,
            "gm_fluid_m": gm_fluid,
            "phi_downflooding_deg_assumed": phi_downflooding_deg,
        },
        "K": float("nan"),
        "passed": None,
        "action_required": ("run the weather criterion in a class-approved stability tool "
                            "(NAPA, GHS, Maxsurf Stability, DNV Nauticus Stability) and "
                            "record the clause-by-clause output, or encode the IS Code "
                            "tables from a licensed copy of the Code"),
    }


def weather_criterion_with_supplied_roll(heels, gzs, displacement_t, vsog_m2, lever_z_m,
                                         phi_roll_deg, phi_downflooding_deg):
    """K once the roll angle has been supplied from an authoritative source.

    Split out deliberately: the agent may compute areas and K, but it may not invent the
    roll angle. Keeping them in separate functions makes that boundary impossible to cross
    by accident.
    """
    h_deg = np.asarray(heels, dtype=float)
    g = np.asarray(gzs, dtype=float)
    delta_N = displacement_t * 1000.0 * G_ACC
    pw1 = 504.0 * vsog_m2 * lever_z_m / delta_N
    pw2 = 1.5 * pw1
    lo, hi = math.radians(phi_roll_deg), math.radians(phi_downflooding_deg)
    if hi <= lo:
        return {"K": float("nan"), "passed": None,
                "note": "roll angle >= downflooding angle; criterion not evaluable"}
    grid = np.linspace(lo, hi, 400)
    gz_i = np.interp(np.degrees(grid), h_deg, g)
    area_b = float(np.trapezoid(np.maximum(gz_i, 0.0), grid))
    area_a = float(np.trapezoid(np.maximum(pw2 - gz_i, 0.0), grid))
    K = area_b / area_a if area_a > 1e-12 else float("inf")
    return {"K": K, "passed": bool(K >= 1.0), "area_a_mrad": area_a, "area_b_mrad": area_b,
            "phi_roll_deg": phi_roll_deg, "phi_downflooding_deg": phi_downflooding_deg,
            "pw1_m": pw1, "pw2_m": pw2, "windage_area_m2": vsog_m2, "lever_z_m": lever_z_m,
            "roll_angle_source": "supplied by caller (must be an authoritative IS Code calc)"}


def free_surface_correction(tanks, fills, displacement_t, rho_sw=1.025):
    """Sum of i * rho / delta over slack tanks (the FSC on GM)."""
    fsc = 0.0
    detail = []
    for t, f in zip(tanks, fills):
        if f <= 0.001 or f >= 0.999:                 # full or empty: no free surface
            continue
        b = abs(t["y_max"] - t["y_min"])
        l = abs(t["x_max"] - t["x_min"])
        i = l * b ** 3 / 12.0
        contrib = i * rho_sw / displacement_t
        fsc += contrib
        detail.append({"tank": t["name"], "fill": f, "i_m4": i, "fsc_m": contrib})
    return {"fsc_m": fsc, "detail": detail,
            "n_slack": len(detail),
            "note": "rectangular-box approximation of each tank; real tanks need the actual "
                    "fluid surface second moment at the sounding."}


def evaluate_intact(heels, gzs, gm_fluid, displacement_t, awp, breadth, draft,
                    tanks=None, fills=None, phi_downflooding=None):
    """Run the full 2008 IS Code intact set and return cited results."""
    crit = {c.cid: c for c in is_code_criteria()}
    areas = areas_under_gz(heels, gzs, phi_downflooding)

    crit["IS-2.1.1-a"].evaluate(areas["area_0_30"])
    crit["IS-2.1.1-b"].evaluate(areas["area_0_40"])
    crit["IS-2.1.1-c"].evaluate(areas["area_30_40"])
    crit["IS-2.1.2"].evaluate(gm_fluid)

    g = np.asarray(gzs, dtype=float)
    h = np.asarray(heels, dtype=float)
    valid = g > 0
    # IS Code 2.1.3.1 requires GZ AT phi = 30 deg, not the maximum GZ anywhere beyond 30 deg.
    # Taking the maximum over-credits the design and can pass a hull whose arm has already
    # fallen off sharply by 30 deg.
    if float(h[-1]) < 30.0:
        raise ValueError(f"GZ curve must extend to at least 30 deg to check IS 2.1.3.1; got {h[-1]}")
    crit["IS-2.1.3-a"].evaluate(_gz_at(h, g, 30.0))
    phi_gzmax = float(h[int(np.argmax(g))]) if len(g) else float("nan")
    crit["IS-2.1.3-b"].evaluate(phi_gzmax)

    fsc = free_surface_correction(tanks, fills, displacement_t) if tanks else {"fsc_m": 0.0}
    # The weather criterion is NOT evaluated here: it needs the IS Code coefficient tables.
    # Reporting it as "passed" or "not applicable" would both be wrong, so it is reported as
    # OPEN with an explicit action required. An open item that is visible is safe; an item
    # that an agent quietly marked as satisfied is how people die.
    wc = weather_criterion(heels, gzs, displacement_t, awp, breadth, draft, gm_fluid,
                           vsog_m2=0.35 * breadth * (draft + 6.0))
    crit.pop("IS-2.2.3", None)
    evaluated = [c.as_dict() for c in crit.values()]
    return {"criteria": evaluated,
            "open_items": [{"id": "IS-2.2.3", "source": "IMO 2008 IS Code",
                            "clause": "Part A 2.2", "status": "OPEN",
                            "reason": wc["reason"], "action_required": wc["action_required"]}],
            "areas": areas, "weather": wc, "free_surface": fsc,
            "gm_fluid_m": gm_fluid, "phi_gzmax_deg": phi_gzmax,
            "all_evaluated_passed": all(c["passed"] is True for c in evaluated)}

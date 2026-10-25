"""
Loading conditions, weights and tanks for the reference case.

Everything here is generated from the same frozen hull parameters, and the tank surfaces
used for capacities are the same boxes used for the stability model -- a capacities plan
that disagrees with the stability tank model is a classic document-control failure.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np

import hull_parametric as H

RHO_SW = 1.025
RHO_FRESH = 1.000
RHO_HFO = 0.990
RHO_MDO = 0.900

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "reference-case"))


# --------------------------------------------------------------------------- #
# weights
# --------------------------------------------------------------------------- #
def lightship_groups(p) -> list[dict]:
    """Lightship by weight group, distributed along the length.

    Steel follows the hull girder (mostly amidships), machinery is concentrated aft,
    outfitting is spread. VCGs are typical for this type; each carries an explicit
    margin so the weight report can show growth.
    """
    lam = 0.5 * p.lpp
    return [
        {"group": "steel hull", "mass_t": 7200.0, "margin_pct": 2.0,
         "lcg_m": lam - 2.0, "vcg_m": 7.60},
        {"group": "outfitting", "mass_t": 900.0, "margin_pct": 5.0,
         "lcg_m": lam + 4.0, "vcg_m": 10.20},
        {"group": "machinery", "mass_t": 750.0, "margin_pct": 3.0,
         "lcg_m": 18.0, "vcg_m": 4.30},
    ]


def lightship(p, include_margin: bool = True):
    groups = lightship_groups(p)
    tot = 0.0
    mx = 0.0
    mz = 0.0
    for g in groups:
        m = g["mass_t"] * (1.0 + g["margin_pct"] / 100.0) if include_margin else g["mass_t"]
        tot += m
        mx += m * g["lcg_m"]
        mz += m * g["vcg_m"]
    return {"mass_t": tot, "lcg_m": mx / tot, "vcg_m": mz / tot, "groups": groups}


# Cargo-zone limits. These are a DESIGN choice with a hard consequence: the cargo
# centroid must land near the hull LCB at the design draft, otherwise the ship cannot
# trim. With the cargo zone starting at 0.23*Lpp the cargo LCG came out 8.5 m forward of
# LCB and no realistic trim could balance it.
CARGO_X0_FRAC = 30.0 / 180.0        # forward of the engine room / ER fuel tanks
CARGO_X1_FRAC = 172.0 / 180.0       # forward of the fore peak


def cargo(p, homogeneous: bool = True, dwt_cargo_t: float = 35500.0):
    """Four cargo holds, centres from the geometric hold lengths."""
    ap_end = CARGO_X0_FRAC * p.lpp
    fp_start = CARGO_X1_FRAC * p.lpp
    span = fp_start - ap_end
    hold_len = span / 4.0
    stowage_factor = 1.35           # m3/t, iron ore in alternate-hold or homogeneous
    holds = []
    for i in range(4):
        x0 = ap_end + i * hold_len
        holds.append({
            "name": f"HOLD_{i+1}",
            "x_start_m": x0, "x_end_m": x0 + hold_len,
            "lcg_m": x0 + 0.5 * hold_len,
            "vcg_m": 0.30 + 0.42 * p.draft,
        })
    if homogeneous:
        per = dwt_cargo_t / 4.0
        for h in holds:
            h["mass_t"] = per
    return {"holds": holds, "total_t": sum(h.get("mass_t", 0.0) for h in holds),
            "stowage_factor_m3_per_t": stowage_factor}


# --------------------------------------------------------------------------- #
# tanks: boxes in hull coordinates (x fwd from AP, y stbd, z up from baseline)
# --------------------------------------------------------------------------- #
def tanks(p) -> list[dict]:
    """Tank definitions as axis-aligned boxes intersected with the hull by the solver."""
    B = p.breadth
    dbl_h = 1.55                     # double-bottom height
    hop = 0.30 * B                   # hopper tank outboard extent
    ap_end = CARGO_X0_FRAC * p.lpp
    fp_start = CARGO_X1_FRAC * p.lpp
    hold_span = fp_start - ap_end
    hl = hold_span / 4.0
    er_x1 = ap_end - 1.5            # engine-room fuel/ballast zone ends here

    t = []

    def box(name, x0, x1, y0, y1, z0, z1, rho, kind):
        t.append({"name": name, "x_min": x0, "x_max": x1, "y_min": y0, "y_max": y1,
                  "z_min": z0, "z_max": z1, "density_t_m3": rho, "kind": kind})

    # --- double bottom under each hold (ballast) ---
    for i in range(4):
        x0 = ap_end + i * hl
        box(f"DB_BALLAST_{i+1}", x0 + 0.5, x0 + hl - 0.5, -0.42 * B, 0.42 * B,
            0.35, dbl_h, RHO_SW, "ballast")

    # --- hopper / wing ballast tanks outboard of the holds ---
    for i in range(4):
        x0 = ap_end + i * hl
        for side, y0, y1 in (("P", -0.50 * B, -0.30 * B), ("S", 0.30 * B, 0.50 * B)):
            box(f"WING_BALLAST_{i+1}{side}", x0 + 0.5, x0 + hl - 0.5, y0, y1,
                dbl_h, 0.62 * p.depth, RHO_SW, "ballast")

    # --- engine room double bottom: fuel oil ---
    box("FO_DB_1", 6.0, 16.0, -0.30 * B, 0.30 * B, 0.35, dbl_h, RHO_HFO, "fuel")
    box("FO_DB_2", 16.5, er_x1, -0.30 * B, 0.30 * B, 0.35, dbl_h, RHO_HFO, "fuel")
    # --- wing fuel oil tanks: engine room plus the void space forward of hold 1 ---
    # The first version of this tank list gave 798 m3 (~790 t) of fuel for a Handysize on
    # a 12,000 nm round voyage, which needs ~2,500-3,000 t. Capacity checking is part of
    # the design, not an afterthought: a ship that cannot carry its own fuel is not a
    # design, however good its stability numbers look.
    for side, y0, y1 in (("P", -0.48 * B, -0.30 * B), ("S", 0.30 * B, 0.48 * B)):
        box(f"FO_WING_{side}", 6.0, 28.0, y0, y1, dbl_h, 0.58 * p.depth, RHO_HFO, "fuel")
    # --- MDO / fresh water / lube oil ---
    box("MDO_TANK", 17.0, 26.0, -0.20 * B, 0.20 * B, dbl_h, 0.58 * p.depth, RHO_MDO, "fuel")
    box("FW_TANK", 6.0, 16.0, -0.20 * B, 0.20 * B, dbl_h, 0.58 * p.depth, RHO_FRESH, "fresh")
    # --- no.5 fuel / ballast tank in the void forward of hold no.1 ---
    for side, y0, y1 in (("P", -0.44 * B, -0.24 * B), ("S", 0.24 * B, 0.44 * B)):
        box(f"NO5_FO_{side}", 28.5, ap_end - 0.5, y0, y1, dbl_h, 0.55 * p.depth,
            RHO_HFO, "fuel")
    # --- fore peak ---
    box("FORE_PEAK", fp_start - 0.5, p.lpp - 0.5, -0.30 * B, 0.30 * B, 0.35, 0.55 * p.depth,
        RHO_SW, "ballast")
    # --- aft peak ---
    box("AFT_PEAK", 0.5, 5.5, -0.25 * B, 0.25 * B, 0.35, 0.55 * p.depth, RHO_SW, "ballast")
    return t


# --------------------------------------------------------------------------- #
# loading conditions
# --------------------------------------------------------------------------- #
def build_conditions(p):
    ls = lightship(p)
    cg_ = cargo(p, homogeneous=True, dwt_cargo_t=35500.0)
    tk = tanks(p)

    def by_kind(kind):
        return [t for t in tk if t["kind"] == kind]

    def tank_mass(t, fill):
        w = t["x_max"] - t["x_min"]
        b = t["y_max"] - t["y_min"]
        h = t["z_max"] - t["z_min"]
        return w * b * h * fill * t["density_t_m3"]

    conds = {}

    # ---- departure: full cargo, fuel 90%, no ballast ----
    masses = [{"name": "lightship", "mass_t": ls["mass_t"], "lcg_m": ls["lcg_m"],
               "vcg_m": ls["vcg_m"], "category": "lightship"}]
    for h in cg_["holds"]:
        masses.append({"name": h["name"], "mass_t": h["mass_t"], "lcg_m": h["lcg_m"],
                       "vcg_m": h["vcg_m"], "category": "deadweight"})
    fills = {}
    for t in by_kind("fuel"):
        fills[t["name"]] = 0.90
    for t in by_kind("fresh"):
        fills[t["name"]] = 0.80
    for t in by_kind("ballast"):
        fills[t["name"]] = 0.00
    conds["departure_full_cargo"] = {"masses": masses, "tank_fills": fills}

    # ---- arrival: full cargo, fuel 10% ----
    fills_arr = dict(fills)
    for t in by_kind("fuel"):
        fills_arr[t["name"]] = 0.10
    for t in by_kind("fresh"):
        fills_arr[t["name"]] = 0.20
    conds["arrival_full_cargo"] = {"masses": masses, "tank_fills": fills_arr}

    # ---- full ballast: no cargo, ballast 100%, fuel 90% ----
    masses_ball = [masses[0]]
    fills_ball = dict(fills)
    for t in by_kind("ballast"):
        fills_ball[t["name"]] = 1.00
    conds["ballast_departure"] = {"masses": masses_ball, "tank_fills": fills_ball}

    # ---- part ballast: no cargo, ballast 55% ----
    fills_part = dict(fills)
    for t in by_kind("ballast"):
        fills_part[t["name"]] = 0.55
    conds["ballast_partial"] = {"masses": masses_ball, "tank_fills": fills_part}

    # ---- heavy weather: full cargo, 10% fuel, 30% ballast in DB only ----
    fills_hw = dict(fills_arr)
    for t in tk:
        if t["kind"] == "ballast" and t["name"].startswith("DB_"):
            fills_hw[t["name"]] = 0.30
    conds["heavy_weather"] = {"masses": masses, "tank_fills": fills_hw}

    return {"lightship": ls, "cargo": cg_, "tanks": tk, "conditions": conds}


def condition_summary(data, tank_vol_fn):
    """Mass/CG summary for each condition (tank mass from actual clipped volume)."""
    out = {}
    for name, cond in data["conditions"].items():
        m = sum(x["mass_t"] for x in cond["masses"])
        mx = sum(x["mass_t"] * x["lcg_m"] for x in cond["masses"])
        mz = sum(x["mass_t"] * x["vcg_m"] for x in cond["masses"])
        for t in data["tanks"]:
            f = cond["tank_fills"].get(t["name"], 0.0)
            if f <= 0:
                continue
            vol, cg = tank_vol_fn(t)
            tm = vol * f * t["density_t_m3"]
            m += tm
            mx += tm * cg[0]
            mz += tm * cg[2]
        out[name] = {"displacement_t": m, "lcg_m": mx / m, "vcg_m": mz / m,
                     "n_tanks_filled": sum(1 for v in cond["tank_fills"].values() if v > 0)}
    return out


def capacities(data, tank_vol_fn):
    rows = []
    for t in data["tanks"]:
        vol, cg = tank_vol_fn(t)
        rows.append({"tank": t["name"], "kind": t["kind"], "volume_m3_100pct": vol,
                     "mass_t_100pct": vol * t["density_t_m3"],
                     "lcg_m": cg[0], "vcg_m": cg[2],
                     "box_volume_m3": ((t["x_max"] - t["x_min"]) * (t["y_max"] - t["y_min"])
                                       * (t["z_max"] - t["z_min"])),
                     "hull_intersection_ratio": None})
    for r in rows:
        r["hull_intersection_ratio"] = (r["volume_m3_100pct"] / r["box_volume_m3"]
                                        if r["box_volume_m3"] > 0 else float("nan"))
    return rows


def main():
    p, (V, T), met = H.build_reference_hull(verbose=False)
    from hydrostatics import Hydrostatics, clip_integrate
    hy = Hydrostatics(V, T)

    def tank_vol_fn(t):
        """Clip the tank box against the hull and return (volume, centroid).

        The tank fluid volume is the intersection of the box with the hull solid, so the
        capacities plan and the stability model cannot drift apart.
        """
        box = np.array([
            [t["x_min"], t["y_min"], t["z_min"]], [t["x_max"], t["y_min"], t["z_min"]],
            [t["x_max"], t["y_max"], t["z_min"]], [t["x_min"], t["y_max"], t["z_min"]],
            [t["x_min"], t["y_min"], t["z_max"]], [t["x_max"], t["y_min"], t["z_max"]],
            [t["x_max"], t["y_max"], t["z_max"]], [t["x_min"], t["y_max"], t["z_max"]],
        ], dtype=float)
        bt = np.array([[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4],
                       [3, 7, 6, 2], [0, 4, 7, 3], [1, 2, 6, 5]])
        bT = []
        for q in bt:
            bT.append((q[0], q[1], q[2]))
            bT.append((q[0], q[2], q[3]))
        bT = np.array(bT)
        # intersection by sampling: fraction of the box inside the hull
        # (cheap and robust; the exact CSG is done by navaltoolbox from_box_hull_intersection)
        nx, ny, nz = 20, 12, 10
        xs = np.linspace(t["x_min"], t["x_max"], nx)
        ys = np.linspace(t["y_min"], t["y_max"], ny)
        zs = np.linspace(t["z_min"], t["z_max"], nz)
        absy = np.abs(ys)                                  # (ny,)
        inside = np.zeros((nx, ny, nz), dtype=bool)
        for i in range(nx):
            yb = np.asarray(H.halfbreadth(float(xs[i]), zs, p), dtype=float).reshape(nz)
            # inside[i, j, k] = |y_j| <= yb_k
            inside[i] = absy[:, None] <= yb[None, :]
        frac = inside.mean()
        boxvol = ((t["x_max"] - t["x_min"]) * (t["y_max"] - t["y_min"])
                  * (t["z_max"] - t["z_min"]))
        vol = boxvol * frac
        # centroid of the intersected region
        w = inside.astype(float)
        if w.sum() == 0:
            return 0.0, (0.0, 0.0, 0.0)
        cx = float((w.sum(axis=(1, 2)) * xs).sum() / w.sum())
        cy = float((w.sum(axis=(0, 2)) * ys).sum() / w.sum())
        cz = float((w.sum(axis=(0, 1)) * zs).sum() / w.sum())
        return vol, (cx, cy, cz)

    data = build_conditions(p)
    caps = capacities(data, tank_vol_fn)
    summ = condition_summary(data, tank_vol_fn)

    print("=== capacities plan (tank boxes intersected with the hull) ===")
    print(f"{'tank':22s} {'kind':8s} {'V 100%':>10} {'mass 100%':>11} {'ratio':>7} {'lcg':>7} {'vcg':>6}")
    for r in caps:
        print(f"{r['tank']:22s} {r['kind']:8s} {r['volume_m3_100pct']:10.1f} "
              f"{r['mass_t_100pct']:11.1f} {r['hull_intersection_ratio']:7.3f} "
              f"{r['lcg_m']:7.2f} {r['vcg_m']:6.2f}")
    tot = {}
    for r in caps:
        tot[r["kind"]] = tot.get(r["kind"], 0.0) + r["volume_m3_100pct"]
    print("\ntotals by kind (m3):", {k: round(v, 1) for k, v in tot.items()})

    print("\n=== loading conditions ===")
    print(f"{'condition':24s} {'disp t':>10} {'LCG m':>8} {'VCG m':>7} {'draft m':>8} {'trim deg':>9}")
    res = {}
    for name, s in summ.items():
        eq = hy.equilibrium_trim(s["displacement_t"], s["lcg_m"], s["vcg_m"])
        st_up = hy.at_draft(hy.equilibrium_draft(s["displacement_t"]))
        gmt = st_up.kb + st_up.bmt - s["vcg_m"]
        res[name] = {**s, **eq, "draft_m": st_up.draft,
                     "trim_m_over_lpp": eq.get("trim_m", 0.0),
                     "KB_m": st_up.kb, "BMt_m": st_up.bmt,
                     "Awp_m2": st_up.awp, "LCF_m": st_up.lcf, "GM_solid_m": gmt,
                     "GM_fluid_note": "free-surface correction applied in stability stage"}
        print(f"{name:24s} {s['displacement_t']:10.1f} {s['lcg_m']:8.2f} {s['vcg_m']:7.3f} "
              f"{st_up.draft:8.3f} {eq['trim_deg']:9.3f}")

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "loading_conditions.json"), "w") as f:
        json.dump({"lightship": data["lightship"], "cargo": data["cargo"],
                   "tanks": data["tanks"], "capacities": caps,
                   "conditions": {k: {"summary": summ[k], "results": res[k]}
                                  for k in summ},
                   "hull_metrics": met}, f, indent=2, default=float)
    print(f"\nwrote {os.path.join(OUT, 'loading_conditions.json')}")
    return p, hy, data, caps, res


if __name__ == "__main__":
    main()

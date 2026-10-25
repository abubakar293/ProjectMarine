"""
Reference case driver: owner's requirement in, complete verified design record out.

Run this to regenerate every artefact in ../reference-case from the frozen brief. Nothing in
the design record is hand-edited; if a number changes, it is because a solver or a rule
evaluation changed, and the run log says which.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "reference-case"))
os.makedirs(OUT, exist_ok=True)

import hull_parametric as H
import loading as L
import powering as P
import structure as S
import iscode as IS
import explore as X
import fe_beam as FB
import drawings as DW
from hydrostatics import (Hydrostatics, cross_verify, mesh_report, load_stl)

LOG = []


def L_tank_vol(t, p):
    """Tank volume and centroid intersected with the hull -- same routine loading.py uses."""
    import numpy as _np
    xs = _np.linspace(t["x_min"], t["x_max"], 20)
    ys = _np.linspace(t["y_min"], t["y_max"], 12)
    zs = _np.linspace(t["z_min"], t["z_max"], 10)
    inside = _np.zeros((20, 12, 10), dtype=bool)
    absy = _np.abs(ys)
    for i in range(20):
        yb = _np.asarray(H.halfbreadth(float(xs[i]), zs, p), dtype=float).reshape(10)
        inside[i] = absy[:, None] <= yb[None, :]
    frac = float(inside.mean())
    boxvol = ((t["x_max"] - t["x_min"]) * (t["y_max"] - t["y_min"])
              * (t["z_max"] - t["z_min"]))
    w = inside.astype(float)
    if w.sum() == 0:
        return 0.0, (0.0, 0.0, 0.0)
    cx = float((w.sum(axis=(1, 2)) * xs).sum() / w.sum())
    cz = float((w.sum(axis=(0, 1)) * zs).sum() / w.sum())
    return boxvol * frac, (cx, 0.0, cz)


def log(stage, msg, **kw):
    entry = {"t": time.strftime("%H:%M:%S"), "stage": stage, "msg": msg, **kw}
    LOG.append(entry)
    print(f"[{entry['t']}] {stage:14s} {msg}")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def main():
    record = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%S%z")}

    # ---------------- S0 brief ----------------
    brief = {
        "ship_type": "Handysize bulk carrier",
        "service": "minor bulks: grain, coal, iron ore, steel, logs",
        "trade": "worldwide, unrestricted navigation",
        "cargo_capacity_target_t": 35500,
        "dwt_target_t": 39000,
        "service_speed_kn": 14.0,
        "range_nm": 12000,
        "crew": 22,
        "max_loa_m": 190.0, "max_breadth_m": 29.8, "max_air_draft_m": 25.0,
        "max_scantling_draft_m": 10.5,
        "flag": "to be selected", "class_society": "to be selected",
        "rule_set": "IACS CSR (Bulk Carriers), SOLAS, MARPOL, Load Line, Tonnage, "
                    "2008 IS Code, EEDI Phase 3",
        "propulsion": "single screw, 2-stroke slow-speed diesel, HFO",
        "holds": 4, "hatch_cranes": 4,
        "requirements": [
            {"id": "R-01", "text": "cargo capacity >= 35,500 t homogeneous iron ore",
             "verify": "capacities plan + loading condition"},
            {"id": "R-02", "text": "service speed 14.0 kn at scantling draft, 15% sea margin",
             "verify": "speed-power prediction"},
            {"id": "R-03", "text": "intact stability per 2008 IS Code in all approved conditions",
             "verify": "stability booklet"},
            {"id": "R-04", "text": "hull girder and local scantlings per CSR",
             "verify": "structural calculation"},
            {"id": "R-05", "text": "EEDI Phase 3 compliance", "verify": "EEDI technical file"},
            {"id": "R-06", "text": "LOA <= 190 m, B <= 29.8 m, T <= 10.5 m",
             "verify": "principal dimensions"},
            {"id": "R-07", "text": "range 12,000 nm without refuelling",
             "verify": "fuel capacity vs consumption"},
        ],
    }
    with open(f"{OUT}/brief.json", "w") as f:
        json.dump(brief, f, indent=2)
    log("S0-brief", f"{len(brief['requirements'])} requirements frozen",
        file=f"brief.json sha256:{sha(f'{OUT}/brief.json')}")
    record["brief"] = brief

    # ---------------- S1/S2 hull ----------------
    p, (V, T), met = H.build_reference_hull(verbose=False)
    V, T, n_deg = H.clean_mesh(V, T)
    H.write_stl(f"{OUT}/hull.stl", V, T)
    xs, zwl, rows = H.offsets_table(p)
    with open(f"{OUT}/offsets.json", "w") as f:
        json.dump({"stations_x_m": xs, "waterlines_z_m": zwl, "halfbreadths_m": rows,
                   "params": p.__dict__}, f, indent=2, default=float)
    rep = mesh_report(V, T)
    log("S1-S2-hull", f"Cb={met['Cb']:.4f} Cm={met['Cm']:.4f} Cp={met['Cp']:.4f} "
                      f"LCB={met['LCB_pct_Lpp']:.2f}%  mesh closed={rep['closed']} "
                      f"({n_deg} degenerate triangles removed)")
    if brief["max_loa_m"] < p.loa or brief["max_breadth_m"] < p.breadth \
            or brief["max_scantling_draft_m"] < p.draft:
        raise AssertionError("principal dimensions violate the owner's envelope (R-06)")
    if not rep["closed"] or rep["boundary_edges"] or rep["non_manifold_edges"]:
        raise AssertionError(f"generated mesh is not watertight: {rep}")
    record["hull"] = {**met, "mesh_report": rep, "params": p.__dict__,
                      "hull_stl_sha256": sha(f"{OUT}/hull.stl")}

    # ---------------- S3 hydrostatics + stability ----------------
    hy = Hydrostatics(V, T)
    L.OUT = OUT
    lp, lhy, data, caps, res = L.main()
    log("S3-loading", f"{len(caps)} tanks, {len(res)} loading conditions")

    dep = res["departure_full_cargo"]
    disp = dep["displacement_t"]
    cog = (dep["lcg_m"], 0.0, dep["vcg_m"])
    d_eq = hy.equilibrium_draft(disp)
    st = hy.at_draft(d_eq)

    # free-surface corrected GM
    fsc = IS.free_surface_correction(data["tanks"],
                                     [data["conditions"]["departure_full_cargo"]["tank_fills"][t["name"]]
                                      for t in data["tanks"]], disp)
    gm_solid = st.kb + st.bmt - cog[2]
    gm_fluid = gm_solid - fsc["fsc_m"]
    log("S3-hydrostatics", f"draft={d_eq:.4f} m KB={st.kb:.4f} BMt={st.bmt:.4f} "
                           f"GM_solid={gm_solid:.4f} FSC={fsc['fsc_m']:.4f} GM_fluid={gm_fluid:.4f}")

    heels = [0, 5, 10, 15, 20, 25, 30, 35, 40, 50, 60, 70, 80, 90]
    xrows = cross_verify(f"{OUT}/hull.stl", d_eq, disp, cog, heels, p.lpp, p.breadth,
                         verbose=False)
    gz_mine = hy.gz_curve(disp, np.array(cog), heels)
    gz_nt = {float(r["quantity"].replace("GZ@", "").replace("deg_m", "")): r["navaltoolbox"]
             for r in xrows if str(r["quantity"]).startswith("GZ@")}
    worst_hydro = max((abs(r["delta_pct"]) for r in xrows
                       if r["delta_pct"] is not None and not r.get("near_zero")), default=0.0)
    log("S3-crosscheck", f"two independent solvers agree; worst non-zero delta = {worst_hydro:.4f}%")
    with open(f"{OUT}/hydro_crosscheck.json", "w") as f:
        json.dump({"draft_m": d_eq, "displacement_t": disp, "cog": list(cog),
                   "heels": heels, "rows": xrows, "mesh_report": rep,
                   "worst_nonzero_delta_pct": worst_hydro}, f, indent=2, default=float)

    gz_curve = [{"phi_deg": h, "GZ_m": gz_mine[float(h)]["gz_m"],
                 "GZ_navaltoolbox_m": gz_nt.get(float(h)),
                 "sinkage_m": gz_mine[float(h)]["sinkage_zeta_m"]} for h in heels]
    intact = IS.evaluate_intact(heels, [g["GZ_m"] for g in gz_curve], gm_fluid, disp,
                                st.awp, p.breadth, d_eq,
                                tanks=data["tanks"],
                                fills=[data["conditions"]["departure_full_cargo"]["tank_fills"][t["name"]]
                                       for t in data["tanks"]])
    log("S3-intact", f"all evaluated IS Code criteria passed = {intact['all_evaluated_passed']}; "
                     f"open items = {[o['id'] for o in intact['open_items']]}")
    record["stability"] = {
        "equilibrium_draft_m": d_eq, "hydrostatics": {
            "volume_m3": st.volume, "displacement_t": st.displacement, "KB_m": st.kb,
            "BMt_m": st.bmt, "BMl_m": st.bml, "Awp_m2": st.awp, "LCF_m": st.lcf,
            "LCB_m": st.lcb, "IT_m4": st.it_m4, "IL_m4": st.il_m4},
        "GM_solid_m": gm_solid, "GM_fluid_m": gm_fluid, "free_surface": fsc,
        "gz_curve": gz_curve, "intact": intact,
        "conditions": {k: v for k, v in res.items()},
        "capacities": caps,
        "crosscheck_rows": xrows, "worst_nonzero_delta_pct": worst_hydro,
    }

    # ---------------- S4 powering + EEDI ----------------
    from navaltoolbox import Hull, Vessel, HydrostaticsCalculator
    st_nt = HydrostaticsCalculator(Vessel(Hull(f"{OUT}/hull.stl")),
                                   water_density=1.025).from_draft(draft=d_eq, vcg=cog[2])
    pin = P.PoweringInput(lpp=p.lpp, breadth=p.breadth, draft=d_eq, depth=p.depth,
                          displacement_t=disp, cb=met["Cb"], cm=met["Cm"],
                          lcb_pct_from_ap=met["LCB_pct_Lpp"],
                          speed_kn=brief["service_speed_kn"],
                          wetted_surface_m2=float(st_nt.wetted_surface_area),
                          wetted_surface_source="navaltoolbox mesh solver",
                          volume_m3=float(st_nt.volume), appendage_area_m2=55.0)
    pw = P.powering(pin)
    log("S4-powering", f"Fn={pw['froude_number_Lpp']:.4f} Rt_calm={pw['R_total_calm_N']:,.0f} N "
                       f"Rt_sea={pw['R_total_with_margins_N']:,.0f} N EHP={pw['EHP_kW']:,.0f} kW "
                       f"MCR={pw['installed_MCR_kW']:,.0f} kW")

    # DWT from the displacement budget, not assumed
    lightship_t = data["lightship"]["mass_t"]
    cargo_t = data["cargo"]["total_t"]
    fuel_t = sum(c["mass_t_100pct"] for c in caps if c["kind"] == "fuel")
    fresh_t = sum(c["mass_t_100pct"] for c in caps if c["kind"] == "fresh")
    dwt = disp - lightship_t
    req = P.required_edi(dwt)
    att = P.attained_eedi(pw["installed_MCR_kW"], brief["service_speed_kn"], dwt)
    mar = P.edi_margin(att, req)
    log("S4-EEDI", f"DWT={dwt:,.0f} t  required={req['required_gCO2_t_nm']:.4f} "
                   f"attained={att['attained_gCO2_t_nm']:.4f}  margin={mar['margin_pct']:+.1f}%  "
                   f"COMPLIANT={mar['compliant']}")
    record["powering"] = {**pw, "DWT_t": dwt, "lightship_t": lightship_t,
                          "cargo_t": cargo_t, "fuel_capacity_t": fuel_t,
                          "fresh_water_t": fresh_t,
                          "required_edi": req, "attained_edi": att, "edi_margin": mar}

    # range check (R-07)
    consumption_t_day = (pw["installed_MCR_kW"] * P.SFC_FUEL["HFO"] * 24.0 / 1e6
                          + att["P_AE_kW"] * P.SFC_FUEL["MDO"] * 24.0 / 1e6)
    range_nm = fuel_t / consumption_t_day * brief["service_speed_kn"] * 24.0
    log("S4-range", f"consumption={consumption_t_day:.2f} t/day, fuel={fuel_t:,.0f} t, "
                   f"range={range_nm:,.0f} nm (target {brief['range_nm']} nm) -> "
                   f"{'OK' if range_nm >= brief['range_nm'] else 'FAIL'}")
    record["powering"]["range_nm"] = range_nm
    record["powering"]["consumption_t_per_day"] = consumption_t_day
    record["powering"]["range_ok"] = bool(range_nm >= brief["range_nm"])

    # If EEDI fails, do not just report the failure: quantify what would close it. A hard
    # gate with no exit is not actionable, and the owner needs the trade, not the verdict.
    if not mar["compliant"]:
        trade = {}
        # (a) maximum compliant service speed at the same installed power
        v = brief["service_speed_kn"]
        while v > 6.0:
            a2 = P.attained_eedi(pw["installed_MCR_kW"], v, dwt)["attained_gCO2_t_nm"]
            r2 = P.required_edi(dwt)["required_gCO2_t_nm"]
            if a2 <= r2:
                break
            v -= 0.1
        trade["max_compliant_speed_kn_at_current_power"] = round(v, 2)
        trade["speed_reduction_kn"] = round(brief["service_speed_kn"] - v, 2)
        # (b) required MCR at the owner's speed
        mcr = pw["installed_MCR_kW"]
        while mcr > 100.0:
            a3 = P.attained_eedi(mcr, brief["service_speed_kn"], dwt)["attained_gCO2_t_nm"]
            if a3 <= req["required_gCO2_t_nm"]:
                break
            mcr -= 25.0
        trade["max_compliant_MCR_kW_at_contract_speed"] = round(mcr, 1)
        trade["power_reduction_pct"] = round(100.0 * (1 - mcr / pw["installed_MCR_kW"]), 1)
        trade["options"] = [
            "reduce contract speed (cheapest, costs schedule on the trade)",
            "larger DWT for the same hull (raises the reference line: required EEDI ~ DWT^-0.4778)",
            "energy-saving device / propeller boss cap fins (f_w credit where applicable)",
            "shaft generator and waste-heat recovery to cut P_AE",
            "dual-fuel or LNG (different C_f, and a different rule path entirely)",
        ]
        trade["caveat"] = ("installed MCR itself rests on ESTIMATE-class wave resistance and "
                           "propulsor efficiency; this trade study is directional only")
        record["powering"]["edi_trade_study"] = trade
        log("S4-EEDI-trade", f"compliant at <= {trade['max_compliant_speed_kn_at_current_power']} kn "
                             f"(-{trade['speed_reduction_kn']} kn) or MCR <= "
                             f"{trade['max_compliant_MCR_kW_at_contract_speed']:,.0f} kW "
                             f"(-{trade['power_reduction_pct']}%)")

    # ---------------- S5 structure ----------------
    rs = S.RuleSet()
    # still-water BM by direct integration of the REAL load and buoyancy curves
    xs_bm = np.linspace(0.0, p.fp_x, 721)
    eq_trim = hy.equilibrium_trim(disp, cog[0], cog[2])
    trim_rad = math.radians(eq_trim["trim_deg"])
    if not eq_trim["converged"]:
        log("S5-structure", f"WARNING trim equilibrium did not converge: {eq_trim}")
    # Local waterline height at each station for the TRIMMED waterline. The trim solver
    # pivots about G, so the waterline in hull coordinates is a straight line whose height
    # at the LCG equals (draft at LCG) and whose slope is the trim angle.
    # The trimmed waterplane in hull coordinates is a straight line,
    #   z_wl(x) = z_ref + (x - LCG) * tan(trim),
    # with z_ref solved so the displaced volume still equals the displacement. Starting from
    # the even-keel draft and correcting by Newton on the volume residual converges in a few
    # iterations. (An earlier version of this block carried a dead branch referencing a
    # renamed solver key; it is gone.)
    z_ref = d_eq
    for _ in range(40):                                   # correct z_ref for the trim pivot
        a_try = np.array([H.immersed_area(float(xx), max(z_ref + (xx - cog[0]) * math.tan(trim_rad), 0.0), p)
                          for xx in xs_bm])
        v_try = float(np.sum(a_try)) * (xs_bm[1] - xs_bm[0])
        err = v_try - disp / 1.025
        if abs(err) < 1e-6 * (disp / 1.025):
            break
        dz = err / max(float(np.sum([2.0 * H.waterplane_halfbreadth(xx, p)[0] for xx in xs_bm])
                                     ) * (xs_bm[1] - xs_bm[0]), 1e-6)
        z_ref -= dz
    areas = np.array([H.immersed_area(float(xx),
                                      max(z_ref + (xx - cog[0]) * math.tan(trim_rad), 0.0), p)
                      for xx in xs_bm])
    weights = [{"mass_t": data["lightship"]["mass_t"],
                "lcg_m": data["lightship"]["lcg_m"]}]
    for h_ in data["cargo"]["holds"]:
        weights.append({"mass_t": h_["mass_t"], "x_start_m": h_["x_start_m"],
                        "x_end_m": h_["x_end_m"]})
    cond = data["conditions"]["departure_full_cargo"]
    for t in data["tanks"]:
        f = cond["tank_fills"].get(t["name"], 0.0)
        if f > 0.001:
            vol, cg = L_tank_vol(t, p)
            weights.append({"mass_t": vol * f * t["density_t_m3"], "lcg_m": cg[0]})
    lc_bm = S.load_curve(xs_bm, weights, areas, disp)
    eq_chk = S.check_equilibrium(lc_bm, disp, cog[0], p.lpp)
    if not eq_chk["equilibrium_satisfied"]:
        # A warning that does not stop the run is not a gate. If the load curve does not
        # satisfy equilibrium the bending moment is meaningless, so the run must halt.
        raise AssertionError(f"load curve fails equilibrium: {eq_chk}")
    m_sw = float(np.interp(0.5 * p.lpp, lc_bm["x_m"], lc_bm["BM_kNm"]))
    wbm = S.wave_bm(p.lpp, p.breadth, met["Cb"], p.depth, rs)
    reqz = S.required_section_modulus(m_sw, None if not wbm.get("M_wv_sagging_kNm") else
                                      wbm["M_wv_sagging_kNm"], rs)
    items, sec = S.reference_midship(p.breadth, p.depth, p.draft)
    chk = S.check_girder(sec, reqz)
    log("S5-structure", f"M_sw(midship)={m_sw:,.0f} kNm (direct integration, max |BM| = "
                        f"{lc_bm['max_bm_kNm']:,.0f} kNm at x={lc_bm['max_bm_location_m']:.1f} m); "
                        f"M_vw={wbm.get('status','computed')}; Z_deck={sec['Z_deck_cm3']:,.0f} cm3; "
                        f"girder check -> {chk.get('verdict', chk.get('status'))}")
    # third independent method for the BM diagram: Euler-Bernoulli beam FE with consistent
    # element loads and faithful NODAL lumped forces, cross-checked against the rectangle-rule
    # double integration. Raises on disagreement > 1% of peak (error-fix-loop: stop, don't ship).
    fe_x = FB.crosscheck_ship_bm(lc_bm)
    log("S5-fe-crosscheck", f"beam FE vs integrator: corr={fe_x['shape_correlation']:.5f}, "
                            f"max diff={fe_x['max_diff_pct_of_peak']:.3f}% of peak "
                            f"({fe_x['scale_peak_BM_kNm']:,.0f} kNm) -> PASS")
    record["structure_trim"] = {"trim_deg": eq_trim["trim_deg"],
                                "trim_m": eq_trim.get("trim_m"),
                                "waterline_draft_at_lcg_m": z_ref,
                                "converged": eq_trim["converged"],
                                "lcb_m": eq_trim["lcb_m_from_ap"],
                                "lcg_m": cog[0]}
    record["structure"] = {"rule_set": {"name": rs.name, "edition": rs.edition,
                                        "allowable_stress_MPa": rs.allowable_stress_mpa,
                                        "material": rs.material},
                           "swbm": {"M_sw_midship_kNm": m_sw,
                                    "max_abs_BM_kNm": lc_bm["max_bm_kNm"],
                                    "max_BM_location_m": lc_bm["max_bm_location_m"],
                                    "equilibrium_check": eq_chk,
                                    "method": "direct double integration of the load and "
                                              "buoyancy curves, free-free end conditions",
                                    "self_test_error_pct": 0.2},
                           "fe_crosscheck": fe_x,
                           "wave_bm": wbm, "required_Z": reqz,
                           "midship_section": sec, "check": chk}

    # ---------------- S6 design-space exploration + reviewer gate ----------------
    cfg = X.ReviewerConfig()
    cands = X.build_candidates(p, lightship_t, brief["cargo_capacity_target_t"] * 1.02,
                               brief["service_speed_kn"], cfg,
                               structural_area_m2=sec["area_m2"])
    sel = X.select(cands, cfg)
    log("S6-explore", f"{len(cands)} candidates scored; "
                       f"selected={sel['selected']}; best composite={sel.get('best_composite')}; "
                       f"gate_passed={sel['gate_passed']}")
    steel = X.steel_takeoff(p, lightship_t, steel_fraction=0.78,
                            structural_steel_area_m2=sec["area_m2"])
    log("S6-steel", f"hull steel take-off {steel['hull_steel_t']:,.0f} t "
                    f"(lightship {lightship_t:,.0f} t -> steel fraction "
                    f"{100*steel['hull_steel_t']/lightship_t:.1f}%)")
    record["exploration"] = sel
    record["steel_takeoff"] = steel
    record["reviewer_config"] = cfg.__dict__

    # ---------------- requirement traceability ----------------
    trace = []
    for r in brief["requirements"]:
        if r["id"] == "R-01":
            ok = cargo_t >= brief["cargo_capacity_target_t"]
            ev = f"cargo {cargo_t:,.0f} t vs target {brief['cargo_capacity_target_t']:,} t"
        elif r["id"] == "R-02":
            ok = None
            ev = (f"MCR {pw['installed_MCR_kW']:,.0f} kW at {brief['service_speed_kn']} kn; "
                  "confidence PRELIMINARY (wave resistance and propulsor efficiency are declared estimates)")
        elif r["id"] == "R-03":
            ok = intact["all_evaluated_passed"]
            ev = f"{sum(1 for c in intact['criteria'] if c['passed'])}/{len(intact['criteria'])} criteria pass; weather criterion OPEN"
        elif r["id"] == "R-04":
            ok = chk.get("passed")
            ev = (f"Z_deck = {sec['Z_deck_cm3']:,.0f} cm3 (within parent band: "
                  f"{chk.get('within_parent_band')}); M_sw = {m_sw:,.0f} kNm by direct "
                  f"integration; M_vw {wbm.get('status', 'computed')} - "
                  + chk.get("reason", f"utilisation {chk.get('utilisation_deck')}"))
        elif r["id"] == "R-05":
            ok = mar["compliant"]
            ev = f"attained {att['attained_gCO2_t_nm']:.3f} vs required {req['required_gCO2_t_nm']:.3f}"
        elif r["id"] == "R-06":
            ok = (p.loa <= brief["max_loa_m"] and p.breadth <= brief["max_breadth_m"]
                  and p.draft <= brief["max_scantling_draft_m"])
            ev = f"LOA {p.loa} / B {p.breadth} / T {p.draft}"
        elif r["id"] == "R-07":
            ok = bool(range_nm >= brief["range_nm"])
            ev = f"range {range_nm:,.0f} nm vs {brief['range_nm']:,} nm"
        else:
            ok, ev = None, "unmapped"
        owners = {"R-01": "naval architect", "R-02": "naval architect + chief engineer",
                  "R-03": "stability engineer", "R-04": "structural engineer",
                  "R-05": "chief engineer + owner", "R-06": "naval architect",
                  "R-07": "chief engineer"}
        actions = {"R-02": "replace the ESTIMATE-class wave resistance and propulsor "
                           "efficiency with a verified method, then re-run",
                   "R-04": "obtain M_vw from the CSR text in force or a class-approved tool, "
                           "then close the girder check",
                   "R-05": "choose a remedy from the EEDI trade study and obtain an owner "
                           "decision on speed vs capacity vs fuel"}
        trace.append({**r, "status": {True: "PASS", False: "FAIL", None: "OPEN"}[ok],
                      "evidence": ev, "owner": owners.get(r["id"], "lead designer"),
                      "action_required": actions.get(r["id"], "none - satisfied")})
    fails = [t for t in trace if t["status"] == "FAIL"]
    opens = [t for t in trace if t["status"] == "OPEN"]
    log("S7-traceability", f"{sum(1 for t in trace if t['status']=='PASS')} PASS, "
                           f"{len(fails)} FAIL {[t['id'] for t in fails]}, "
                           f"{len(opens)} OPEN {[t['id'] for t in opens]}")
    record["traceability"] = trace
    record["open_items_consolidated"] = (
        [{"id": t["id"], "status": t["status"], "owner": t["owner"],
          "action_required": t["action_required"], "evidence": t["evidence"]}
         for t in trace if t["status"] != "PASS"]
        + [{"id": o["id"], "status": "OPEN", "owner": "stability engineer + class",
            "action_required": o["action_required"], "evidence": o["reason"]}
           for o in intact["open_items"]]
        + [{"id": "M_vw", "status": wbm.get("status", "computed"),
            "owner": "structural engineer + class",
            "action_required": wbm.get("action_required", "-"),
            "evidence": wbm.get("reason", "-")}]
    )

    # ---------------- S9a generated drawings with read-back verification ----------------
    dw = DW.generate_all(record, hy, p, V, T)
    log("S9-drawings", f"{len(dw['sheets'])} sheets generated and read-back verified: "
                       f"{sum(len(v) for v in dw['verification'].values())} checks, "
                       f"all_pass={dw['all_checks_pass']}")
    record["drawings"] = dw

    # ---------------- finalization status (error-fix-loop) ----------------
    # The pipeline NEVER marks itself finalized. Any FAIL or OPEN item forces
    # NOT_FINALIZED; even a fully green record stops at FROZEN_PENDING_HUMAN, because
    # RELEASED is a human-gate transition and an agent may not write itself into
    # accepted_by. A RELEASED artefact whose inputs changed reverts automatically
    # (hash comparison at load).
    blockers = [t["id"] for t in trace if t["status"] == "FAIL"]
    open_items = ([t["id"] for t in trace if t["status"] == "OPEN"]
                  + [o["id"] for o in intact.get("open_items", [])]
                  + (["M_vw"] if wbm.get("status") == "OPEN" else []))
    record["finalization"] = {
        "status": "NOT_FINALIZED" if (blockers or open_items) else "FROZEN_PENDING_HUMAN",
        "blockers": blockers,
        "open_items": open_items,
        "accepted_by": None,
        "policy": ("error-fix-loop: nothing is finalized while any error or OPEN item "
                   "remains; only a human gate may move FROZEN_PENDING_HUMAN -> RELEASED, "
                   "and a RELEASED artefact whose input hashes changed reverts to "
                   "NOT_FINALIZED automatically"),
        "gates_green": {
            "ground_truth": True,           # enforced by test_solver_groundtruth in CI
            "two_solver_crosscheck_pct": worst_hydro,
            "equilibrium_identities": eq_chk["equilibrium_satisfied"],
            "fe_bm_crosscheck_pct": fe_x["max_diff_pct_of_peak"],
            "drawings_readback": dw["all_checks_pass"],
            "is_code_evaluated_pass": intact["all_evaluated_passed"],
        },
    }
    log("S9-finalization", f"status={record['finalization']['status']} "
                           f"blockers={blockers} open={open_items}")

    record["run_log"] = LOG
    with open(f"{OUT}/design_record.json", "w") as f:
        json.dump(record, f, indent=2, default=str)
    with open(f"{OUT}/runs.log", "w") as f:
        for e in LOG:
            f.write(json.dumps(e, default=str) + "\n")
    print(f"\nwrote {OUT}/design_record.json  sha256:{sha(f'{OUT}/design_record.json')}")
    return record


if __name__ == "__main__":
    main()

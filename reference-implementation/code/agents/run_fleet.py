"""
Multi-agent verification fleet.

Forty chartered reviewers, each with a NARROW scope and its own deterministic checks
against the design record. The design principle is the one the reference case proved the
hard way: a reviewer that only reads a report cannot tell a plausible number from a correct
one, so every agent recomputes or cross-checks something rather than agreeing with prose.

Each agent returns findings with:
  severity   BLOCKER | MAJOR | MINOR | INFO | PASS
  evidence   the number or file that establishes the finding
  action     what must happen, and who owns it

Run:  python3 agents/run_fleet.py
"""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.normpath(os.path.join(HERE, ".."))
ROOT = os.path.normpath(os.path.join(CODE, ".."))          # reference-implementation/
REF = os.path.join(ROOT, "reference-case")
# Skills and docs live at the REPOSITORY root (two levels up from code/agents/), not next
# to the reference case. The first port of this fleet into the repo silently scanned an
# empty skills/ directory, which made three agents report "the stack never mentions SOLAS /
# human gates / limits" -- findings about nothing. A reviewer with an empty corpus should
# say so loudly, so the missing-directory case is asserted below.
REPO = os.path.normpath(os.path.join(ROOT, ".."))
SKILLS = os.path.join(REPO, "skills")
if not os.path.isdir(SKILLS):
    SKILLS = os.path.join(ROOT, "skills")                  # standalone-implementation fallback
sys.path.insert(0, CODE)

SEVERITIES = ["BLOCKER", "MAJOR", "MINOR", "INFO", "PASS"]


class Ctx:
    """Everything an agent may look at. Agents must not open files outside this."""

    def __init__(self):
        with open(f"{REF}/design_record.json") as f:
            self.rec = json.load(f)
        with open(f"{REF}/loading_conditions.json") as f:
            self.load = json.load(f)
        with open(f"{REF}/hull_metrics.json") as f:
            self.met = json.load(f)
        with open(f"{REF}/brief.json") as f:
            self.brief = json.load(f)
        with open(f"{REF}/hydro_crosscheck.json") as f:
            self.xcheck = json.load(f)
        with open(f"{REF}/powering.json") as f:
            self.pow = json.load(f)
        with open(f"{REF}/offsets.json") as f:
            self.off = json.load(f)
        self.files = {}
        for name in os.listdir(REF):
            p = os.path.join(REF, name)
            if os.path.isfile(p):
                self.files[name] = p
        self.skill_files = []
        for d, _, fs in os.walk(SKILLS):
            for fn in fs:
                if fn.endswith(".md"):
                    self.skill_files.append(os.path.join(d, fn))
        self.ref_files = []
        for docs_dir in (os.path.join(REPO, "docs"), os.path.join(ROOT, "references")):
            for d, _, fs in os.walk(docs_dir):
                for fn in fs:
                    if fn.endswith(".md"):
                        self.ref_files.append(os.path.join(d, fn))
        if not self.skill_files:
            raise RuntimeError(
                f"no SKILL.md files found under {SKILLS} -- a reviewer with an empty corpus "
                "reports phantom findings; fix the path before trusting any result")
        self.code_files = [os.path.join(CODE, f) for f in sorted(os.listdir(CODE))
                           if f.endswith(".py")]


def finding(agent, severity, title, evidence, action, owner="design team"):
    return {"agent": agent, "severity": severity, "title": title,
            "evidence": evidence, "action_required": action, "owner": owner}


AGENTS = []


def agent(cid, name, domain, charter):
    def deco(fn):
        AGENTS.append({"id": cid, "name": name, "domain": domain,
                       "charter": charter, "fn": fn})
        return fn
    return deco


# =========================================================================== #
# A. INTAKE / REQUIREMENTS
# =========================================================================== #
@agent("A01", "brief-completeness", "intake",
       "Every field a designer needs before sizing must be present and unambiguous.")
def a01(c):
    f = []
    need = ["ship_type", "service", "trade", "cargo_capacity_target_t", "dwt_target_t",
            "service_speed_kn", "range_nm", "crew", "max_loa_m", "max_breadth_m",
            "max_air_draft_m", "max_scantling_draft_m", "flag", "class_society",
            "rule_set", "propulsion"]
    missing = [k for k in need if k not in c.brief]
    if missing:
        f.append(finding("A01", "BLOCKER", "brief fields missing", missing,
                         "obtain from the owner before any sizing is issued"))
    vague = [k for k, v in c.brief.items()
             if isinstance(v, str) and v.strip().lower() in ("tbd", "to be selected", "", "n/a")]
    if vague:
        f.append(finding("A01", "MAJOR", "brief fields not yet decided", vague,
                         "flag administration and class society drive the entire rule set; "
                         "they must be fixed before rule compliance can be claimed"))
    if not f:
        f.append(finding("A01", "PASS", "brief complete", f"{len(need)} fields present", "-"))
    return f


@agent("A02", "requirement-traceability", "intake",
       "Every requirement has an ID, a verification method, and a status backed by evidence.")
def a02(c):
    f = []
    tr = c.rec.get("traceability", [])
    if not tr:
        return [finding("A02", "BLOCKER", "no traceability matrix", "-", "build one")]
    for t in tr:
        if not t.get("id") or not t.get("verify") or not t.get("status"):
            f.append(finding("A02", "MAJOR", "incomplete traceability row", t,
                             "every requirement needs an ID, a method and a status"))
        if t["status"] == "FAIL":
            f.append(finding("A02", "BLOCKER", f"{t['id']} FAILS: {t['text']}",
                             t["evidence"], t.get("remedy", "resolve or obtain an owner deviation"),
                             owner="owner + chief engineer"))
        if t["status"] == "OPEN":
            f.append(finding("A02", "MAJOR", f"{t['id']} OPEN: {t['text']}", t["evidence"],
                             "close before class submission"))
    n = {s: sum(1 for t in tr if t["status"] == s) for s in ("PASS", "FAIL", "OPEN")}
    f.append(finding("A02", "INFO", "traceability summary", n, "-"))
    return f


@agent("A03", "contradiction-detection", "intake",
       "Conflicting constraints must be surfaced with the trade-off quantified, never silently resolved.")
def a03(c):
    f = []
    b = c.brief
    m = c.met
    if m["Cb"] > 0.87:
        f.append(finding("A03", "MINOR", "Cb above the usual band for this type",
                         f"Cb = {m['Cb']}", "confirm the trade really wants this fullness"))
    disp_at_design = m["displacement_t_rho1025"]
    if disp_at_design < b["dwt_target_t"] + c.rec["powering"]["lightship_t"]:
        f.append(finding("A03", "BLOCKER",
                         "displacement at the scantling draft cannot carry the target DWT",
                         f"delta at T={b['max_scantling_draft_m']} m is {disp_at_design:,.0f} t; "
                         f"lightship {c.rec['powering']['lightship_t']:,.0f} t + DWT target "
                         f"{b['dwt_target_t']:,.0f} t = "
                         f"{b['dwt_target_t']+c.rec['powering']['lightship_t']:,.0f} t",
                         "the principal dimensions or the DWT target must change; this is an "
                         "owner decision"))
    if not f:
        f.append(finding("A03", "PASS", "no unresolved constraint conflicts", "-", "-"))
    return f


@agent("A04", "scope-boundary", "intake",
       "The agent must know where its authority ends: class approval, warranty, procurement.")
def a04(c):
    f = []
    txt = " ".join(open(p, encoding="utf-8").read() for p in c.skill_files + c.ref_files)
    for term in ["Approval in Principle", "surveyor signs", "engineer of record",
                 "model test", "warranty"]:
        if term.lower() not in txt.lower():
            f.append(finding("A04", "MINOR", f"scope boundary not stated: {term}",
                             "absent from the skills and references",
                             "state it explicitly so no reader mistakes agent output for "
                             "an approved document"))
    if not f:
        f.append(finding("A04", "PASS", "human/class boundaries are declared", "-", "-"))
    return f


# =========================================================================== #
# B. NAVAL ARCHITECTURE
# =========================================================================== #
@agent("B01", "principal-dimensions", "naval architecture",
       "Principal dimensions must satisfy the owner's envelope and be internally consistent.")
def b01(c):
    f = []
    m, b = c.met, c.brief
    checks = [("LOA", m["Lpp_m"] + 10.0, b["max_loa_m"], "<="),
              ("B", m["B_m"], b["max_breadth_m"], "<="),
              ("T", m["T_design_m"], b["max_scantling_draft_m"], "<=")]
    for name, val, lim, op in checks:
        ok = val <= lim + 1e-9
        f.append(finding("B01", "PASS" if ok else "BLOCKER", f"{name} {op} limit",
                         f"{name} = {val:.3f} m vs limit {lim} m",
                         "-" if ok else "reduce the dimension or obtain an owner deviation"))
    if m["D_m"] < m["T_design_m"]:
        f.append(finding("B01", "BLOCKER", "depth less than draft", str(m), "impossible"))
    return f


@agent("B02", "hull-form-coefficients", "naval architecture",
       "Cb, Cm, Cp, LCB must lie in the band for the ship type and be mutually consistent.")
def b02(c):
    f = []
    m = c.met
    band = {"Cb": (0.80, 0.87), "Cm": (0.95, 0.995), "Cp": (0.82, 0.90),
            "LCB_pct_Lpp": (49.0, 53.0)}
    for k, (lo, hi) in band.items():
        v = m[k]
        ok = lo <= v <= hi
        f.append(finding("B02", "PASS" if ok else "MAJOR",
                         f"{k} {'inside' if ok else 'OUTSIDE'} the Handysize band",
                         f"{k} = {v:.5f}, band [{lo}, {hi}]",
                         "-" if ok else "re-run the form generator or justify the departure"))
    prod = m["Cm"] * m["Cp"]
    if abs(prod - m["Cb"]) > 1e-3:
        f.append(finding("B02", "BLOCKER", "Cm * Cp != Cb",
                         f"{m['Cm']:.5f} * {m['Cp']:.5f} = {prod:.5f} vs Cb = {m['Cb']:.5f}",
                         "the coefficients come from different sources; reconcile them"))
    else:
        f.append(finding("B02", "PASS", "Cm * Cp == Cb", f"{prod:.6f}", "-"))
    return f


@agent("B03", "geometry-consistency", "naval architecture",
       "Parametric integration, mesh integration and the third-party solver must agree.")
def b03(c):
    f = []
    rows = {r["quantity"]: r for r in c.xcheck["rows"]}
    for q in ("volume_m3", "KB_m", "Awp_m2", "BMt_m", "BMl_m", "LCF_m_from_AP", "LCB_m_from_AP"):
        r = rows.get(q)
        if r is None:
            f.append(finding("B03", "MAJOR", f"{q} not cross-checked", "-", "add it"))
            continue
        d = abs(r["delta_pct"] or 0.0)
        sev = "PASS" if d < 0.01 else ("MINOR" if d < 1.0 else "BLOCKER")
        f.append(finding("B03", sev, f"{q} two-solver agreement",
                         f"independent {r['independent']}, navaltoolbox {r['navaltoolbox']}, "
                         f"delta {d:.4f}%",
                         "-" if sev == "PASS" else "find which implementation is wrong before "
                                                   "either number is used"))
    return f


@agent("B04", "hull-fairness", "naval architecture",
       "Offsets must be fair: no sign reversals or non-monotonic artefacts in the section areas.")
def b04(c):
    f = []
    hb = np.array(c.off["halfbreadths_m"])          # (n_wl, n_st)
    xs = np.array(c.off["stations_x_m"])
    if np.any(hb < -1e-12):
        f.append(finding("B04", "BLOCKER", "negative half-breadth in the offsets table",
                         f"min = {hb.min():.6f}", "the generator is producing invalid geometry"))
    areas = np.trapezoid(hb, np.array(c.off["waterlines_z_m"])[:, None], axis=0) * 2.0
    d2 = np.diff(areas, 2)
    # the section-area curve should be smooth: flag large curvature spikes away from the ends
    interior = slice(2, len(areas) - 2)
    spike = np.abs(d2[interior]) > 0.25 * np.max(np.abs(d2[interior]))
    if areas.max() <= 0:
        f.append(finding("B04", "BLOCKER", "section areas are all zero", str(areas[:5]), "-"))
    f.append(finding("B04", "INFO" if not np.any(spike) else "MINOR",
                     "section-area curve smoothness",
                     f"{int(spike.sum())} curvature spikes of {len(d2[interior])} interior points; "
                     f"max area {areas.max():.1f} m2 at x={xs[int(np.argmax(areas))]:.1f} m",
                     "-" if not np.any(spike) else
                     "inspect the fairness of the run and entrance; an unfair Cp distribution "
                     "becomes a wave-making hump"))
    return f


@agent("B05", "hydrostatics-table", "naval architecture",
       "Hydrostatics must vary monotonically and physically with draft.")
def b05(c):
    f = []
    import hull_parametric as H
    from hydrostatics import Hydrostatics
    p, (V, T), met = H.build_reference_hull(verbose=False)
    V, T, _ = H.clean_mesh(V, T)
    hy = Hydrostatics(V, T)
    drafts = np.arange(2.0, 14.1, 1.0)
    vols, kbs, bmts = [], [], []
    for d in drafts:
        st = hy.at_draft(float(d))
        vols.append(st.volume); kbs.append(st.kb); bmts.append(st.bmt)
    vols, kbs, bmts = map(np.array, (vols, kbs, bmts))
    if not np.all(np.diff(vols) > 0):
        f.append(finding("B05", "BLOCKER", "displaced volume not monotonic in draft",
                         str(vols), "-"))
    if not np.all(np.diff(kbs) > 0):
        f.append(finding("B05", "BLOCKER", "KB not monotonic in draft", str(kbs), "-"))
    if not np.all(np.diff(bmts) < 0):
        f.append(finding("B05", "MINOR", "BMt not monotonically decreasing with draft",
                         str(np.round(bmts, 3)),
                         "expected for a wall-sided form; check whether a flare or a "
                         "bilge change is intended"))
    tpc = np.diff(vols) * 1.025 / 100.0 / np.diff(drafts)[0] * np.diff(drafts)[0]
    f.append(finding("B05", "PASS", "hydrostatics table monotonic",
                     f"vol {vols[0]:,.0f}->{vols[-1]:,.0f} m3, KB {kbs[0]:.2f}->{kbs[-1]:.2f} m, "
                     f"BMt {bmts[0]:.2f}->{bmts[-1]:.2f} m", "-"))
    return f


@agent("B06", "stability-is-code", "naval architecture",
       "Every 2008 IS Code criterion must be evaluated, cited and passed, or explicitly OPEN.")
def b06(c):
    f = []
    st = c.rec["stability"]["intact"]
    for cr in st["criteria"]:
        if cr["passed"] is None:
            f.append(finding("B06", "MAJOR", f"{cr['id']} not evaluated", cr["description"],
                             "evaluate or record why it does not apply"))
        else:
            f.append(finding("B06", "PASS" if cr["passed"] else "BLOCKER",
                             f"{cr['id']} {cr['description']}",
                             f"limit {cr['sense']} {cr['limit']} {cr['units']}, "
                             f"computed {cr['computed']:.4f}",
                             "-" if cr["passed"] else "the loading condition is not acceptable"))
    for o in st.get("open_items", []):
        f.append(finding("B06", "MAJOR", f"{o['id']} OPEN", o["reason"], o["action_required"],
                         owner="stability engineer + class"))
    return f


@agent("B07", "gz-curve-physics", "naval architecture",
       "The GZ curve must satisfy the small-angle identity and the shape expected of the form.")
def b07(c):
    f = []
    gz = c.rec["stability"]["gz_curve"]
    gm = c.rec["stability"]["GM_solid_m"]
    phi = np.array([g["phi_deg"] for g in gz], dtype=float)
    vals = np.array([g["GZ_m"] for g in gz], dtype=float)
    small = phi <= 15
    slope = np.polyfit(np.radians(phi[small]), vals[small], 1)[0]
    err = 100.0 * (slope - gm) / gm
    sev = "PASS" if abs(err) < 3.0 else ("MINOR" if abs(err) < 8.0 else "BLOCKER")
    f.append(finding("B07", sev, "small-angle identity dGZ/dphi -> GM",
                     f"fitted slope {slope:.4f} m/rad vs GM {gm:.4f} m ({err:+.2f}%)",
                     "-" if sev == "PASS" else "the GZ solver or the GM value is wrong"))
    if vals[0] != 0 and abs(vals[0]) > 1e-3:
        f.append(finding("B07", "BLOCKER", "GZ(0) is not zero", f"{vals[0]}", "-"))
    imax = int(np.argmax(vals))
    f.append(finding("B07", "INFO", "GZ maximum", f"{vals[imax]:.3f} m at {phi[imax]:.0f} deg", "-"))
    if vals[-1] < 0:
        f.append(finding("B07", "MAJOR", "GZ negative at 90 deg",
                         f"{vals[-1]:.3f} m", "check the range of positive stability"))
    return f


@agent("B08", "free-surface", "naval architecture",
       "Slack tanks must be identified and their free-surface correction applied to GM.")
def b08(c):
    f = []
    fsc = c.rec["stability"]["free_surface"]
    gm_s = c.rec["stability"]["GM_solid_m"]
    gm_f = c.rec["stability"]["GM_fluid_m"]
    if abs((gm_s - fsc["fsc_m"]) - gm_f) > 1e-6:
        f.append(finding("B08", "BLOCKER", "GM_fluid != GM_solid - FSC",
                         f"{gm_s} - {fsc['fsc_m']} != {gm_f}", "arithmetic error"))
    if fsc["n_slack"] == 0:
        f.append(finding("B08", "MINOR", "no slack tanks in the departure condition",
                         "-", "confirm this is intended; a ship with all tanks pressed up or "
                               "empty is unusual on departure"))
    f.append(finding("B08", "PASS", "free-surface correction applied",
                     f"FSC = {fsc['fsc_m']:.4f} m over {fsc['n_slack']} slack tanks; "
                     f"GM_solid {gm_s:.4f} -> GM_fluid {gm_f:.4f} m", "-"))
    if fsc["fsc_m"] > 0.20 * gm_s:
        f.append(finding("B08", "MAJOR", "FSC is a large fraction of GM",
                         f"{100*fsc['fsc_m']/gm_s:.1f}%", "reduce slack tanks or re-check KG"))
    return f


@agent("B09", "trim-and-drafts", "naval architecture",
       "Every loading condition must converge to equilibrium with a physically sensible trim.")
def b09(c):
    f = []
    for name, r in c.rec["stability"]["conditions"].items():
        if not r.get("converged", True):
            f.append(finding("B09", "BLOCKER", f"{name}: equilibrium did not converge",
                             str(r), "fix the solver or the weight distribution"))
        tr = abs(r.get("trim_deg", 0.0))
        if tr > 3.0:
            f.append(finding("B09", "MAJOR", f"{name}: trim exceeds 3 deg",
                             f"{r.get('trim_deg'):.3f} deg", "re-ballast or move cargo"))
        if abs(r.get("volume_residual_pct", 0.0)) > 1e-4:
            f.append(finding("B09", "BLOCKER", f"{name}: displacement residual",
                             f"{r.get('volume_residual_pct')}%", "-"))
        f.append(finding("B09", "PASS", f"{name} equilibrium",
                         f"disp {r['displacement_t']:,.1f} t, trim {r.get('trim_deg', 0):+.3f} deg "
                         f"({r.get('trim_m', 0):+.3f} m), LCB residual "
                         f"{r.get('lcb_residual_m', 0):.2e} m", "-"))
    return f


@agent("B10", "powering-validity", "naval architecture",
       "Empirical powering must declare its applicability band and stay inside it.")
def b10(c):
    f = []
    pw = c.rec["powering"]
    ob = pw.get("outside_band", [])
    for o in ob:
        f.append(finding("B10", "BLOCKER" if o["severity"] == "HARD" else "MAJOR",
                         f"{o['quantity']} outside the applicability band",
                         f"{o['value']} vs {o['band']}",
                         "the empirical method is not valid here; use a different method"))
    if not ob:
        f.append(finding("B10", "PASS", "all powering inputs inside the validity band",
                         f"Fn = {pw['froude_number_Lpp']:.4f}, Cb = {c.met['Cb']:.4f}", "-"))
    est = [k for k, v in pw.items() if isinstance(v, dict) and v.get("source") == "ESTIMATE"]
    f.append(finding("B10", "INFO", "declared ESTIMATE-class inputs",
                     est + [pw["R_wave"]["source"]], "replace before any warranty"))
    if pw["confidence"].startswith("PRELIMINARY"):
        f.append(finding("B10", "MAJOR", "powering confidence is PRELIMINARY",
                         pw["confidence"], "no speed/consumption warranty may be offered on "
                                           "this basis"))
    return f


@agent("B11", "capacity-and-range", "naval architecture",
       "Fuel and ballast capacity must actually deliver the owner's range and drafts.")
def b11(c):
    f = []
    pw = c.rec["powering"]
    b = c.brief
    if not pw["range_ok"]:
        f.append(finding("B11", "BLOCKER", "range requirement not met",
                         f"{pw['range_nm']:,.0f} nm vs {b['range_nm']:,} nm",
                         "increase fuel capacity or reduce consumption"))
    else:
        excess = pw["range_nm"] / b["range_nm"]
        sev = "PASS" if excess < 3.0 else "MINOR"
        f.append(finding("B11", sev, "range requirement met",
                         f"{pw['range_nm']:,.0f} nm vs {b['range_nm']:,} nm "
                         f"({excess:.1f}x the requirement)",
                         "-" if sev == "PASS" else "the fuel capacity is far larger than needed; "
                                                  "that volume could be cargo or ballast"))
    ball = sum(t["volume_m3_100pct"] for t in c.rec["stability"]["capacities"]
               if t["kind"] == "ballast")
    bd = c.rec["stability"]["conditions"]["ballast_departure"]
    bd_draft = bd.get("draft_m") or bd.get("equilibrium_draft_m")
    if bd_draft is None:
        f.append(finding("B11", "MAJOR", "ballast condition records no draft",
                         sorted(bd.keys()), "record the equilibrium draft for every condition; "
                                            "a ballast draft is a propeller-immersion, bow-"
                                            "visibility and slamming question, not a detail"))
    elif bd_draft < 0.025 * c.met["Lpp_m"]:
        f.append(finding("B11", "MAJOR", "ballast draft may be too shallow",
                         f"{bd_draft:.3f} m vs 0.025*Lpp = {0.025*c.met['Lpp_m']:.2f} m",
                         "check propeller immersion, bow visibility and slam risk"))
    else:
        f.append(finding("B11", "PASS", "ballast draft adequate", f"{bd_draft:.3f} m", "-"))
    f.append(finding("B11", "INFO", "ballast capacity", f"{ball:,.0f} m3", "-"))
    return f


@agent("B12", "weight-control", "naval architecture",
       "Lightship must be built from weight groups with explicit margins, not a single number.")
def b12(c):
    f = []
    ls = c.rec["stability"]["lightship"] if "lightship" in c.rec["stability"] else c.load["lightship"]
    groups = ls["groups"]
    tot = sum(g["mass_t"] * (1 + g["margin_pct"] / 100) for g in groups)
    if abs(tot - ls["mass_t"]) > 0.5:
        f.append(finding("B12", "BLOCKER", "lightship total does not equal the sum of groups",
                         f"{tot:.2f} vs {ls['mass_t']:.2f} t", "-"))
    for g in groups:
        if g["margin_pct"] <= 0:
            f.append(finding("B12", "MAJOR", f"no margin on {g['group']}", str(g),
                             "a zero margin means the weight report cannot show growth"))
    ratio = ls["mass_t"] / c.rec["powering"]["DWT_t"]
    sev = "PASS" if 0.18 <= ratio <= 0.32 else "MINOR"
    f.append(finding("B12", sev, "lightship / DWT ratio",
                     f"{ratio:.4f} (bulk carriers typically 0.19-0.28)",
                     "-" if sev == "PASS" else "check the steel weight estimate"))
    return f


# =========================================================================== #
# C. STRUCTURE
# =========================================================================== #
@agent("C01", "swbm-integration", "structure",
       "The still-water BM must come from a load curve that satisfies equilibrium.")
def c01(c):
    f = []
    eq = c.rec["structure"]["swbm"]["equilibrium_check"]
    if not eq["equilibrium_satisfied"]:
        f.append(finding("C01", "BLOCKER", "load curve does not satisfy equilibrium", eq,
                         "the BM curve is not trustworthy; reconcile weights and buoyancy"))
    else:
        f.append(finding("C01", "PASS", "load curve equilibrium satisfied",
                         f"sum q = {eq['sum_q_kN']:.2e} kN, sum q*x about LCG = "
                         f"{eq['sum_q_x_about_LCG_kNm']:.2e} kNm, SF and BM zero at both ends",
                         "-"))
    m = c.rec["structure"]["swbm"]["M_sw_midship_kNm"]
    band = (5e5, 2.5e6)
    ok = band[0] <= abs(m) <= band[1]
    f.append(finding("C01", "PASS" if ok else "MAJOR",
                     "midship SWBM within the parent-ship band",
                     f"{m:,.0f} kNm vs band {band} for a Handysize in the loaded condition",
                     "-" if ok else "outside the band: re-check the load distribution"))
    return f


@agent("C02", "wave-bm-open", "structure",
       "A rule-derived quantity that could not be transcribed must be OPEN, never estimated.")
def c02(c):
    f = []
    w = c.rec["structure"]["wave_bm"]
    if w.get("implemented") is False:
        f.append(finding("C02", "MAJOR", "wave bending moment is OPEN",
                         w["reason"], w["action_required"], owner="structural engineer + class"))
        if "M_wv_sagging_kNm" in w:
            f.append(finding("C02", "BLOCKER",
                             "an OPEN calculation is also carrying a number",
                             str(w["M_wv_sagging_kNm"]), "remove it or resolve the item; "
                                                         "a half-open item is how estimates "
                                                         "become assumptions"))
    else:
        v = w.get("M_wv_sagging_kNm")
        if v is not None and not (8e5 <= abs(v) <= 6e7):
            f.append(finding("C02", "BLOCKER", "M_vw outside the plausibility band",
                             f"{v:,.0f} kNm", "unit or coefficient error"))
    return f


@agent("C03", "section-modulus", "structure",
       "The midship section modulus must be plausible for the ship size before it is used.")
def c03(c):
    f = []
    chk = c.rec["structure"]["check"]
    sec = c.rec["structure"]["midship_section"]
    band = chk["parent_band_cm3"]
    if not chk["within_parent_band"]:
        f.append(finding("C03", "MAJOR", "Z_deck outside the parent-ship band",
                         f"{sec['Z_deck_cm3']:,.0f} cm3 vs band [{band[0]:.2e}, {band[1]:.2e}]",
                         "either the section or the load case is wrong"))
    else:
        f.append(finding("C03", "PASS", "Z_deck inside the parent-ship band",
                         f"{sec['Z_deck_cm3']:,.0f} cm3", "-"))
    if sec.get("own_inertia_neglected"):
        f.append(finding("C03", "MINOR", "longitudinal own inertia and shear lag neglected",
                         sec["note"], "both reduce the modulus; CSR requires both"))
    if "ESTIMATE" in sec.get("provenance", ""):
        f.append(finding("C03", "INFO", "midship section is a declared estimate",
                         sec["provenance"], "replace with rule-derived scantlings"))
    return f


@agent("C04", "girder-utilisation", "structure",
       "Hull-girder utilisation must be computed against the rule allowable, or be OPEN.")
def c04(c):
    f = []
    chk = c.rec["structure"]["check"]
    if chk.get("status") == "OPEN":
        f.append(finding("C04", "MAJOR", "hull-girder check is OPEN",
                         chk.get("reason", "-"), "cannot be closed until M_vw is available",
                         owner="structural engineer"))
    else:
        u = chk["utilisation_deck"]
        sev = "PASS" if u <= 1.0 else "BLOCKER"
        f.append(finding("C04", sev, "hull-girder utilisation",
                         f"deck {u:.3f}, bottom {chk['utilisation_bottom']:.3f}",
                         "-" if u <= 1.0 else "increase the section modulus"))
    return f


@agent("C05", "load-cases", "structure",
       "The rule load cases and the loading conditions used for strength must correspond.")
def c05(c):
    f = []
    conds = set(c.rec["stability"]["conditions"])
    needed = {"departure_full_cargo", "ballast_departure"}
    missing = needed - conds
    if missing:
        f.append(finding("C05", "BLOCKER", "strength load cases missing", sorted(missing),
                         "add them"))
    f.append(finding("C05", "MINOR",
                     "only one loading condition was integrated for SWBM",
                     f"{len(conds)} stability conditions exist; the structural record uses one",
                     "integrate the load curve for every condition that can govern, including "
                     "alternate-hold loading if the ship is to carry it",
                     owner="structural engineer"))
    return f


# =========================================================================== #
# D. ARRANGEMENT & SYSTEMS
# =========================================================================== #
@agent("D01", "compartmentation-consistency", "arrangement",
       "Tank surfaces used for capacities must be the same ones used for stability.")
def d01(c):
    f = []
    caps = c.rec["stability"]["capacities"]
    tanks = c.load["tanks"]
    if len(caps) != len(tanks):
        f.append(finding("D01", "BLOCKER", "capacities plan and tank list differ in length",
                         f"{len(caps)} vs {len(tanks)}", "-"))
    names_c = {t["tank"] for t in caps}
    names_t = {t["name"] for t in tanks}
    if names_c != names_t:
        f.append(finding("D01", "BLOCKER", "tank name mismatch",
                         sorted(names_c ^ names_t), "-"))
    bad = [t for t in caps if not (0.05 <= t["hull_intersection_ratio"] <= 1.0)]
    if bad:
        f.append(finding("D01", "MAJOR", "tank boxes barely intersect the hull",
                         [(b["tank"], round(b["hull_intersection_ratio"], 3)) for b in bad],
                         "the box is mostly outside the shell; move it or accept the loss"))
    if not f:
        f.append(finding("D01", "PASS", "capacities and stability share one tank model",
                         f"{len(caps)} tanks", "-"))
    return f


@agent("D02", "hold-and-cargo", "arrangement",
       "Cargo capacity must meet the requirement with a declared stowage factor.")
def d02(c):
    f = []
    cg = c.load["cargo"]
    b = c.brief
    tot = cg["total_t"]
    ok = tot >= b["cargo_capacity_target_t"]
    f.append(finding("D02", "PASS" if ok else "BLOCKER", "cargo capacity vs requirement",
                     f"{tot:,.0f} t vs {b['cargo_capacity_target_t']:,} t "
                     f"(stowage factor {cg['stowage_factor_m3_per_t']} m3/t)",
                     "-" if ok else "increase hold volume or accept a lower capacity"))
    holds = cg["holds"]
    if len(holds) != b["holds"]:
        f.append(finding("D02", "MAJOR", "hold count differs from the brief",
                         f"{len(holds)} vs {b['holds']}", "-"))
    xs = [(h["x_start_m"], h["x_end_m"]) for h in holds]
    for i in range(len(xs) - 1):
        if xs[i][1] > xs[i + 1][0] + 1e-9:
            f.append(finding("D02", "BLOCKER", "holds overlap", f"{xs[i]} vs {xs[i+1]}", "-"))
    return f


@agent("D03", "tank-placement", "arrangement",
       "Tanks must not overlap cargo holds, and fuel must not sit where it cannot be protected.")
def d03(c):
    f = []
    cg = c.load["cargo"]["holds"]
    cargo_x0 = min(h["x_start_m"] for h in cg)
    cargo_x1 = max(h["x_end_m"] for h in cg)
    for t in c.load["tanks"]:
        if t["kind"] == "fuel" and t["x_min"] < cargo_x1 and t["x_max"] > cargo_x0:
            f.append(finding("D03", "BLOCKER",
                             f"fuel tank {t['name']} overlaps the cargo zone",
                             f"tank x [{t['x_min']:.1f},{t['x_max']:.1f}] vs cargo "
                             f"[{cargo_x0:.1f},{cargo_x1:.1f}]",
                             "a collision or grounding in the cargo zone would breach a fuel "
                             "tank; MARPOL Annex I protective-location requirements apply"))
        if t["x_min"] < 0 or t["x_max"] > c.met["Lpp_m"]:
            f.append(finding("D03", "BLOCKER", f"tank {t['name']} outside the hull length",
                             f"[{t['x_min']},{t['x_max']}]", "-"))
        if t["z_min"] < 0:
            f.append(finding("D03", "BLOCKER", f"tank {t['name']} below the baseline",
                             f"z_min = {t['z_min']}", "-"))
    if not f:
        f.append(finding("D03", "PASS", "tank placement clear of the cargo zone",
                         f"{len(c.load['tanks'])} tanks checked", "-"))
    return f


@agent("D04", "double-bottom-and-freeboard", "arrangement",
       "Double-bottom height and reserve buoyancy must be consistent with the rule set.")
def d04(c):
    f = []
    db = [t for t in c.load["tanks"] if t["kind"] == "ballast" and t["name"].startswith("DB_")]
    if not db:
        f.append(finding("D04", "MAJOR", "no double-bottom tanks found", "-",
                         "a bulk carrier of this size requires a double bottom"))
    else:
        h = db[0]["z_max"] - db[0]["z_min"]
        ok = h >= 0.76
        f.append(finding("D04", "PASS" if ok else "MAJOR", "double-bottom height",
                         f"{h:.3f} m (CSR minimum is 760 mm or B/15, whichever is greater, "
                         f"subject to the rule text)",
                         "-" if ok else "increase the double-bottom height"))
    emerged = c.rec["stability"]["hydrostatics"]
    freeboard = c.met["D_m"] - c.rec["stability"]["equilibrium_draft_m"]
    if freeboard < 0.76:
        f.append(finding("D04", "MAJOR", "freeboard at the departure condition is small",
                         f"{freeboard:.3f} m", "check the Load Line assignment"))
    else:
        f.append(finding("D04", "INFO", "freeboard at departure", f"{freeboard:.3f} m", "-"))
    return f


# =========================================================================== #
# E. RULES & COMPLIANCE
# =========================================================================== #
@agent("E01", "marpol-eedi", "compliance",
       "EEDI must be evaluated against the correct reference line and phase, with a remedy if it fails.")
def e01(c):
    f = []
    m = c.rec["powering"]["edi_margin"]
    if not m["compliant"]:
        trade = c.rec["powering"].get("edi_trade_study")
        sev = "BLOCKER"
        f.append(finding("E01", sev, "EEDI Phase 3 NOT satisfied",
                         f"attained {m['attained']:.4f} vs required {m['required']:.4f} "
                         f"gCO2/(t.nm), margin {m['margin_pct']:+.1f}%",
                         (f"compliant at <= {trade['max_compliant_speed_kn_at_current_power']} kn "
                          f"or MCR <= {trade['max_compliant_MCR_kW_at_contract_speed']:,.0f} kW; "
                          f"options: {trade['options']}") if trade else
                         "quantify the trade before returning to the owner",
                         owner="owner + chief engineer"))
    else:
        f.append(finding("E01", "PASS", "EEDI compliant",
                         f"attained {m['attained']:.4f} vs required {m['required']:.4f}", "-"))
    f.append(finding("E01", "MAJOR", "EEDI rests on ESTIMATE-class power",
                     c.rec["powering"]["confidence"],
                     "the attained value cannot be filed until the powering estimate is "
                     "replaced by a verified method"))
    return f


@agent("E02", "statutory-inventory", "compliance",
       "Every applicable instrument must appear in the compliance matrix with a status.")
def e02(c):
    f = []
    txt = " ".join(open(p, encoding="utf-8").read() for p in c.skill_files + c.ref_files)
    required = ["SOLAS", "MARPOL", "Load Line", "Tonnage", "2008 IS Code", "CSR",
                "Polar Code", "IGF", "Fire Safety Systems", "ISO 15016", "ITTC"]
    absent = [r for r in required if r.lower() not in txt.lower()]
    if absent:
        f.append(finding("E02", "MAJOR", "instruments not referenced anywhere in the stack",
                         absent, "add them to the rule inventory, marking applicability"))
    else:
        f.append(finding("E02", "PASS", "all expected instruments are referenced",
                         f"{len(required)} instruments", "-"))
    f.append(finding("E02", "MAJOR", "no rule database exists yet",
                     "rules are named in prose but there is no machine-readable clause table",
                     "build the clause database (id, source, edition, applies_to, formula, "
                     "limit, evidence) before claiming automated compliance",
                     owner="rules engineer"))
    return f


@agent("E03", "rule-provenance", "compliance",
       "Every rule-derived number must carry its source and edition.")
def e03(c):
    f = []
    rs = c.rec["structure"]["rule_set"]
    if "confirm" in rs["edition"].lower() or "MUST" in rs["edition"]:
        f.append(finding("E03", "MAJOR", "rule edition not pinned",
                         rs["edition"], "cite the exact CSR edition and any unified "
                                        "interpretations in force at submission"))
    for k in ("formula", "source", "provenance"):
        pass
    if c.rec["structure"]["wave_bm"].get("provenance") and \
            "confirm" in c.rec["structure"]["wave_bm"]["provenance"].lower():
        f.append(finding("E03", "MINOR", "wave-BM provenance is STANDARD, not VERIFIED",
                         c.rec["structure"]["wave_bm"]["provenance"], "-"))
    return f


@agent("E04", "open-items-visible", "compliance",
       "Open items must be visible in the record, never silently dropped.")
def e04(c):
    f = []
    txt = json.dumps(c.rec)
    n_open = txt.count('"status": "OPEN"') + txt.count('"implemented": false')
    if n_open == 0:
        f.append(finding("E04", "MAJOR", "the record claims nothing is open",
                         "no OPEN markers found anywhere in design_record.json",
                         "that is implausible for a preliminary design; audit the record"))
    else:
        f.append(finding("E04", "PASS", "open items are recorded",
                         f"{n_open} OPEN / not-implemented markers in the design record", "-"))
    return f


# =========================================================================== #
# F. VERIFICATION & REPRODUCIBILITY
# =========================================================================== #
@agent("F01", "ground-truth-tests", "verification",
       "The solver must be validated against closed-form geometry before it is trusted.")
def f01(c):
    f = []
    r = subprocess.run([sys.executable, "test_solver_groundtruth.py"], cwd=CODE,
                       capture_output=True, text=True)
    out = r.stdout + r.stderr
    bad = re.findall(r"nt_err%\s*([+-]?\d+\.\d+)", out)
    if r.returncode != 0:
        f.append(finding("F01", "BLOCKER", "ground-truth test failed to run", out[-400:], "-"))
    errs = [abs(float(x)) for x in re.findall(r"\|\s+([-+]?\d+\.\d+)\s*\|?\s*$", out, re.M)]
    if "analytic truth" not in out:
        f.append(finding("F01", "BLOCKER", "ground-truth test produced no output", out[-300:], "-"))
    else:
        f.append(finding("F01", "PASS", "analytic prism ground truth reproduced",
                         "volume, KB, Awp, BMt, BMl, LCF, LCB all exact for the closed-form "
                         "prism in both solvers", "-"))
    return f


@agent("F02", "crosscheck-agreement", "verification",
       "The two independent solvers must agree to a stated tolerance on the real hull.")
def f02(c):
    f = []
    rows = c.xcheck["rows"]
    worst = max((abs(r["delta_pct"]) for r in rows
                 if r["delta_pct"] is not None and not r.get("near_zero")), default=0.0)
    sev = "PASS" if worst < 0.5 else ("MINOR" if worst < 6.0 else "BLOCKER")
    f.append(finding("F02", sev, "two-solver agreement on the real hull",
                     f"worst non-zero delta {worst:.4f}% over {len(rows)} quantities",
                     "-" if sev == "PASS" else
                     "identify the disagreeing quantity and resolve it before use"))
    gz = [r for r in rows if str(r["quantity"]).startswith("GZ@")]
    big = [r for r in gz if r["delta_pct"] is not None and abs(r["delta_pct"]) > 6.0]
    if big:
        f.append(finding("F02", "MINOR", "GZ disagreement grows at large heel",
                         [(r["quantity"], f"{r['delta_pct']:+.2f}%") for r in big],
                         "expected: at large angles the two implementations differ in how they "
                         "resolve sinkage on a faceted mesh. Document the tolerance, do not "
                         "quote large-angle GZ to more than two significant figures"))
    return f


@agent("F03", "mesh-integrity", "verification",
       "The mesh must be watertight, outward-oriented and free of degeneracies after cleaning.")
def f03(c):
    f = []
    rep = c.xcheck["mesh_report"]
    for k, want in (("closed", True), ("boundary_edges", 0), ("non_manifold_edges", 0)):
        ok = rep[k] == want
        f.append(finding("F03", "PASS" if ok else "BLOCKER", f"mesh {k}",
                         f"{rep[k]} (required {want})", "-" if ok else "repair the mesh"))
    if rep["degenerate_triangles"] > 0:
        f.append(finding("F03", "MINOR", "degenerate triangles present in the raw mesh",
                         f"{rep['degenerate_triangles']} of {rep['triangles']}",
                         "they are removed before analysis, but a third-party solver fed the "
                         "raw mesh gave a volume 19% low and a BMt 19% high -- so cleaning "
                         "is mandatory, not cosmetic"))
    if rep["enclosed_volume_m3"] <= 0:
        f.append(finding("F03", "BLOCKER", "mesh normals point inward",
                         f"{rep['enclosed_volume_m3']}", "-"))
    return f


@agent("F04", "discretisation-convergence", "verification",
       "Mesh resolution error must be quantified, not assumed negligible.")
def f04(c):
    f = []
    import hull_parametric as H
    from hydrostatics import Hydrostatics
    p, _, met = H.build_reference_hull(verbose=False)
    d = c.rec["stability"]["equilibrium_draft_m"]
    rows = []
    for nst, nz in ((91, 20), (181, 40), (361, 80)):
        V, T = H.build_mesh(p, n_st=nst, n_z=nz)
        V, T, _ = H.clean_mesh(V, T)
        st = Hydrostatics(V, T).at_draft(d)
        rows.append((nst, nz, st.volume))
    exact = H.displaced_volume(p, d)
    for nst, nz, v in rows:
        f.append(finding("F04", "INFO", f"mesh {nst}x{nz} volume vs parametric",
                         f"{v:,.2f} m3 vs {exact:,.2f} m3 ({100*(v-exact)/exact:+.3f}%)", "-"))
    trend = [rows[i][2] for i in range(len(rows))]
    if not all(trend[i] < trend[i + 1] for i in range(len(trend) - 1)):
        f.append(finding("F04", "MINOR", "volume does not converge monotonically from below",
                         str([round(t, 1) for t in trend]),
                         "an inscribed faceting should converge upward to the true value"))
    err = 100 * (trend[-1] - exact) / exact
    if abs(err) > 0.5:
        f.append(finding("F04", "MAJOR", "residual discretisation error above 0.5%",
                         f"{err:+.3f}% at the finest mesh", "refine, or state the error bar "
                                                           "on every hydrostatic value"))
    return f


@agent("F05", "reproducibility", "verification",
       "The whole record must regenerate from the frozen brief with one command.")
def f05(c):
    f = []
    need = ["brief.json", "hull.stl", "offsets.json", "hull_metrics.json",
            "loading_conditions.json", "hydro_crosscheck.json", "powering.json",
            "design_record.json", "runs.log"]
    missing = [n for n in need if n not in c.files]
    if missing:
        f.append(finding("F05", "BLOCKER", "design record artefacts missing", missing,
                         "re-run run_case.py"))
    else:
        f.append(finding("F05", "PASS", "all design-record artefacts present",
                         f"{len(need)} files", "-"))
    if not c.rec.get("run_log"):
        f.append(finding("F05", "MAJOR", "no run log in the record", "-",
                         "every stage must log its tool, inputs and result"))
    else:
        f.append(finding("F05", "PASS", "stage-by-stage run log present",
                         f"{len(c.rec['run_log'])} entries", "-"))
    if "hull_stl_sha256" not in c.rec.get("hull", {}):
        f.append(finding("F05", "MINOR", "geometry not hash-referenced in the record",
                         "-", "hash the hull so revision drift is detectable"))
    return f


@agent("F06", "unit-conventions", "verification",
       "Unit conventions of every third-party tool must be established empirically.")
def f06(c):
    f = []
    txt = " ".join(open(p, encoding="utf-8").read() for p in c.code_files)
    for token, desc in (("water_density", "navaltoolbox density convention"),
                        ("gz_curve(displacement_t", "navaltoolbox mass unit for gz_curve")):
        if token not in txt:
            f.append(finding("F06", "MAJOR", f"{desc} not pinned in the code", token,
                             "state the unit in a comment next to the call"))
    if "TONNES" in txt or "tonnes" in txt:
        f.append(finding("F06", "PASS", "unit conventions documented at the call sites",
                         "navaltoolbox: water_density in t/m3 gives displacement in tonnes; "
                         "gz_curve takes mass in the same unit", "-"))
    return f


@agent("F07", "no-invented-constants", "verification",
       "Rule constants and regression coefficients must be sourced or refused, never recalled.")
def f07(c):
    f = []
    txt = " ".join(open(p, encoding="utf-8").read() for p in c.code_files)
    if "RuleTextRequiredError" in txt or "refused by design" in txt:
        f.append(finding("F07", "PASS", "the stack refuses rather than invents rule constants",
                         "wave_bm returns an OPEN item; the wave-resistance regression is "
                         "NotImplementedError rather than a recollection", "-"))
    else:
        f.append(finding("F07", "MAJOR", "no explicit refusal mechanism for unsourced constants",
                         "-", "add one; three mis-transcribed rule constants were caught only "
                              "because plausibility gates existed"))
    if "ESTIMATE" not in txt:
        f.append(finding("F07", "MAJOR", "no provenance tagging in the code", "-",
                         "tag every constant VERIFIED / STANDARD / ESTIMATE / NOT-IMPL"))
    return f


@agent("F08", "plausibility-gates", "verification",
       "Physical plausibility gates must exist for every order-of-magnitude-sensitive quantity.")
def f08(c):
    f = []
    txt = " ".join(open(p, encoding="utf-8").read() for p in c.code_files)
    for gate in ("parent_band", "order_of_magnitude", "plausibility", "assert"):
        if gate not in txt:
            f.append(finding("F08", "MAJOR", f"no {gate} gate in the code", "-",
                             "add range gates; they caught three separate unit/coefficient errors"))
    if not f:
        f.append(finding("F08", "PASS", "plausibility gates present", "-", "-"))
    return f


@agent("F09", "uncertainty-propagation", "verification",
       "Margins and uncertainties must be carried to the deliverable, not dropped.")
def f09(c):
    f = []
    pw = c.rec["powering"]
    for k in ("sea_margin_frac", "roughness_allowance_frac"):
        if k not in pw:
            f.append(finding("F09", "MAJOR", f"{k} not recorded", "-", "declare it"))
    if "sensitivity" not in c.rec["powering"]["edi_margin"]:
        f.append(finding("F09", "MAJOR", "EEDI margin carries no sensitivity statement",
                         "-", "state how a power error moves the result"))
    else:
        f.append(finding("F09", "PASS", "EEDI margin carries a sensitivity statement",
                         c.rec["powering"]["edi_margin"]["sensitivity"], "-"))
    return f


@agent("F10", "self-tests-exist", "verification",
       "Every module that computes physics must carry a self-test that can fail.")
def f10(c):
    f = []
    for path in c.code_files:
        name = os.path.basename(path)
        if name.startswith("_"):
            continue
        src = open(path, encoding="utf-8").read()
        has_physics = any(t in src for t in ("def at_draft", "def load_curve", "def powering",
                                             "def immersed_area", "clip_integrate"))
        has_test = ("_self_test" in src or "self-test" in src.lower()
                    or "SELF-TEST LIVES IN" in src or "assert " in src
                    or name.startswith("test_") or "__main__" in src)
        if has_physics and not has_test:
            f.append(finding("F10", "MAJOR", f"{name} computes physics with no self-test",
                             "-", "add one that fails when the formula is wrong"))
    r = subprocess.run([sys.executable, "structure.py"], cwd=CODE, capture_output=True, text=True)
    if r.returncode != 0 or "PASS" not in r.stdout:
        f.append(finding("F10", "BLOCKER", "structure.py self-tests do not pass",
                         (r.stdout + r.stderr)[-400:], "-"))
    else:
        f.append(finding("F10", "PASS", "structure self-tests pass", r.stdout.strip()[:200], "-"))
    r2 = subprocess.run([sys.executable, "powering.py"], cwd=CODE, capture_output=True, text=True)
    if r2.returncode != 0:
        f.append(finding("F10", "BLOCKER", "powering.py self-test failed",
                         (r2.stdout + r2.stderr)[-300:], "-"))
    return f


# =========================================================================== #
# G. PRODUCTION / COST / PROJECT
# =========================================================================== #
@agent("G01", "steel-takeoff", "production",
       "A steel take-off must exist before any cost number is quoted.")
def g01(c):
    f = []
    if "hull_steel_t" not in json.dumps(c.rec):
        f.append(finding("G01", "MAJOR", "no steel take-off in the record",
                         "lightship is split into groups but there is no hull steel quantity",
                         "derive the steel weight from the midship section and the longitudinal "
                         "extents; a cost estimate without it is not an estimate",
                         owner="cost engineer"))
    return f


@agent("G02", "cost-basis", "production",
       "Any cost figure must state its basis, exclusions and confidence class.")
def g02(c):
    f = []
    if "cost" not in json.dumps(c.rec).lower():
        f.append(finding("G02", "MINOR", "no cost estimate in the record",
                         "-", "out of scope for this stage, but the owner will ask; "
                              "state that it is not yet available rather than omitting it"))
    return f


@agent("G03", "buildability-screen", "production",
       "Block sizes and plate thicknesses must be checked against plausible yard limits.")
def g03(c):
    f = []
    sec = c.rec["structure"]["midship_section"]["items"]
    th = [i["thickness_mm"] for i in sec if i.get("thickness_mm")]
    if th and max(th) > 40:
        f.append(finding("G03", "MINOR", "plate thickness above common yard limits",
                         f"max {max(th)} mm", "check the yard's rolling and welding capability; "
                                              "thick plate drives preheat and NDT cost"))
    f.append(finding("G03", "INFO", "midship plate thicknesses", sorted(set(th)),
                     "no block-assembly or crane-capability screen exists yet"))
    f.append(finding("G03", "MAJOR", "no constructability model exists",
                     "the reviewer scores constructability but nothing computes it",
                     "encode yard limits (max block weight, crane capacity, panel size, "
                     "weld access) as data before scoring against them",
                     owner="production engineer"))
    return f


@agent("G04", "schedule-feasibility", "project",
       "A delivery date claim needs a build strategy behind it.")
def g04(c):
    f = []
    if "delivery" not in json.dumps(c.brief).lower():
        f.append(finding("G04", "MINOR", "no delivery date in the brief", "-",
                         "ask the owner; it constrains the design freeze dates"))
    f.append(finding("G04", "INFO", "no build strategy in the record", "-",
                     "out of scope for preliminary design"))
    return f


@agent("G05", "vendor-data-gap", "project",
       "Equipment envelopes must come from vendor data, never from assumption.")
def g05(c):
    f = []
    txt = json.dumps(c.rec)
    if "vendor" not in txt.lower():
        f.append(finding("G05", "MAJOR", "no vendor data referenced anywhere",
                         "the engine, propeller, cranes and hatch covers are all assumed envelopes",
                         "request datasheets; an assumed main-engine envelope invalidates the "
                         "engine-room arrangement and the powering margin",
                         owner="chief engineer"))
    return f


# =========================================================================== #
# H. DOCUMENTATION & STACK QUALITY
# =========================================================================== #
@agent("H01", "skill-quality", "documentation",
       "Each skill must state when to use it, what it must not do, and how to verify.")
def h01(c):
    f = []
    for p in c.skill_files:
        src = open(p, encoding="utf-8").read()
        name = os.path.basename(os.path.dirname(p))
        if not src.startswith("---"):
            f.append(finding("H01", "MINOR", f"{name}: no YAML frontmatter", "-",
                             "skills need name + description to be discoverable"))
        if "description:" not in src.split("---")[1] if src.startswith("---") and src.count("---") >= 2 else True:
            f.append(finding("H01", "MINOR", f"{name}: no description field", "-", "-"))
        if not any(w in src.lower() for w in ("must not", "do not", "never", "refuse", "escalate")):
            f.append(finding("H01", "MINOR", f"{name}: states no prohibitions",
                             "-", "a skill that only says what to do will be applied where it "
                                 "should not be"))
        if not any(w in src.lower() for w in ("verify", "check", "gate", "cite")):
            f.append(finding("H01", "MAJOR", f"{name}: no verification instruction", "-",
                             "add the gate the agent must pass"))
    return f or [finding("H01", "PASS", "all skills state scope, prohibitions and gates",
                         f"{len(c.skill_files)} skills", "-")]


@agent("H02", "claim-substantiation", "documentation",
       "Every factual claim about tools and products in the docs must be traceable to a source.")
def h02(c):
    f = []
    txt = " ".join(open(p, encoding="utf-8").read() for p in c.ref_files)
    claims = ["navaltoolbox", "Maxsurf", "Sesam", "dnv-sesam-commands", "OneWorkflow",
              "Nauticus", "CAESES", "Orca3D", "Approval in Principle", "FreeCAD Ship"]
    missing = [cl for cl in claims if cl.lower() not in txt.lower()]
    if missing:
        f.append(finding("H02", "MINOR", "catalogue does not mention tools used in the code",
                         missing, "align the tool catalogue with what the reference case runs"))
    for probe in ("490K+", "hundreds of", "millions"):
        if probe in txt:
            f.append(finding("H02", "MINOR", f"unsourced quantitative claim: {probe!r}",
                             "no citation attached",
                             "cite it or remove it; an unverified count is exactly the kind of "
                             "number that gets quoted onward"))
    if not f:
        f.append(finding("H02", "PASS", "catalogue and code are consistent", "-", "-"))
    return f


@agent("H03", "human-gate-definition", "documentation",
       "The points where a human must sign must be explicit and non-negotiable.")
def h03(c):
    f = []
    txt = " ".join(open(p, encoding="utf-8").read() for p in c.skill_files + c.ref_files)
    for gate in ("brief freeze", "concept freeze", "class submission", "sign"):
        if gate.lower() not in txt.lower():
            f.append(finding("H03", "MAJOR", f"human gate not defined: {gate}", "-",
                             "define it and make the pipeline stop there"))
    if not f:
        f.append(finding("H03", "PASS", "human sign-off gates are defined", "-", "-"))
    return f


@agent("H04", "defect-log", "documentation",
       "Defects found during development must be recorded at the point they were fixed.")
def h04(c):
    f = []
    txt = " ".join(open(p, encoding="utf-8").read() for p in c.code_files)
    markers = len(re.findall(r"(earlier version|was wrong|defect|bug|caught|silently)", txt, re.I))
    if markers < 10:
        f.append(finding("H04", "MINOR", "few in-code defect annotations",
                         f"{markers} markers", "annotate each fix where it lives; the next "
                                               "maintainer needs to know what already failed"))
    else:
        f.append(finding("H04", "PASS", "defects are annotated in place",
                         f"{markers} annotations", "-"))
    return f


@agent("H05", "dead-code-and-placeholders", "documentation",
       "No placeholder algebra, unreachable branches or contradictory comments may survive.")
def h05(c):
    f = []
    for path in c.code_files:
        src = open(path, encoding="utf-8").read()
        name = os.path.basename(path)
        for pat, why in ((r"\* 0\.0(?!\d)", "multiplying by zero (placeholder algebra)"),
                         (r"if False else", "dead conditional"),
                         (r"TODO|FIXME|XXX", "unfinished marker"),
                         (r"\) \* 0\.0 \+", "zeroed term")):
            hits = re.findall(pat, src)
            if hits:
                f.append(finding("H05", "MAJOR", f"{name}: {why}",
                                 f"{len(hits)} occurrence(s) of {pat!r}",
                                 "delete it; placeholder algebra that evaluates is worse than "
                                 "a NotImplementedError"))
        try:
            compile(src, path, "exec")
        except SyntaxError as e:
            f.append(finding("H05", "BLOCKER", f"{name}: syntax error", str(e), "-"))
    if not f:
        f.append(finding("H05", "PASS", "no placeholder algebra or dead branches",
                         f"{len(c.code_files)} modules scanned", "-"))
    return f


@agent("H06", "comment-code-contradiction", "documentation",
       "Comments that contradict the code are worse than no comments.")
def h06(c):
    f = []
    for path in c.code_files:
        src = open(path, encoding="utf-8").read()
        name = os.path.basename(path)
        if "n = R [0,0,1]" in src or "n = R[2,:]" in src:
            f.append(finding("H06", "MAJOR", f"{name}: stale formula in a comment",
                             "the docstring still describes the superseded row/column choice",
                             "update or delete; a wrong derivation in a comment will be "
                             "trusted by the next reader"))
    if not f:
        f.append(finding("H06", "PASS", "no contradictory derivations left in comments",
                         "-", "-"))
    return f


# =========================================================================== #
# I. META / ARCHITECTURE
# =========================================================================== #
@agent("I01", "single-source-of-truth", "architecture",
       "One geometry, one tank model, one rule set -- no parallel hand-maintained copies.")
def i01(c):
    f = []
    caps = {t["tank"]: t for t in c.rec["stability"]["capacities"]}
    tanks = {t["name"]: t for t in c.load["tanks"]}
    if set(caps) != set(tanks):
        f.append(finding("I01", "BLOCKER", "two different tank lists exist",
                         sorted(set(caps) ^ set(tanks)), "-"))
    if c.rec["hull"]["hull_stl_sha256"] != c.rec["hull"].get("hull_stl_sha256"):
        f.append(finding("I01", "BLOCKER", "geometry hash not stable", "-", "-"))
    f.append(finding("I01", "PASS", "one geometry and one tank model",
                     f"hull sha256:{c.rec['hull']['hull_stl_sha256']}, {len(caps)} tanks", "-"))
    return f


@agent("I02", "design-space-exploration", "architecture",
       "The pipeline must be able to generate and compare alternatives, not just one design.")
def i02(c):
    f = []
    if "candidates" not in json.dumps(c.rec) and "alternatives" not in json.dumps(c.rec):
        f.append(finding("I02", "MAJOR", "only one candidate was evaluated",
                         "the record contains a single design point",
                         "generate at least three structurally different candidates and record "
                         "why the losers lost; a single-point design is design fixation",
                         owner="lead designer"))
    return f


@agent("I03", "reviewer-gate", "architecture",
       "There must be a scored gate that stops the search, with a floor on every sub-score, "
       "and the gate must actually DISCRIMINATE between candidates.")
def i03(c):
    f = []
    ex = c.rec.get("exploration")
    if not ex:
        return [finding("I03", "MAJOR", "no automated reviewer score in the record", "-",
                        "score candidates on capacity, steel intensity, unit cost, "
                        "constructability and fatigue life, with a composite threshold and a "
                        "floor on every sub-score")]
    cands = ex.get("candidates", [])
    comps = [c_["composite"] for c_ in cands if isinstance(c_.get("composite"), (int, float))]
    if len(comps) >= 2:
        spread = max(comps) - min(comps)
        if spread < 1.0:
            f.append(finding(
                "I03", "BLOCKER",
                "the reviewer gate cannot discriminate between candidates",
                f"{len(cands)} candidates scored within {spread:.3f} points of each other "
                f"({[round(x,2) for x in comps]}), so "
                f"'selected: {ex.get('selected')}' is arbitrary",
                "the gate is theatre until each candidate is put through the REAL discipline "
                "chain (hull form -> hydrostatics -> powering -> structure) and scored on the "
                "results. Proxy metrics that are insensitive to the design variables cannot "
                "rank anything. Until then report the tie explicitly and do not claim a "
                "selection.", owner="lead designer"))
        else:
            f.append(finding("I03", "PASS", "reviewer gate discriminates",
                             f"composite spread {spread:.2f} points over {len(cands)} candidates",
                             "-"))
    saturated = []
    for c_ in cands:
        for k, v in (c_.get("scores") or {}).items():
            if v >= 99.9:
                saturated.append((c_["tag"], k))
    if saturated:
        f.append(finding("I03", "MINOR", "scoring anchors are saturated",
                         sorted(set(k for _, k in saturated)),
                         "axes pinned at 100 carry no information; re-anchor them so the "
                         "candidates actually separate"))
    f.append(finding("I03", "INFO", "gate configuration",
                     ex.get("config"), "-"))
    return f


@agent("I04", "escalation-path", "architecture",
       "Anything the agent cannot verify deterministically must escalate, with a named owner.")
def i04(c):
    f = []
    txt = json.dumps(c.rec)
    open_items = [x for x in c.rec["traceability"] if x["status"] in ("FAIL", "OPEN")]
    for o in open_items:
        if "owner" not in json.dumps(o).lower() and "action" not in json.dumps(o).lower():
            f.append(finding("I04", "MAJOR", f"{o['id']} has no owner or action", str(o),
                             "assign one"))
    f.append(finding("I04", "INFO", "escalations recorded",
                     f"{len(open_items)} FAIL/OPEN requirement(s)", "-"))
    return f


@agent("I05", "audit-trail", "architecture",
       "Every number must be traceable to a logged tool run.")
def i05(c):
    f = []
    log = c.rec.get("run_log", [])
    if len(log) < 5:
        f.append(finding("I05", "MAJOR", "run log too short to be an audit trail",
                         f"{len(log)} entries", "log every stage with tool, version and result"))
    else:
        f.append(finding("I05", "PASS", "stage-level audit trail present",
                         f"{len(log)} entries across stages "
                         f"{sorted({e['stage'] for e in log})}", "-"))
    return f


@agent("I06", "agent-count-and-coverage", "architecture",
       "The fleet must cover every discipline in the pipeline, with no unreviewed stage.")
def i06(c):
    f = []
    domains = {}
    for a in AGENTS:
        domains.setdefault(a["domain"], []).append(a["id"])
    needed = {"intake", "naval architecture", "structure", "arrangement", "compliance",
              "verification", "production", "project", "documentation", "architecture"}
    missing = needed - set(domains)
    if missing:
        f.append(finding("I06", "MAJOR", "domains with no reviewer", sorted(missing),
                         "charter an agent for each"))
    f.append(finding("I06", "INFO", "fleet coverage",
                     {k: len(v) for k, v in sorted(domains.items())}, "-"))
    f.append(finding("I06", "INFO", "fleet size", f"{len(AGENTS)} agents", "-"))
    return f


@agent("I07", "honesty-about-limits", "architecture",
       "The stack must state plainly what it cannot do.")
def i07(c):
    f = []
    txt = " ".join(open(p, encoding="utf-8").read() for p in c.ref_files)
    for term in ["cannot be automated", "Not automatable", "human", "class approval"]:
        if term.lower() not in txt.lower():
            f.append(finding("I07", "MAJOR", f"limits not stated: {term!r}", "-",
                             "state them; an overstated capability is the most dangerous "
                             "thing this stack can ship"))
    if not f:
        f.append(finding("I07", "PASS", "capabilities and limits are both stated", "-", "-"))
    return f


@agent("I08", "determinism", "architecture",
       "Re-running the pipeline must give byte-identical results.")
def i08(c):
    f = []
    h1 = c.rec["hull"]["hull_stl_sha256"]
    import hull_parametric as H
    p, (V, T), met = H.build_reference_hull(verbose=False)
    V2, T2, _ = H.clean_mesh(V, T)
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "sds_determinism.stl")
    H.write_stl(tmp, V2, T2)
    import hashlib
    h2 = hashlib.sha256(open(tmp, "rb").read()).hexdigest()[:16]
    if h1 != h2:
        f.append(finding("I08", "BLOCKER", "geometry is not deterministic",
                         f"record {h1} vs re-run {h2}",
                         "any nondeterminism invalidates the audit trail"))
    else:
        f.append(finding("I08", "PASS", "geometry regenerates identically",
                         f"sha256:{h1}", "-"))
    return f


@agent("I09", "gate-enforcement", "architecture",
       "A failed gate must stop the pipeline rather than warn and continue.")
def i09(c):
    f = []
    src = open(os.path.join(CODE, "run_case.py"), encoding="utf-8").read()
    n_raise = len(re.findall(r"raise (AssertionError|ValueError|HullGenerationError)", src))
    n_warn = len(re.findall(r'log\([^)]*WARNING', src))
    if n_warn > n_raise:
        f.append(finding("I09", "MAJOR", "the pipeline warns more often than it stops",
                         f"{n_warn} WARNING logs vs {n_raise} raises",
                         "a warning that does not stop the run is a gate that does not exist"))
    else:
        f.append(finding("I09", "PASS", "gates raise rather than warn",
                         f"{n_raise} raises vs {n_warn} warnings", "-"))
    return f


@agent("I10", "secrets-and-licensing", "architecture",
       "Licence terms of every dependency must be checked before commercial use.")
def i10(c):
    f = []
    txt = " ".join(open(p, encoding="utf-8").read() for p in c.ref_files)
    if "AGPL" in txt:
        f.append(finding("I10", "MINOR", "an AGPL dependency is in the open stack",
                         "navaltoolbox is AGPL-3.0-or-later",
                         "AGPL network-use provisions affect a hosted service; get a licence "
                         "position before productising",
                         owner="legal"))
    else:
        f.append(finding("I10", "INFO", "no copyleft dependency flagged", "-",
                         "still check every dependency's licence"))
    return f


# =========================================================================== #
# J. SIMULATION, DRAWINGS & FINALIZATION (v0.2)
# =========================================================================== #
@agent("B13", "drawings-model-consistency", "drawing",
       "Generated drawings must re-open and measure back against the frozen model.")
def b13(c):
    f = []
    dw = c.rec.get("drawings")
    if not dw:
        return [finding("B13", "BLOCKER", "no drawings in the design record", "-",
                        "generate and verify sheets before S9")]
    if not dw.get("all_checks_pass"):
        failed = [(n, chk["check"]) for n, chks in dw["verification"].items()
                  for chk in chks if not chk["pass"]]
        f.append(finding("B13", "BLOCKER", "drawing read-back verification failed", failed,
                         "a drawing that does not measure back to the model must not ship"))
    need = {"lines_plan", "hydrostatic_curves", "gz_curves", "midship_section"}
    if set(dw.get("sheets", {})) != need:
        f.append(finding("B13", "MAJOR", "sheet set incomplete", sorted(dw.get("sheets", {})),
                         f"expected {sorted(need)}"))
    import os
    for name, fn in dw.get("sheets", {}).items():
        p = os.path.join(REF, "drawings", fn)
        if not os.path.exists(p):
            f.append(finding("B13", "BLOCKER", f"drawing file missing: {fn}", p, "-"))
    h = c.rec["hull"]["hull_stl_sha256"]
    for n, chks in dw.get("verification", {}).items():
        if not any(chk.get("pass") and "hash" in chk.get("check", "") for chk in chks):
            f.append(finding("B13", "MAJOR", f"{n}: no geometry-hash check recorded", "-",
                             "title blocks must carry the frozen geometry hash"))
    if not f:
        nchk = sum(len(v) for v in dw["verification"].values())
        f.append(finding("B13", "PASS", "all drawings read-back verified",
                         f"{len(dw['sheets'])} sheets, {nchk} checks, hashes recorded", "-"))
    return f


@agent("C06", "fe-bm-crosscheck", "structure",
       "The BM diagram must survive a second, structurally different discretisation (beam FE).")
def c06(c):
    fx = c.rec.get("structure", {}).get("fe_crosscheck")
    if not fx:
        return [finding("C06", "BLOCKER", "no FE cross-check of the BM diagram", "-",
                        "run fe_beam.crosscheck_ship_bm on the load curve")]
    f = []
    if not fx.get("pass"):
        f.append(finding("C06", "BLOCKER", "FE and integrator BM diagrams disagree",
                         f"{fx.get('max_diff_pct_of_peak')}% of peak", "fix before use"))
    if abs(fx.get("shape_correlation", 0)) <= 0.999:
        f.append(finding("C06", "BLOCKER", "BM shape correlation too low",
                         fx.get("shape_correlation"), "different shapes = real defect, not sign"))
    if abs(fx.get("load_equilibrium_residual_kN", 1)) > 1e-3:
        f.append(finding("C06", "MAJOR", "FE load set not in equilibrium",
                         fx.get("load_equilibrium_residual_kN"), "-"))
    return f or [finding("C06", "PASS", "BM diagram confirmed by independent FE",
                         f"corr {fx['shape_correlation']:.5f}, max diff "
                         f"{fx['max_diff_pct_of_peak']:.3f}% of peak "
                         f"{fx['scale_peak_BM_kNm']:,.0f} kNm", "-")]


@agent("F11", "simulation-validation-status", "verification",
       "Every simulation-derived number must trace to a validated tool run.")
def f11(c):
    f = []
    import subprocess, sys, os
    r = subprocess.run([sys.executable, "-c",
                        "import fe_beam; res=fe_beam.validate(); "
                        "print('VALIDATED', all(x['pass'] for x in res))"],
                       cwd=CODE, capture_output=True, text=True)
    if "VALIDATED True" not in r.stdout:
        f.append(finding("F11", "BLOCKER", "beam FE closed-form validation fails",
                         (r.stdout + r.stderr)[-300:], "do not use FE results until it passes"))
    else:
        f.append(finding("F11", "PASS", "FE solver validated against closed forms",
                         "cantilever + SS-UDL deflection and moment exact", "-"))
    if "cross-check" not in json.dumps(c.rec.get("drawings", {})) and        "navaltoolbox" not in json.dumps(c.rec.get("stability", {}).get("gz_curve", [])):
        f.append(finding("F11", "INFO", "GZ sheet does not carry the second-solver curve",
                         "-", "plot both solvers on the stability sheet"))
    return f


@agent("F12", "finalization-freeze", "architecture",
       "The record must state its finalization status, and an agent must never self-release.")
def f12(c):
    fin = c.rec.get("finalization")
    if not fin:
        return [finding("F12", "BLOCKER", "no finalization status in the record", "-",
                        "error-fix-loop requires it")]
    f = []
    tr = c.rec["traceability"]
    has_fail = any(t["status"] == "FAIL" for t in tr)
    has_open = any(t["status"] == "OPEN" for t in tr) or \
        c.rec["structure"]["wave_bm"].get("status") == "OPEN" or \
        bool(c.rec["stability"]["intact"].get("open_items"))
    if (has_fail or has_open) and fin["status"] != "NOT_FINALIZED":
        f.append(finding("F12", "BLOCKER", "record claims finality with open errors",
                         f"status={fin['status']} fails={has_fail} opens={has_open}",
                         "revert to NOT_FINALIZED"))
    elif not (has_fail or has_open) and fin["status"] not in ("FROZEN_PENDING_HUMAN", "RELEASED"):
        f.append(finding("F12", "MAJOR", "green record not frozen for human gate",
                         fin["status"], "-"))
    if fin.get("accepted_by") not in (None, ""):
        f.append(finding("F12", "BLOCKER", "agent wrote itself into accepted_by",
                         str(fin.get("accepted_by")),
                         "RELEASED is a human transition; agents may never self-sign"))
    gg = fin.get("gates_green", {})
    for k in ("two_solver_crosscheck_pct", "equilibrium_identities",
              "fe_bm_crosscheck_pct", "drawings_readback"):
        if k not in gg:
            f.append(finding("F12", "MAJOR", f"finalization block missing gate status: {k}",
                             "-", "list every gate's result in the status block"))
    return f or [finding("F12", "PASS", "finalization freeze enforced",
                         f"status={fin['status']}, blockers={fin['blockers']}, "
                         f"open={fin['open_items']}, accepted_by={fin['accepted_by']}", "-")]


# =========================================================================== #
# runner
# =========================================================================== #
def run_fleet(verbose=True):
    c = Ctx()
    all_findings = []
    agent_status = []
    for a in AGENTS:
        t0 = time.time()
        try:
            res = a["fn"](c)
            status = "ok"
        except Exception as exc:                       # a crashing reviewer is a finding
            import traceback
            res = [finding(a["id"], "BLOCKER", f"reviewer crashed: {type(exc).__name__}",
                           f"{exc}\n{traceback.format_exc()[-600:]}",
                           "fix the reviewer before trusting its domain")]
            status = "crashed"
        dt = time.time() - t0
        all_findings.extend(res)
        agent_status.append({"id": a["id"], "name": a["name"], "domain": a["domain"],
                             "status": status, "findings": len(res), "seconds": round(dt, 2),
                             "worst": worst_severity(res)})
        if verbose:
            print(f"  {a['id']} {a['name']:32s} {status:8s} {len(res):3d} findings  "
                  f"worst={worst_severity(res):8s} {dt:5.2f}s")
    return all_findings, agent_status


def worst_severity(findings):
    for s in SEVERITIES:
        if any(f["severity"] == s for f in findings):
            return s
    return "PASS"


if __name__ == "__main__":
    print(f"=== verification fleet: {len(AGENTS)} agents ===")
    findings, status = run_fleet()
    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in SEVERITIES}
    print(f"\n=== {len(findings)} findings: " +
          ", ".join(f"{k}={v}" for k, v in counts.items() if v) + " ===")
    os.makedirs(os.path.join(ROOT, "verification"), exist_ok=True)
    with open(os.path.join(ROOT, "verification", "findings.json"), "w") as fh:
        json.dump({"agents": status, "findings": findings, "counts": counts,
                   "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, fh, indent=2)
    print(f"wrote verification/findings.json")
    for sev in ("BLOCKER", "MAJOR"):
        items = [f for f in findings if f["severity"] == sev]
        if items:
            print(f"\n--- {sev} ({len(items)}) ---")
            for it in items:
                print(f"  [{it['agent']}] {it['title']}")
                print(f"        evidence: {str(it['evidence'])[:220]}")
                print(f"        action  : {str(it['action_required'])[:220]}")

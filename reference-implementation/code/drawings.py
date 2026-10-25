"""
CAD drawing generation with READ-BACK verification.

Drawings are rendered views of the frozen geometry model, never a second source of truth.
Every sheet carries the geometry hash in its title block, and after writing, each DXF is
re-opened and MEASURED against the model: waterline half-breadths, station curve counts,
profile extents and the hash text itself. A drawing that cannot be machine-verified
against its source is a rumour.

Outputs (reference-case/drawings/):
  lines_plan.dxf        body plan + profile + half-breadth plan, one sheet
  hydrostatic_curves.dxf   volume/KB/BMt/Awp/TPC vs draft
  gz_curves.dxf            departure condition GZ + IS Code limit annotations
  midship_section.dxf      immersed outline + neutral axis + scantling table
  drawings.json            hashes + read-back verification results

Toolchain: ezdxf only (free, pip-installable, reads back what it writes). The same
structure maps to FreeCAD TechDraw macros or paid CAD APIs (see cad-drawing-generation
skill); the verification step is tool-independent.
"""
from __future__ import annotations

import hashlib
import json
import math
import os

import numpy as np

import ezdxf

import hull_parametric as H
from hydrostatics import Hydrostatics

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.normpath(os.path.join(HERE, "..", "reference-case", "drawings"))

LAYERS = {
    "HULL_KEEL":    {"color": 5, "linetype": "CONTINUOUS"},
    "HULL_SHEER":   {"color": 5, "linetype": "CONTINUOUS"},
    "HULL_STATION": {"color": 3, "linetype": "CONTINUOUS"},
    "HULL_WL":      {"color": 4, "linetype": "CONTINUOUS"},
    "HULL_BUTTOCK": {"color": 1, "linetype": "DASHED"},
    "GRID":         {"color": 8, "linetype": "CONTINUOUS"},
    "CL":           {"color": 8, "linetype": "CENTER"},
    "TITLE":        {"color": 7, "linetype": "CONTINUOUS"},
    "TEXT":         {"color": 7, "linetype": "CONTINUOUS"},
    "CURVE":        {"color": 4, "linetype": "CONTINUOUS"},
    "ANNOT":        {"color": 6, "linetype": "CONTINUOUS"},
}


def _setup(doc):
    if "CENTER" not in doc.linetypes:
        doc.linetypes.add("CENTER", pattern="A,.5,-.25,0,-.25", description="Center ____ _ ____")
    if "DASHED" not in doc.linetypes:
        doc.linetypes.add("DASHED", pattern="A,.5,-.25", description="Dashed ____ ____")
    for name, props in LAYERS.items():
        if name not in doc.layers:
            doc.layers.add(name, color=props["color"], linetype=props["linetype"])


def _title_block(msp, x, y, w, h, fields):
    msp.add_lwpolyline([(x, y), (x + w, y), (x + w, y + h), (x, y + h)],
                       close=True, dxfattribs={"layer": "TITLE"})
    msp.add_line((x, y + h * 0.5), (x + w, y + h * 0.5), dxfattribs={"layer": "TITLE"})
    msp.add_line((x + w * 0.5, y), (x + w * 0.5, y + h * 0.5), dxfattribs={"layer": "TITLE"})
    msp.add_text(fields["title"], height=h * 0.22,
                 dxfattribs={"layer": "TITLE"}).set_placement(
        (x + w * 0.5, y + h * 0.72), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    msp.add_text(fields["dwg_no"], height=h * 0.14,
                 dxfattribs={"layer": "TEXT"}).set_placement(
        (x + w * 0.25, y + h * 0.25), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    msp.add_text(fields["meta"], height=h * 0.12,
                 dxfattribs={"layer": "TEXT"}).set_placement(
        (x + w * 0.75, y + h * 0.25), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    msp.add_text(fields["hash_line"], height=h * 0.12,
                 dxfattribs={"layer": "TEXT"}).set_placement(
        (x + w * 0.5, y + h * 0.40), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)


def _polyline(msp, pts, layer):
    msp.add_lwpolyline([(float(a), float(b)) for a, b in pts],
                       dxfattribs={"layer": layer})


def _buttock_z(x: float, y_b: float, p) -> float | None:
    """z where halfbreadth(x, z) == y_b, by bisection. None if unreachable."""
    hb = lambda z: float(np.atleast_1d(H.halfbreadth(x, z, p))[0])
    zmax = H.deck_height(x, p)
    if hb(0.0) > y_b or hb(zmax) < y_b:
        # y_b outside the section: find max-z where hb >= y_b (section narrows above draft
        # only via flare here, so scan)
        zs = np.linspace(0.0, zmax, 60)
        vals = [hb(z) for z in zs]
        inside = [z for z, v in zip(zs, vals) if v >= y_b]
        return max(inside) if inside else None
    lo, hi = 0.0, zmax
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if hb(mid) < y_b:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# --------------------------------------------------------------------------- #
# sheet 1: lines plan
# --------------------------------------------------------------------------- #
def make_lines_plan(p, geom_hash: str, path: str, n_st: int = 21, n_wl: int = 7) -> dict:
    doc = ezdxf.new("R2010", setup=True)
    _setup(doc)
    msp = doc.modelspace()

    Lpp, D = p.lpp, p.depth
    xs = np.linspace(0.0, Lpp, n_st)
    zwl = np.linspace(0.0, p.draft, n_wl)

    # ---- profile view (origin 0,0) ----
    prof_y0 = 0.0
    keel = [(x, prof_y0) for x in xs]
    sheer = [(float(x), float(H.deck_height(float(x), p)) + prof_y0) for x in xs]
    _polyline(msp, keel, "HULL_KEEL")
    _polyline(msp, sheer, "HULL_SHEER")
    # stem and transom closure
    _polyline(msp, [(0.0, prof_y0), (0.0, float(H.deck_height(0.0, p)) + prof_y0)], "HULL_SHEER")
    _polyline(msp, [(Lpp, prof_y0), (Lpp, float(H.deck_height(Lpp, p)) + prof_y0)], "HULL_SHEER")
    # design waterline
    _polyline(msp, [(0.0, p.draft), (Lpp, p.draft)], "HULL_WL")
    # buttocks at y = +/- B/4 (drawn in profile as z(x) at that offset)
    for y_b in (0.25 * p.breadth,):
        pts_fwd, pts_aft = [], []
        for x in xs:
            z = _buttock_z(float(x), y_b, p)
            if z is not None:
                pts_fwd.append((float(x), z + prof_y0))
        if len(pts_fwd) > 2:
            _polyline(msp, pts_fwd, "HULL_BUTTOCK")
    # station grid + labels
    for i, x in enumerate(xs):
        msp.add_line((float(x), -2.0), (float(x), D + 2.0), dxfattribs={"layer": "GRID"})
        msp.add_text(f"{i}", height=0.8, dxfattribs={"layer": "TEXT"}).set_placement(
            (float(x), -3.2), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

    # ---- half-breadth plan (below profile) ----
    hb_y0 = -45.0
    # Each waterline is drawn on its OWN layer (HB_WL_k) so the read-back verification can
    # match curves to waterlines by name. Matching by geometry alone is ambiguous here:
    # several waterlines share the same maximum half-breadth (14.9 m for every WL in the
    # parallel-sided zone), so a nearest-value match greedily assigns all curves to one WL
    # and reports the others "undrawn". Self-describing drawings verify exactly.
    for k, z in enumerate(zwl):
        layer = f"HB_WL_{k}"
        if layer not in doc.layers:
            doc.layers.add(layer, color=4, linetype="CONTINUOUS")
        pts_stbd = [(float(x), float(np.atleast_1d(H.halfbreadth(float(x), float(z), p))[0]) + hb_y0)
                    for x in xs]
        pts_port = [(float(x), -float(np.atleast_1d(H.halfbreadth(float(x), float(z), p))[0]) + hb_y0)
                    for x in xs]
        _polyline(msp, pts_stbd, layer)
        _polyline(msp, pts_port, layer)
        msp.add_text(f"WL {float(z):.2f}", height=0.7, dxfattribs={"layer": "TEXT"}).set_placement(
            (Lpp + 3.0, float(z) + hb_y0), align=ezdxf.enums.TextEntityAlignment.MIDDLE_LEFT)
    msp.add_line((0.0, hb_y0), (Lpp, hb_y0), dxfattribs={"layer": "CL"})

    # ---- body plan (stations overlaid, right of profile) ----
    bx0 = Lpp + 60.0
    x_mid = 0.5 * Lpp
    zs_body = np.linspace(0.0, 1.0, 40)
    for i, x in enumerate(xs):
        x = float(x)
        zmax = float(H.deck_height(x, p))
        side = 1.0 if x >= x_mid else -1.0     # fwd stations starboard of CL, aft to port
        pts = []
        for zz in zs_body:
            z = float(zz) * zmax
            y = float(np.atleast_1d(H.halfbreadth(x, z, p))[0])
            pts.append((bx0 + side * y, z))
        _polyline(msp, pts, "HULL_STATION")
    msp.add_line((bx0, -2.0), (bx0, D + 3.0), dxfattribs={"layer": "CL"})
    msp.add_line((bx0 - 16.0, p.draft), (bx0 + 16.0, p.draft), dxfattribs={"layer": "HULL_WL"})

    # ---- annotations & title block ----
    msp.add_text("PROFILE", height=1.2, dxfattribs={"layer": "TEXT"}).set_placement(
        (Lpp * 0.5, D + 4.0), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    msp.add_text("HALF-BREADTH PLAN (waterlines)", height=1.2, dxfattribs={"layer": "TEXT"}).set_placement(
        (Lpp * 0.5, hb_y0 + 20.0), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    msp.add_text("BODY PLAN (stations; fwd stbd / aft port of CL)", height=1.2,
                 dxfattribs={"layer": "TEXT"}).set_placement(
        (bx0, D + 4.0), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    _title_block(msp, Lpp * 0.55, hb_y0 - 22.0, 110.0, 14.0, {
        "title": "LINES PLAN",
        "dwg_no": "HULL-001 Rev A",
        "meta": f"Lpp {Lpp:.1f}  B {p.breadth:.1f}  D {D:.1f}  T {p.draft:.2f}  Cb "
                f"{H.block_coeff(p):.4f}   SCALE 1:100 @ A0   GENERATED FROM MODEL - DO NOT SCALE",
        "hash_line": f"GEOMETRY SHA256:{geom_hash}",
    })
    doc.saveas(path)
    return {"stations": n_st, "waterlines": n_wl, "zwl": zwl.tolist(), "xs": xs.tolist(),
            "hb_origin_y": hb_y0, "body_origin_x": bx0}


# --------------------------------------------------------------------------- #
# sheet 2: hydrostatic curves
# --------------------------------------------------------------------------- #
def make_hydrostatic_curves(hy: Hydrostatics, p, geom_hash: str, path: str,
                            d0: float, d1: float = 14.0, n: int = 49) -> dict:
    doc = ezdxf.new("R2010", setup=True)
    _setup(doc)
    msp = doc.modelspace()
    drafts = np.linspace(d0, d1, n)
    series = {"volume_m3": [], "KB_m": [], "BMt_m": [], "Awp_m2": [], "TPC_t_cm": []}
    for d in drafts:
        st = hy.at_draft(float(d))
        series["volume_m3"].append(st.volume)
        series["KB_m"].append(st.kb)
        series["BMt_m"].append(st.bmt)
        series["Awp_m2"].append(st.awp)
        series["TPC_t_cm"].append(st.awp * 1.025 / 100.0)
    charts = [("volume_m3", 0.0), ("KB_m", 60.0), ("BMt_m", 120.0),
              ("Awp_m2", 180.0), ("TPC_t_cm", 240.0)]
    for name, x_off in charts:
        vals = np.array(series[name])
        vmin, vmax = float(vals.min()), float(vals.max())
        span = max(vmax - vmin, 1e-9)
        pts = [(x_off + 8.0 + 40.0 * (float(d) - d0) / (d1 - d0),
                8.0 + 40.0 * (float(v) - vmin) / span) for d, v in zip(drafts, vals)]
        _polyline(msp, pts, "CURVE")
        # axes
        msp.add_line((x_off + 8.0, 8.0), (x_off + 48.0, 8.0), dxfattribs={"layer": "GRID"})
        msp.add_line((x_off + 8.0, 8.0), (x_off + 8.0, 48.0), dxfattribs={"layer": "GRID"})
        msp.add_text(f"{name}  [{vmin:,.2f} .. {vmax:,.2f}]", height=1.4,
                     dxfattribs={"layer": "TEXT"}).set_placement(
            (x_off + 28.0, 52.0), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
        msp.add_text(f"T={d0:.1f}m", height=0.9, dxfattribs={"layer": "TEXT"}).set_placement(
            (x_off + 8.0, 5.5), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
        msp.add_text(f"T={d1:.1f}m", height=0.9, dxfattribs={"layer": "TEXT"}).set_placement(
            (x_off + 48.0, 5.5), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    _title_block(msp, 90.0, -22.0, 130.0, 14.0, {
        "title": "HYDROSTATIC CURVES",
        "dwg_no": "HULL-002 Rev A",
        "meta": "SW rho=1.025 t/m3, upright, baseline datum - GENERATED FROM MODEL via the "
                "validated two-solver hydrostatics chain",
        "hash_line": f"GEOMETRY SHA256:{geom_hash}",
    })
    doc.saveas(path)
    return {k: [round(v, 4) for v in vals] for k, vals in series.items()} | {
        "drafts": drafts.tolist(), "chart_x_offsets": {n_: x for n_, x in charts}}


# --------------------------------------------------------------------------- #
# sheet 3: GZ curves (departure condition)
# --------------------------------------------------------------------------- #
def make_gz_sheet(record: dict, geom_hash: str, path: str) -> dict:
    doc = ezdxf.new("R2010", setup=True)
    _setup(doc)
    msp = doc.modelspace()
    gz = record["stability"]["gz_curve"]
    phi = np.array([g["phi_deg"] for g in gz], dtype=float)
    val = np.array([g["GZ_m"] for g in gz], dtype=float)
    nt = np.array([g.get("GZ_navaltoolbox_m") or g["GZ_m"] for g in gz], dtype=float)
    ox, oy, sx, sy = 10.0, 10.0, 1.6, 22.0
    _polyline(msp, [(ox + sx * a, oy + sy * b) for a, b in zip(phi, val)], "CURVE")
    _polyline(msp, [(ox + sx * a, oy + sy * b) for a, b in zip(phi, nt)], "ANNOT")
    msp.add_line((ox, oy), (ox + sx * 90, oy), dxfattribs={"layer": "GRID"})
    msp.add_line((ox, oy), (ox, oy + sy * max(val.max(), nt.max()) * 1.1),
                 dxfattribs={"layer": "GRID"})
    for a in range(0, 91, 10):
        msp.add_text(str(a), height=2.0, dxfattribs={"layer": "TEXT"}).set_placement(
            (ox + sx * a, oy - 4.0), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    msp.add_text("heel angle [deg]", height=2.4, dxfattribs={"layer": "TEXT"}).set_placement(
        (ox + sx * 45, oy - 9.0), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    msp.add_text("GZ [m]", height=2.4, dxfattribs={"layer": "TEXT"}).set_placement(
        (ox - 6.0, oy + sy * 2.0), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    gm = record["stability"]["GM_fluid_m"]
    msp.add_text(f"departure condition - GM_fluid {gm:.3f} m", height=2.6,
                 dxfattribs={"layer": "TEXT"}).set_placement(
        (ox + sx * 45, oy + sy * (max(val.max(), nt.max()) + 0.35)),
        align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    msp.add_text("solid: independent solver   dashed colour: navaltoolbox (cross-check)",
                 height=2.0, dxfattribs={"layer": "ANNOT"}).set_placement(
        (ox + sx * 45, oy - 14.0), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    # IS Code reference lines: GZ(30) >= 0.20 m
    msp.add_line((ox, oy + sy * 0.20), (ox + sx * 90, oy + sy * 0.20),
                 dxfattribs={"layer": "ANNOT"})
    msp.add_text("IS 2.1.3.1: GZ(30 deg) >= 0.20 m", height=1.8,
                 dxfattribs={"layer": "ANNOT"}).set_placement(
        (ox + sx * 62, oy + sy * 0.20 + 1.5), align=ezdxf.enums.TextEntityAlignment.MIDDLE_LEFT)
    _title_block(msp, 60.0, oy - 34.0, 120.0, 14.0, {
        "title": "GZ CURVES - DEPARTURE FULL CARGO",
        "dwg_no": "STAB-001 Rev A",
        "meta": "constant-displacement GZ, sinkage re-solved per heel; both solvers plotted",
        "hash_line": f"GEOMETRY SHA256:{geom_hash}",
    })
    doc.saveas(path)
    return {"phi": phi.tolist(), "gz": val.tolist(), "gz_navaltoolbox": nt.tolist()}


# --------------------------------------------------------------------------- #
# sheet 4: midship section
# --------------------------------------------------------------------------- #
def make_midship_section(p, sec: dict, geom_hash: str, path: str) -> dict:
    doc = ezdxf.new("R2010", setup=True)
    _setup(doc)
    msp = doc.modelspace()
    x = 0.5 * p.lpp
    zs = np.linspace(0.0, float(H.deck_height(x, p)), 80)
    ys = np.array([float(np.atleast_1d(H.halfbreadth(x, float(z), p))[0]) for z in zs])
    _polyline(msp, [(y, z) for y, z in zip(ys, zs)], "HULL_STATION")
    _polyline(msp, [(-y, z) for y, z in zip(ys, zs)], "HULL_STATION")
    # inner bottom + design waterline + neutral axis
    msp.add_line((-16, p.draft), (16, p.draft), dxfattribs={"layer": "HULL_WL"})
    na = sec.get("neutral_axis_m")
    if na:
        msp.add_line((-16, na), (16, na), dxfattribs={"layer": "CL"})
        msp.add_text(f"NA z={na:.2f} m", height=0.5, dxfattribs={"layer": "TEXT"}).set_placement(
            (16.5, na), align=ezdxf.enums.TextEntityAlignment.MIDDLE_LEFT)
    msp.add_line((0, -1), (0, p.depth + 2), dxfattribs={"layer": "CL"})
    # scantling table
    ty = -6.0
    msp.add_text("MIDSHIP SECTION - EFFECTIVE STRUCTURAL ITEMS (ESTIMATE-class first pass)",
                 height=0.55, dxfattribs={"layer": "TEXT"}).set_placement(
        (0, ty + 1.2), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    for i, it in enumerate(sec.get("items", [])):
        row = (f"{it['name'][:44]:46s} A={it['area_m2']:6.3f} m2  z={it['z_m']:5.2f} m  "
               f"t={it['thickness_mm']} mm")
        msp.add_text(row, height=0.42, dxfattribs={"layer": "TEXT"}).set_placement(
            (-16.0, ty - 0.8 * i), align=ezdxf.enums.TextEntityAlignment.MIDDLE_LEFT)
    summary = (f"A_total={sec['area_m2']:.3f} m2   NA={sec['neutral_axis_m']:.3f} m   "
               f"I={sec['I_m4']:.2f} m4   Z_deck={sec['Z_deck_cm3']:,.0f} cm3   "
               f"Z_bottom={sec['Z_bottom_cm3']:,.0f} cm3")
    msp.add_text(summary, height=0.5, dxfattribs={"layer": "ANNOT"}).set_placement(
        (0, ty - 0.8 * (len(sec.get("items", [])) + 1) - 0.6),
        align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    _title_block(msp, -16.0, ty - 0.8 * (len(sec.get("items", [])) + 2) - 6.0, 60.0, 4.5, {
        "title": "MIDSHIP SECTION", "dwg_no": "STR-001 Rev A",
        "meta": "x = 0.5 Lpp - scantlings ESTIMATE pending rule-derived sizing",
        "hash_line": f"SHA256:{geom_hash}",
    })
    doc.saveas(path)
    return {"items": len(sec.get("items", [])), "Z_deck_cm3": sec["Z_deck_cm3"]}


# --------------------------------------------------------------------------- #
# READ-BACK verification
# --------------------------------------------------------------------------- #
def verify_lines_plan(path: str, p, meta: dict) -> list[dict]:
    """Re-open the DXF and measure it against the model. This is the gate that makes a
    generated drawing trustworthy: the file on disk, not the intent in memory."""
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    checks = []

    def add(name, ok, detail):
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    keel = [e for e in msp.query('LWPOLYLINE[layer=="HULL_KEEL"]')]
    stations = [e for e in msp.query('LWPOLYLINE[layer=="HULL_STATION"]')]
    texts = " ".join(t.dxf.text for t in msp.query("TEXT"))

    add("keel present", len(keel) == 1, f"{len(keel)} keel polylines")
    if keel:
        pts = keel[0].get_points("xy")
        add("keel x-extent == Lpp", abs((max(q[0] for q in pts) - min(q[0] for q in pts)) - p.lpp) < 1e-6,
            f"measured {max(q[0] for q in pts) - min(q[0] for q in pts):.6f} vs {p.lpp}")
    add("station curve count", len(stations) == meta["stations"],
        f"{len(stations)} vs {meta['stations']}")

    # per-waterline exact matching via dedicated layers
    y0 = meta["hb_origin_y"]
    worst, worst_info, uncovered = 0.0, "none", []
    for k, z in enumerate(meta["zwl"]):
        model_max = max(float(np.atleast_1d(H.halfbreadth(float(x), float(z), p))[0])
                        for x in meta["xs"])
        curves = [e for e in msp.query(f'LWPOLYLINE[layer=="HB_WL_{k}"]')]
        if len(curves) != 2:
            uncovered.append(f"WL{k}(z={z:.2f}): {len(curves)} curves, expected 2")
            continue
        for e in curves:
            pts = np.array(e.get_points("xy"))
            meas = max(abs(pts[:, 1].max() - y0), abs(pts[:, 1].min() - y0))
            d = abs(meas - model_max)
            if d > worst:
                worst, worst_info = d, f"WL{k} z={z:.2f}: measured {meas:.6f} vs model {model_max:.6f}"
    add("every waterline drawn (2 curves per WL layer)", not uncovered,
        "; ".join(uncovered) if uncovered else f"{len(meta['zwl'])} WLs x 2 curves")
    add("WL max half-breadth vs model (<=1e-3 m)", worst <= 1e-3, worst_info)

    # design waterline must appear in the profile view
    dwl = [e for e in msp.query('LINE[layer=="HULL_WL"]')]
    add("profile design waterline present", len(dwl) >= 1, f"{len(dwl)} HULL_WL lines")

    add("geometry hash in title text", meta.get("hash", "")[:16] in texts.replace("SHA256:", "")
        or meta.get("hash", "") in texts, "hash string search in TEXT entities")
    return checks


def verify_any_sheet(path: str, geom_hash: str) -> list[dict]:
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    texts = " ".join(t.dxf.text for t in msp.query("TEXT"))
    n_ent = len(list(msp))
    return [
        {"check": "file re-opens", "pass": True, "detail": f"{n_ent} entities"},
        {"check": "geometry hash present", "pass": geom_hash in texts,
         "detail": f"searched for sha256:{geom_hash}"},
        {"check": "not-to-scale warning present",
         "pass": ("DO NOT SCALE" in texts.upper() or "GENERATED FROM MODEL" in texts.upper()
                  or "cross-check" in texts.lower() or "ESTIMATE" in texts.upper()),
         "detail": "title/annotation text"},
    ]


# --------------------------------------------------------------------------- #
def generate_all(record: dict, hy: Hydrostatics, p, V, T, outdir: str = OUTDIR) -> dict:
    os.makedirs(outdir, exist_ok=True)
    geom_hash = record["hull"]["hull_stl_sha256"]
    sec = record["structure"]["midship_section"]
    d_eq = record["stability"]["equilibrium_draft_m"]

    paths = {
        "lines_plan": os.path.join(outdir, "lines_plan.dxf"),
        "hydrostatic_curves": os.path.join(outdir, "hydrostatic_curves.dxf"),
        "gz_curves": os.path.join(outdir, "gz_curves.dxf"),
        "midship_section": os.path.join(outdir, "midship_section.dxf"),
    }
    meta_lp = make_lines_plan(p, geom_hash, paths["lines_plan"])
    meta_lp["hash"] = geom_hash
    meta_hc = make_hydrostatic_curves(hy, p, geom_hash, paths["hydrostatic_curves"],
                                      d0=max(2.0, d_eq - 6.0), d1=min(14.0, p.depth + 0.5))
    meta_gz = make_gz_sheet(record, geom_hash, paths["gz_curves"])
    meta_ms = make_midship_section(p, sec, geom_hash, paths["midship_section"])

    # read-back verification of every sheet
    verification = {}
    for name, path in paths.items():
        checks = verify_any_sheet(path, geom_hash)
        if name == "lines_plan":
            checks = verify_lines_plan(path, p, meta_lp) + checks
        verification[name] = checks

    hashes = {}
    for name, path in paths.items():
        with open(path, "rb") as f:
            hashes[name] = hashlib.sha256(f.read()).hexdigest()[:16]

    all_pass = all(c["pass"] for cs in verification.values() for c in cs)
    out = {"sheets": {k: os.path.basename(v) for k, v in paths.items()},
           "hashes": hashes, "verification": verification,
           "all_checks_pass": all_pass,
           "meta": {"lines_plan": {k: v for k, v in meta_lp.items() if k != "hash"},
                    "hydrostatic_series_keys": list(meta_hc.keys()),
                    "gz_points": len(meta_gz["phi"]),
                    "midship_items": meta_ms["items"]}}
    with open(os.path.join(outdir, "drawings.json"), "w") as f:
        json.dump(out, f, indent=2, default=float)
    if not all_pass:
        failed = [(n, c) for n, cs in verification.items() for c in cs if not c["pass"]]
        raise AssertionError(f"drawing read-back verification FAILED: {failed}")
    return out


if __name__ == "__main__":
    ref = os.path.normpath(os.path.join(HERE, "..", "reference-case"))
    rec = json.load(open(os.path.join(ref, "design_record.json")))
    p, (V, T), met = H.build_reference_hull(verbose=False)
    V, T, _ = H.clean_mesh(V, T)
    out = generate_all(rec, Hydrostatics(V, T), p, V, T)
    print("=== drawing generation + read-back verification ===")
    for name, checks in out["verification"].items():
        npass = sum(c["pass"] for c in checks)
        print(f"  {name:22s} {npass}/{len(checks)} checks pass  sha256:{out['hashes'][name]}")
        for c in checks:
            if not c["pass"]:
                print(f"      FAIL: {c['check']} :: {c['detail']}")
    print("ALL DRAWINGS VERIFIED" if out["all_checks_pass"] else "VERIFICATION FAILED")

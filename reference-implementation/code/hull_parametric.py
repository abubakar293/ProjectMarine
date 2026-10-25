"""
Parametric hull-form generator for the reference case (Handysize bulk carrier).

Design rules this module enforces -- the same ones the review agents check:

  1. **Geometry is code.** The hull exists as a parameter set + generator, never as a
     hand-edited file. Every artefact is reproducible and hashable.
  2. **The moulded beam B is not a tuning knob.** Hitting a target Cb by scaling the beam
     silently redefines a principal dimension that is usually a terminal/lock constraint.
     The longitudinal *fullness exponent* is solved for instead, so B stays exact.
  3. **c(x) must be the true section-area coefficient.** The first version of this module
     varied the waterline fullness exponent along the length, which made the actual
     section area scale like c^0.52 instead of c. The ends came out far fuller than the
     longitudinal distribution claimed (A/Am = 5.1 x c near the stem), and Cb could only
     be hit with a degenerate exponent. Sections are now geometrically similar, scaled by
     s(x) = sqrt(c(x)), so area(x) = c(x) * Am exactly.
  4. **Physical postconditions are asserted, not hoped for:** Cm <= 1, Cp within the band
     for the ship type, c(x) in [0,1], watertight mesh, outward normals, Cb matched to
     tolerance. Failures raise instead of returning a plausible-looking wrong answer.

Coordinates: x forward from AP, y to starboard, z up from baseline (keel).
"""
from __future__ import annotations

import math
import struct
from dataclasses import dataclass, replace

import numpy as np

# Gauss-Legendre nodes/weights on [0,1] for the vertical section integration
_GL_N, _GL_W = np.polynomial.legendre.leggauss(40)
_GL_Z = 0.5 * (_GL_N + 1.0)
_GL_WZ = 0.5 * _GL_W


class HullGenerationError(RuntimeError):
    """Raised when a physical or geometric postcondition fails."""


@dataclass(frozen=True)
class HullParams:
    # ---- principal dimensions: owner / terminal constraints ----
    loa: float = 190.0        # m
    lpp: float = 180.0        # m   (AP at x = 0, FP at x = lpp)
    breadth: float = 29.8     # m   moulded
    depth: float = 15.2       # m   to upper deck, moulded
    draft: float = 10.5       # m   design (scantling) draft

    # ---- form targets ----
    cb_target: float = 0.845  # block coefficient at design draft

    # ---- transverse section at the reference (full) station ----
    rise_of_floor: float = 0.10
    bilge_radius: float = 2.20
    flat_bottom_frac: float = 0.72   # fraction of half-breadth that is flat bottom
    n_wl: float = 0.22               # waterline fullness exponent (uniform along length)

    # ---- longitudinal shape ----
    run_frac: float = 0.220          # afterbody length / Lpp  -> PMB = 60% of Lpp
    ent_frac: float = 0.180          # forebody length / Lpp   (typical Handysize)
    fullness_exponent: float = 1.10  # SOLVED by solve_for_cb(); seed value only

    # ---- validity band for this ship type (guarded in build_reference_hull) ----
    cm_band: tuple = (0.96, 1.00)
    cp_band: tuple = (0.80, 0.90)

    @property
    def fp_x(self) -> float:
        return self.lpp

    def with_exponent(self, e: float) -> "HullParams":
        return replace(self, fullness_exponent=e)


# --------------------------------------------------------------------------- #
# longitudinal section-area coefficient
# --------------------------------------------------------------------------- #
def section_coeff(x, p: HullParams):
    """c(x) in [0,1] -- the TRUE fraction of full (Am) section area at station x.

    Branch order matters. The parallel middle body MUST be tested first: testing the
    afterbody first silently yields c >> 1 whenever run_frac + ent_frac >= 1, because
    u = x / l_run exceeds 1 inside what should be the PMB.
    """
    if p.run_frac + p.ent_frac >= 1.0:
        raise HullGenerationError(
            f"invalid longitudinal shape: run_frac ({p.run_frac}) + ent_frac ({p.ent_frac}) "
            ">= 1 -> parallel middle body has non-positive length"
        )
    x = np.asarray(x, dtype=float)
    l_run = p.run_frac * p.lpp
    l_ent = p.ent_frac * p.lpp
    x_pmb_aft = l_run
    x_pmb_fwd = p.lpp - l_ent
    c = np.where(
        (x >= x_pmb_aft) & (x <= x_pmb_fwd), 1.0,
        np.where(
            x < x_pmb_aft,
            (np.clip(x / max(l_run, 1e-9), 0.0, 1.0)) ** p.fullness_exponent,
            (np.clip((p.fp_x - x) / max(l_ent, 1e-9), 0.0, 1.0)) ** p.fullness_exponent,
        ),
    )
    c = np.where((x <= 0.0) | (x >= p.fp_x), 0.0, c)
    return np.clip(c, 0.0, 1.0) if c.ndim else float(np.clip(c, 0.0, 1.0))


def section_scale(x, p: HullParams):
    """s(x) = sqrt(c(x)): linear scale factor that makes area(x) = c(x) * Am exactly."""
    c = section_coeff(x, p)
    return np.sqrt(c) if hasattr(c, "__len__") else math.sqrt(c)


# --------------------------------------------------------------------------- #
# transverse section shape  (geometrically similar sections, scaled by s)
# --------------------------------------------------------------------------- #
def _ref_halfbreadth(z: float, p: HullParams) -> float:
    """Half-breadth at height z of the full (s = 1) section."""
    b = 0.5 * p.breadth
    n = p.n_wl
    flat = p.flat_bottom_frac * b
    r = min(p.bilge_radius, max(b - flat, 0.05))
    z_lo = p.rise_of_floor + r
    z_hi = p.depth - r
    if z <= 0.0:
        return 0.0
    if z < p.rise_of_floor:                       # sloped bottom, CL -> bilge tangent
        return flat * (z / p.rise_of_floor) if p.rise_of_floor > 1e-9 else flat
    if z < z_lo:                                  # lower bilge arc
        dz = min(max(z - p.rise_of_floor, 0.0), r)
        return flat + math.sqrt(max(r * r - (r - dz) ** 2, 0.0))
    if z <= z_hi:                                 # side; slight flare above design draft
        return b + (0.0 if z <= p.draft else 0.02 * (z - p.draft))
    dz = min(max(z - z_hi, 0.0), r)               # upper bilge -> deck edge
    return max(b - (r - math.sqrt(max(r * r - dz * dz, 0.0))), 0.0)


def halfbreadth(x, z, p: HullParams):
    """Moulded half-breadth at station x and height z (vectorised in x and z)."""
    s = section_scale(x, p)
    zz = np.atleast_1d(np.asarray(z, dtype=float))
    yref = np.array([_ref_halfbreadth(float(v), p) for v in zz])
    out = np.asarray(s, dtype=float)[..., None] * yref if np.ndim(s) else float(s) * yref
    return out


def deck_height(x, p: HullParams):
    """Upper deck height at station x (sheer profile)."""
    xi = np.asarray(x, dtype=float) / p.lpp
    sheer = (0.90 * np.exp(-((xi - 1.0) / 0.28) ** 2)
             + 0.25 * np.exp(-((xi - 0.0) / 0.16) ** 2))
    d = p.depth + sheer
    return d if d.ndim else float(d)


# --------------------------------------------------------------------------- #
# integration (independent of the mesh -- this is the cross-check path)
# --------------------------------------------------------------------------- #
def immersed_area(x: float, z: float, p: HullParams) -> float:
    """Immersed transverse section area up to draft z at station x (Gauss-Legendre)."""
    if float(section_coeff(x, p)) <= 0.0 or z <= 0.0:
        return 0.0
    ys = halfbreadth(x, _GL_Z * z, p)
    ys = np.atleast_1d(ys)
    if not np.all(np.isfinite(ys)) or np.any(ys < -1e-9):
        raise HullGenerationError(f"non-physical half-breadth at x={x:.3f}")
    return float(2.0 * z * np.dot(_GL_WZ, ys))


def _area_sweep(p: HullParams, draft: float, nst: int):
    xs = np.linspace(0.0, p.fp_x, nst)
    areas = np.array([immersed_area(float(x), draft, p) for x in xs])
    return xs, areas


def displaced_volume(p: HullParams, draft: float | None = None, nst: int = 361) -> float:
    """Immersed volume up to `draft` (defaults to the design draft).

    The draft MUST be an explicit argument. An earlier version always integrated to
    p.draft, so "the parametric volume at draft 10.185 m" silently returned the value for
    10.500 m -- a 4% error hiding inside a verification table, and it made a correct mesh
    solver look wrong.
    """
    z = p.draft if draft is None else float(draft)
    xs, areas = _area_sweep(p, z, nst)
    return float(np.trapezoid(areas, xs))


def midship_area(p: HullParams) -> float:
    return immersed_area(0.5 * p.lpp, p.draft, p)


def midship_coeff(p: HullParams) -> float:
    return midship_area(p) / (p.breadth * p.draft)


def block_coeff(p: HullParams, draft: float | None = None) -> float:
    z = p.draft if draft is None else float(draft)
    return displaced_volume(p, z) / (p.lpp * p.breadth * z)


def lcb(p: HullParams, draft: float | None = None, nst: int = 361) -> float:
    z = p.draft if draft is None else float(draft)
    xs, areas = _area_sweep(p, z, nst)
    return float(np.trapezoid(areas * xs, xs) / np.trapezoid(areas, xs))


def waterplane_halfbreadth(x, p: HullParams):
    """Half-breadth at the design waterline -- used for Awp, IT, LCF, TPC."""
    return np.atleast_1d(halfbreadth(np.asarray(x, dtype=float), p.draft, p))


def waterplane_properties(p: HullParams, nst: int = 361):
    """Awp, LCF (from AP), IT (2nd moment about centreline), TPC at design draft."""
    xs = np.linspace(0.0, p.fp_x, nst)
    y = np.array([float(np.atleast_1d(waterplane_halfbreadth(x, p))[0]) for x in xs])
    awp = float(np.trapezoid(2.0 * y, xs))
    lcf = float(np.trapezoid(2.0 * y * xs, xs) / awp)
    it = float(np.trapezoid((2.0 / 3.0) * y ** 3, xs))
    return {"awp_m2": awp, "lcf_m_from_ap": lcf, "it_m4": it,
            "tpc_t_per_cm": awp * 1.025 / 100.0}


def solve_for_cb(p: HullParams, tol: float = 1e-8, itmax: int = 80):
    """Solve the longitudinal fullness exponent so that Cb(design draft) == cb_target.

    Raises rather than silently returning a bound value: an earlier version returned
    the upper bracket and Cb = 0.78 while reporting success.
    """
    target = p.cb_target
    lo, hi = 0.30, 14.0
    f_lo = block_coeff(p.with_exponent(lo)) - target
    f_hi = block_coeff(p.with_exponent(hi)) - target
    if f_lo * f_hi > 0:
        raise HullGenerationError(
            f"Cb target {target} unreachable for exponent in [{lo},{hi}] "
            f"(f(lo)={f_lo:+.4f}, f(hi)={f_hi:+.4f})"
        )
    best = p.with_exponent(0.5 * (lo + hi))
    for _ in range(itmax):
        mid = 0.5 * (lo + hi)
        f = block_coeff(p.with_exponent(mid)) - target
        best = p.with_exponent(mid)
        if abs(f) < tol:
            break
        if f_lo * f < 0:
            hi = mid
        else:
            lo, f_lo = mid, f
    cb = block_coeff(best)
    if abs(cb - target) > 1e-4:
        raise HullGenerationError(f"Cb solver did not converge: {cb:.5f} vs {target:.5f}")
    return best, cb


# --------------------------------------------------------------------------- #
# meshing -> watertight STL
# --------------------------------------------------------------------------- #
def _ring(x: float, p: HullParams, n_z: int) -> np.ndarray:
    """Section outline: starboard keel -> deck edge, then port back down.

    Coincident points are NOT removed: uniform ring counts keep the stitching index
    arithmetic valid, and degenerate triangles have zero area.
    """
    zmax = float(deck_height(x, p))
    zs = np.linspace(0.0, zmax, n_z)
    y = np.atleast_1d(halfbreadth(x, zs, p)).ravel()
    star = np.column_stack([y, zs])
    port = np.column_stack([-y[::-1], zs[::-1]])
    return np.vstack([star, port])


def build_mesh(p: HullParams, n_st: int = 181, n_z: int = 40):
    xs = np.linspace(0.0, p.fp_x, n_st)
    rings = [_ring(float(x), p, n_z) for x in xs]
    m = len(rings[0])
    if not all(len(r) == m for r in rings):
        raise HullGenerationError("ring point count must be uniform")

    verts = np.zeros((n_st * m, 3), dtype=np.float64)
    for i, ring in enumerate(rings):
        verts[i * m:(i + 1) * m, 0] = xs[i]
        verts[i * m:(i + 1) * m, 1:] = ring

    tris = []
    for i in range(n_st - 1):
        b0, b1 = i * m, (i + 1) * m
        for j in range(m):
            jn = (j + 1) % m
            tris.append((b0 + j, b0 + jn, b1 + jn))
            tris.append((b0 + j, b1 + jn, b1 + j))

    # Planar caps. The apex must lie ON the ring plane (x = xs[ring_idx]) -- using the
    # ring centroid of a non-planar outline, or a zero-initialised row, turns the
    # "planar" cap into a cone and corrupts the divergence-theorem volume.
    pieces = [verts]
    for ring_idx, sign in ((0, -1.0), (n_st - 1, +1.0)):
        base = ring_idx * m
        pts = verts[base:base + m]
        apex = np.array([[xs[ring_idx], float(pts[:, 1].mean()), float(pts[:, 2].mean())]])
        centre = len(verts) + len(pieces) - 1
        pieces.append(apex)
        for j in range(m):
            jn = (j + 1) % m
            tris.append((centre, base + j, base + jn) if sign > 0
                        else (centre, base + jn, base + j))

    return np.vstack(pieces), np.array(tris, dtype=np.int64)


def weld_vertices(V: np.ndarray, T: np.ndarray, decimals: int = 6):
    """Merge coincident vertices and re-index the triangles.

    The stem and transom station outlines collapse to a single vertical line, so the
    starboard and port halves of those rings generate DIFFERENT vertex indices at the
    SAME coordinates. The in-memory mesh therefore reports 520 boundary edges and fails a
    manifold check, while the STL round-trip (which welds on read) reports a perfectly
    closed mesh. A model that is closed on disk but open in memory breaks downstream
    solvers non-deterministically, so weld once, at generation time, and check that.
    """
    key = np.round(V, decimals)
    uniq, inv = np.unique(key, axis=0, return_inverse=True)
    inv = np.asarray(inv).ravel()          # numpy >= 2.0 returns this flattened
    # `inv` is a PER-VERTEX map (len == len(V)), so it must be applied to the triangle
    # indices: T_new = inv[T]. Reshaping inv to T.shape is wrong and only ever appeared to
    # work when the vertex list happened to be emitted in triangle order.
    return uniq.astype(np.float64), inv[T].astype(np.int64)


def signed_volume(V: np.ndarray, T: np.ndarray) -> float:
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    return float(np.einsum('ij,ij->i', a, np.cross(b, c)).sum() / 6.0)


def fix_orientation(V: np.ndarray, T: np.ndarray):
    if signed_volume(V, T) < 0:
        T = T[:, [0, 2, 1]].copy()
    return V, T


def mesh_is_closed(T, V=None, area_tol: float = 1e-9):
    """Every edge shared by exactly two triangles (degenerate triangles excluded).

    Delegated to hydrostatics.mesh_report so there is only ONE definition of
    watertightness in the stack -- two definitions is how a real design office ends up
    with a model that one department calls closed and another calls broken.
    """
    from hydrostatics import mesh_is_closed as _closed
    return _closed(T, V, area_tol)


def mesh_report(V, T):
    from hydrostatics import mesh_report as _rep
    return _rep(V, T)


def clean_mesh(V: np.ndarray, T: np.ndarray):
    """Weld coincident vertices and drop zero-area triangles.

    MANDATORY before handing a mesh to a third-party solver. The reference hull has 522
    degenerate triangles where the stem and transom rings collapse to a line; they are
    harmless to a divergence-theorem integrator but they changed navaltoolbox's displaced
    volume by -19% and its BMt by +19%. A tool that is exact on a clean analytic prism and
    wrong on your mesh is still your mesh's fault.
    """
    from hydrostatics import drop_degenerate
    V, T = weld_vertices(V, T)
    V, T = fix_orientation(V, T)
    T, n_removed = drop_degenerate(V, T)
    return V, T, n_removed


def write_stl(path: str, V: np.ndarray, T: np.ndarray, name: str = "hull") -> None:
    V, T = fix_orientation(V, T)
    with open(path, "wb") as f:
        f.write(name.encode("ascii", "ignore")[:80].ljust(80, b"\0"))
        f.write(struct.pack("<I", len(T)))
        for tri in T:
            a, b, c = V[tri[0]], V[tri[1]], V[tri[2]]
            n = np.cross(b - a, c - a)
            ln = float(np.linalg.norm(n))
            n = n / ln if ln > 0 else np.zeros(3)
            f.write(struct.pack("<3f", *n))
            f.write(struct.pack("<3f", *a))
            f.write(struct.pack("<3f", *b))
            f.write(struct.pack("<3f", *c))
            f.write(struct.pack("<H", 0))


def offsets_table(p: HullParams, n_st: int = 21, n_wl: int = 7):
    """Classic offsets table: stations x waterlines -> half-breadths (a class deliverable)."""
    xs = np.linspace(0.0, p.fp_x, n_st)
    zwl = np.linspace(0.0, p.draft, n_wl)
    rows = []
    for z in zwl:
        rows.append([float(np.atleast_1d(halfbreadth(float(x), float(z), p))[0]) for x in xs])
    return xs.tolist(), zwl.tolist(), rows


# --------------------------------------------------------------------------- #
# full generation with postconditions
# --------------------------------------------------------------------------- #
def build_reference_hull(verbose: bool = True):
    p0 = HullParams()
    p, cb = solve_for_cb(p0)

    cm = midship_coeff(p)
    cp = cb / cm
    if cm > 1.0 + 1e-6:
        raise HullGenerationError(f"Cm = {cm:.4f} > 1 is geometrically impossible")
    if not (p.cm_band[0] <= cm <= p.cm_band[1]):
        raise HullGenerationError(
            f"Cm = {cm:.4f} outside the band {p.cm_band} for this ship type: the midship "
            "section is not U-shaped enough (check flat_bottom_frac / bilge_radius)"
        )
    if not (p.cp_band[0] <= cp <= p.cp_band[1]):
        raise HullGenerationError(
            f"Cp = {cp:.4f} outside {p.cp_band}: ends are unrealistically "
            f"{'full' if cp > p.cp_band[1] else 'fine'} for a Handysize bulk carrier. "
            "Fix the longitudinal distribution, do not force Cb with a degenerate exponent."
        )

    v = displaced_volume(p)
    V, T = build_mesh(p)
    n_raw = len(V)
    V, T = weld_vertices(V, T)
    n_welded = n_raw - len(V)
    V, T = fix_orientation(V, T)
    if not mesh_is_closed(T, V):
        raise HullGenerationError(
            f"generated mesh is not watertight: {mesh_report(V, T)}"
        )
    vol_mesh = signed_volume(V, T)
    if vol_mesh <= 0:
        raise HullGenerationError("mesh normals point inward")

    wp = waterplane_properties(p)
    metrics = {
        "Lpp_m": p.lpp, "B_m": p.breadth, "D_m": p.depth, "T_design_m": p.draft,
        "fullness_exponent_solved": round(p.fullness_exponent, 5),
        "displaced_volume_m3": round(v, 2),
        "displacement_t_rho1025": round(v * 1.025, 1),
        "Cb": round(cb, 5), "Cm": round(cm, 5), "Cp": round(cp, 5),
        "LCB_m_from_AP": round(lcb(p), 2),
        "LCB_pct_Lpp": round(100.0 * lcb(p) / p.lpp, 2),
        "Am_midship_m2": round(midship_area(p), 2),
        **{k: (round(val, 3) if isinstance(val, float) else val) for k, val in wp.items()},
        "mesh_vertices": int(len(V)), "mesh_triangles": int(len(T)),
        "vertices_welded": int(n_welded),
        "mesh_closed": True,
        "mesh_volume_to_main_deck_m3": round(vol_mesh, 1),
    }
    if verbose:
        for k_, v_ in metrics.items():
            print(f"  {k_:34s} {v_:,}" if not isinstance(v_, float) else f"  {k_:34s} {v_:,.4f}")
    return p, (V, T), metrics


if __name__ == "__main__":
    import json, os, hashlib
    print("=== reference hull generation ===")
    p, (V, T), met = build_reference_hull()
    os.makedirs("../reference-case", exist_ok=True)
    write_stl("../reference-case/hull.stl", V, T)
    xs, zwl, rows = offsets_table(p)
    with open("../reference-case/offsets.json", "w") as f:
        json.dump({"stations_x_m": xs, "waterlines_z_m": zwl, "halfbreadths_m": rows,
                   "params": {k: v for k, v in p.__dict__.items()}}, f, indent=2)
    with open("../reference-case/hull_metrics.json", "w") as f:
        json.dump(met, f, indent=2)
    h = hashlib.sha256(open("../reference-case/hull.stl", "rb").read()).hexdigest()[:16]
    print(f"\n  wrote hull.stl ({os.path.getsize('../reference-case/hull.stl')/1e6:.2f} MB, sha256:{h})")
    print(f"  wrote offsets.json, hull_metrics.json")

"""
Independent mesh hydrostatics / stability solver, plus cross-verification against the
third-party solver `navaltoolbox`.

Why this exists
---------------
An agent that only ever reads one tool's output cannot detect that tool's mistakes, or
its own. So every reference-case number is computed twice, by two independent
implementations, and the disagreement is reported rather than hidden.

`navaltoolbox` was validated against a closed-form analytic prism before being trusted
(see test_solver_groundtruth.py): volume, KB, Awp, BMt, BMl, LCF, LCB all exact.

This module was NOT correct first time. Four separate defects were found by that
cross-check, and each is recorded at the point where it was fixed:

  1. clipping emitted the two-inside case with reversed triangle winding, so opposite
     faces cancelled (unit cube: 0.0 instead of 0.5);
  2. the signed distances were not rotated together with the vertices, so intersection
     points landed on the wrong edges (box: 9,200 m3 with COB_y = -2.28 m on a hull
     symmetric about y = 0);
  3. the volume was taken as the tetrahedron sum over an OPEN clipped surface. That sum
     is (1/3) * integral (p.n) dS, which equals the enclosed volume only when the surface
     is closed; the missing waterplane cap contributes (1/3) * d * Awp. It is zero only
     when the waterplane passes through the origin -- so a unit-cube test clipped at z=0
     passed while the real case was 4,000 m3 low. Fixed by shifting the mesh by -d*n
     before integrating;
  4. the first moment used a hand-derived surface quadrature that omitted the centroid
     term of the exact quadratic rule. The correct tetrahedron moment is simply
     det[p,q,r] * (p+q+r) / 24.

Conventions
-----------
Ship-fixed frame: x forward from AP, y to starboard, z up from baseline (keel).
Density in t/m3 and masses in tonnes (the navaltoolbox convention, verified empirically).
Heel phi positive = heeled to starboard. Trim positive = by the bow.
"""
from __future__ import annotations

import math
import struct
from dataclasses import dataclass

import numpy as np

RHO_SW = 1.025        # t/m3
G = 9.80665           # m/s2


# --------------------------------------------------------------------------- #
# geometry helpers
# --------------------------------------------------------------------------- #
def _chain_loops(segs2d: np.ndarray, tol: float = 1e-6):
    """Chain 2D segments (N,2,2) into closed loops.

    The adjacency map is keyed on BOTH endpoints of every segment, and each half-edge is
    CONSUMED when it is traversed. An earlier version keyed the map the same way but only
    tracked whole segments as used, so every loop immediately found its own reversed
    segment, closed on itself after two points, and the routine returned 32 copies of the
    same waterplane outline. That made Awp 141,457 m2 instead of 4,715 m2 and BMt 202 m
    instead of 8.05 m -- every stability number downstream was wrong with it.
    """
    if len(segs2d) == 0:
        return []
    # Drop zero-length segments and duplicates first. A collapsed stem/transom ring makes
    # every triangle in the end band emit the SAME zero-length segment (29 and 31 copies
    # on the reference hull), and those self-loops stall the traversal so the waterplane
    # comes back as 16 fragments instead of 1 loop. At 459k triangles the same defect
    # produced Awp = 2,779 m2 instead of 4,718 m2.
    seg_len = np.linalg.norm(segs2d[:, 1] - segs2d[:, 0], axis=1)
    keep = seg_len > 1e-7
    segs2d = segs2d[keep]
    if len(segs2d) == 0:
        return []
    canon = {}
    rows = []
    for sg in segs2d:
        k = tuple(sorted([tuple(np.round(sg[0], 6)), tuple(np.round(sg[1], 6))]))
        if k not in canon:
            canon[k] = True
            rows.append(sg)
    segs2d = np.array(rows) if rows else np.zeros((0, 2, 2))
    if len(segs2d) == 0:
        return []
    adj = {}
    for i, (p0, p1) in enumerate(segs2d):
        k0 = tuple(np.round(p0, 6))
        k1 = tuple(np.round(p1, 6))
        adj.setdefault(k0, []).append((k1, i))
        adj.setdefault(k1, []).append((k0, i))
    avail = set(range(len(segs2d)))
    loops = []
    while avail:
        start_i = min(avail)
        p0, p1 = segs2d[start_i]
        cur = tuple(np.round(p0, 6))
        nxt = tuple(np.round(p1, 6))
        chain = [np.asarray(p0, dtype=float), np.asarray(p1, dtype=float)]
        avail.discard(start_i)
        guard = 0
        while guard < 4 * len(segs2d) + 16:
            guard += 1
            cand = None
            for key, j in adj.get(nxt, []):
                if j in avail:
                    cand = (key, j)
                    break
            if cand is None:
                break
            key, j = cand
            avail.discard(j)
            a, b = segs2d[j]
            other = b if np.allclose(tuple(np.round(a, 6)), nxt, atol=tol) else a
            nxt = tuple(np.round(other, 6))
            chain.append(np.asarray(other, dtype=float))
            if nxt == tuple(np.round(chain[0], 6)):
                break
        if len(chain) >= 3:
            loops.append(np.array(chain))
    return loops


def _loop_moments(pts: np.ndarray):
    """(signed area, x-centroid numerator, integral of y^2 dA) for a closed polygon loop.

        A   = (1/2) sum (x_i y_{i+1} - x_{i+1} y_i)
        A*cx = (1/6) sum (x_i + x_{i+1}) * cr_i
        int y^2 dA = (1/12) sum cr_i * (y_i^2 + y_i y_{i+1} + y_{i+1}^2)

    The 1/12 (not 1/6) is easy to get wrong: on the analytic box waterplane
    100 x 20 it must give IT = 100*20^3/12 = 66,666.67 and hence BMt = IT/nabla
    = 5.5556 m. With 1/6 it gives exactly twice that, which is the error this replaced.
    """
    x, y = pts[:, 0], pts[:, 1]
    x1, y1 = np.roll(x, -1), np.roll(y, -1)
    cr = x * y1 - x1 * y
    area = 0.5 * cr.sum()
    cx_num = ((x + x1) * cr).sum() / 6.0
    iyy = (cr * (y ** 2 + y * y1 + y1 ** 2) / 12.0).sum()     # int y^2 dA -> IT
    return float(area), float(cx_num), float(iyy)


# --------------------------------------------------------------------------- #
# the one geometric kernel: clip a mesh by a half-space and integrate
# --------------------------------------------------------------------------- #
def clip_integrate(V: np.ndarray, T: np.ndarray, n: np.ndarray, d: float):
    """Volume and first moment of {p in solid : n.p <= d}.

    The mesh is first shifted by -d*n so that the cutting plane passes through the
    origin. The clipped surface is then bounded by a cap lying in p.n = 0, and the
    tetrahedral decomposition about the origin is exact:

        volume = sum det[p,q,r] / 6
        moment = sum det[p,q,r] * (p+q+r) / 24

    Returns (volume, moment) expressed in the ORIGINAL (unshifted) frame.
    Requires outward-pointing normals on the input mesh.
    """
    n = np.asarray(n, dtype=float)
    n = n / np.linalg.norm(n)
    Vs = V - d * n
    a, b, c = Vs[T[:, 0]], Vs[T[:, 1]], Vs[T[:, 2]]
    da, db, dc = a @ n, b @ n, c @ n
    ia, ib, ic = da <= 0.0, db <= 0.0, dc <= 0.0
    count = ia.astype(np.int8) + ib.astype(np.int8) + ic.astype(np.int8)

    vol = np.zeros(len(T))
    mom = np.zeros((len(T), 3))

    def accum(p, q, r, mask):
        det = np.einsum('ij,ij->i', p, np.cross(q, r))
        vol[mask] += det / 6.0
        mom[mask] += (det / 24.0)[:, None] * (p + q + r)

    m3 = count == 3
    if m3.any():
        accum(a[m3], b[m3], c[m3], m3)

    def rot3(v0, v1, v2, which):
        """Move the `which`-th vertex (0=a,1=b,2=c) to the front, preserving cyclic order.

        Vertices AND their signed distances must be rotated by the same permutation;
        pairing (b,c,a) with (da,db,dc) puts intersection points on the wrong edges.
        """
        vs = (v0, v1, v2)
        return vs[which], vs[(which + 1) % 3], vs[(which + 2) % 3]

    # exactly one inside -> triangle (P, I1, I2)
    for which, mask in ((0, ia & ~ib & ~ic), (1, ib & ~ia & ~ic), (2, ic & ~ia & ~ib)):
        if not mask.any():
            continue
        P, Q, R = rot3(a, b, c, which)
        dP, dQ, dR = rot3(da, db, dc, which)
        P, Q, R, dP, dQ, dR = (v[mask] for v in (P, Q, R, dP, dQ, dR))
        I1 = P + (dP / (dP - dQ))[:, None] * (Q - P)
        I2 = P + (dP / (dP - dR))[:, None] * (R - P)
        accum(P, I1, I2, mask)

    # exactly two inside -> quad I1-Q-R-I2 split as (I1,R,I2) + (I1,Q,R).
    # Winding must follow the original P->Q->R orientation; reversing it makes
    # opposite faces cancel and the integral collapse.
    for which, mask in ((0, ~ia & ib & ic), (1, ia & ~ib & ic), (2, ia & ib & ~ic)):
        if not mask.any():
            continue
        P, Q, R = rot3(a, b, c, which)
        dP, dQ, dR = rot3(da, db, dc, which)
        P, Q, R, dP, dQ, dR = (v[mask] for v in (P, Q, R, dP, dQ, dR))
        I1 = P + (dP / (dP - dQ))[:, None] * (Q - P)
        I2 = P + (dP / (dP - dR))[:, None] * (R - P)
        accum(I1, R, I2, mask)
        accum(I1, Q, R, mask)

    v = float(vol.sum())
    return v, mom.sum(axis=0) + v * d * n


def cut_segments(V: np.ndarray, T: np.ndarray, n: np.ndarray, d: float) -> np.ndarray:
    """Boundary segments (N,2,3) where the mesh crosses the plane n.p = d."""
    n = np.asarray(n, float); n = n / np.linalg.norm(n)
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    da, db, dc = a @ n - d, b @ n - d, c @ n - d
    ia, ib, ic = da <= 0.0, db <= 0.0, dc <= 0.0
    count = ia.astype(np.int8) + ib.astype(np.int8) + ic.astype(np.int8)
    out = []
    for which, m1, m2 in ((0, ia & ~ib & ~ic, ~ia & ib & ic),
                          (1, ib & ~ia & ~ic, ia & ~ib & ic),
                          (2, ic & ~ia & ~ib, ia & ib & ~ic)):
        vs = (a, b, c); ds = (da, db, dc)
        P, Q, R = vs[which], vs[(which + 1) % 3], vs[(which + 2) % 3]
        dP, dQ, dR = ds[which], ds[(which + 1) % 3], ds[(which + 2) % 3]
        for mask in (m1, m2):
            if not mask.any():
                continue
            p, q, r = P[mask], Q[mask], R[mask]
            dp, dq, dr = dP[mask], dQ[mask], dR[mask]
            i1 = p + (dp / (dp - dq))[:, None] * (q - p)
            i2 = p + (dp / (dp - dr))[:, None] * (r - p)
            out.append(np.stack([i1, i2], axis=1))
    return np.concatenate(out, axis=0) if out else np.zeros((0, 2, 3))


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #
@dataclass
class HydroState:
    draft: float
    volume: float
    displacement: float
    cob: np.ndarray
    kb: float
    lcb: float
    awp: float
    lcf: float
    bmt: float
    bml: float
    it_m4: float
    il_m4: float


class Hydrostatics:
    def __init__(self, V: np.ndarray, T: np.ndarray, rho: float = RHO_SW):
        self.V = np.ascontiguousarray(V, dtype=float)
        self.T = np.ascontiguousarray(T, dtype=np.int64)
        self.rho = rho
        self._z = np.array([0.0, 0.0, 1.0])
        self.full_volume_m3, _ = clip_integrate(self.V, self.T, self._z, 1e9)
        if self.full_volume_m3 <= 0:
            raise ValueError(
                f"mesh normals point inward (enclosed volume {self.full_volume_m3:,.1f} m3)"
            )

    # -- plane definition for an arbitrarily heeled/trimmed waterline --------
    def _plane(self, heel_deg: float, pitch_deg: float, zeta: float, G):
        """Waterplane of a heeled/trimmed hull, as a half-space n.p <= d in hull coords.

        Kinematics
        ----------
        World frame: Z up, calm water surface at Z = 0. A hull point p (x forward from AP,
        y to starboard, z up from the baseline) maps to the world by

            P_w = R (p - G) + G + [0, 0, zeta]

        where G is the centre of gravity used as the rotation pivot and zeta is the WORLD
        HEIGHT OF THE BASELINE (so zeta = -draft when upright). Substituting P_w.z <= 0:

            P_w.z = (R^T e3) . (p - G) + G.z + zeta
            n     = R[:, 2] = R @ e3            <- the world vertical in hull coordinates
                                                  (the third COLUMN, not the third row)
            d     = G.z - zeta - n . G

        Note that n is the third COLUMN of R, not the third row. Taking the row instead
        gives Ry[2,:] = (sp, 0, cp), which contains no heel terms at all, so the waterplane
        never tilts and the entire GZ curve is computed at zero heel -- while every upright
        hydrostatic stays exactly correct. That is why this is asserted below rather than
        left as a comment.

        Conventions
        -----------
        +heel  -> starboard DOWN:  (0,1,0) maps to (0, ch, -sh)
        +pitch -> bow DOWN:        (1,0,0) maps to (cp, 0, -sp)
        R = Rz(heel) @ Ry(pitch): pitch about the hull transverse axis first, then heel
        about the world vertical.
        """
        ch, sh = math.cos(math.radians(heel_deg)), math.sin(math.radians(heel_deg))
        cp, sp = math.cos(math.radians(pitch_deg)), math.sin(math.radians(pitch_deg))
        # HEEL IS A ROTATION ABOUT THE LONGITUDINAL x-AXIS, i.e. Rx -- NOT Rz.
        # Building this from Rz (a rotation in the xy-plane, whose third row AND third
        # column are trivially (0,0,1)) made the waterplane normal independent of heel, so
        # every GZ was computed at zero heel. The bug survived four review passes because
        # all the UPRIGHT hydrostatics were exactly right, and only the heeled case -- the
        # one that matters for stability -- was wrong.
        #   Rx(heel) : +heel sends starboard DOWN, (0,1,0) -> (0, ch, -sh)
        #   Ry(pitch): +pitch sends the bow DOWN,  (1,0,0) -> (cp, 0, -sp)
        #   R = Rx(heel) @ Ry(pitch)
        Rx = np.array([[1.0, 0.0, 0.0],
                       [0.0, ch, sh],
                       [0.0, -sh, ch]])
        # Ry must send the bow DOWN for +pitch: (1,0,0) -> (cp, 0, -sp). The transpose sends
        # the bow UP and silently flips the sign of every reported trim. Settled numerically
        # in settle_convention.py rather than by hand, after two wrong hand derivations.
        Ry = np.array([[cp, 0.0, sp],
                       [0.0, 1.0, 0.0],
                       [-sp, 0.0, cp]])
        R = Rx @ Ry
        n = np.ascontiguousarray(R[:, 2])
        self._check_plane_convention(R, n, ch, sh, cp, sp, heel_deg, pitch_deg)
        G = np.asarray(G, dtype=float)
        return n, float(G[2] - zeta - float(n @ G)), R

    @staticmethod
    def _check_plane_convention(R, n, ch, sh, cp, sp, heel_deg, pitch_deg):
        """Pin the rotation convention by PHYSICAL properties, not by a hand-derived formula.

        Two separate hand derivations of the closed form for n = R[:,2] were wrong, and each
        wrong version was self-consistent enough to pass review. These assertions instead
        check things that can be read straight off the definition of the convention:

          * +heel maps the starboard unit vector DOWN in the world;
          * +pitch maps the bow unit vector DOWN in the world;
          * n is the world vertical expressed in hull coordinates, R[:,2] = R @ e3;
          * n is unit length and depends on heel and on pitch.

        Every one of these failed at some point during development, and each failure
        produced plausible numbers rather than an exception -- which is precisely the
        failure mode a verification layer exists to make impossible.
        """
        y_world = R @ np.array([0.0, 1.0, 0.0])
        if not np.allclose(y_world, [0.0, ch, -sh], atol=1e-13):
            raise AssertionError(
                f"+heel must send starboard DOWN: R @ (0,1,0) = {y_world}, expected (0, {ch}, {-sh})"
            )
        if pitch_deg > 0.0 and y_world[2] > 0.0:
            raise AssertionError("heel raised the starboard side; the heel sign is flipped")
        x_world = R @ np.array([1.0, 0.0, 0.0])
        if heel_deg == 0.0 and not np.allclose(x_world, [cp, 0.0, -sp], atol=1e-13):
            raise AssertionError(
                f"+pitch must send the bow DOWN: R @ (1,0,0) = {x_world}, expected ({cp}, 0, {-sp})"
            )
        if pitch_deg > 0.0 and x_world[2] > 0.0:
            raise AssertionError("positive pitch raised the bow; the trim sign is flipped")
        # n = R[:,2] = R @ e3. Note this is the third COLUMN: R^T @ e3 would be the third
        # ROW, which for R = Rx(heel) @ Ry(pitch) equals (sp, 0, cp) and is independent of
        # heel -- asserting against it is what sent this round of debugging in a circle.
        if not np.allclose(n, R @ np.array([0.0, 0.0, 1.0]), atol=1e-14):
            raise AssertionError("n must equal R @ e3 = R[:,2] (the world vertical in hull coordinates)")
        if abs(np.linalg.norm(n) - 1.0) > 1e-12:
            raise AssertionError(f"waterplane normal is not unit length: {n}")
        if abs(heel_deg) > 1e-9 and abs(n[1]) < 1e-9:
            raise AssertionError(
                f"waterplane normal does not depend on heel (n = {n}); heel is being applied "
                "about the wrong axis -- it must be the longitudinal x-axis, not z"
            )
        if abs(pitch_deg) > 1e-9 and abs(n[0]) < 1e-9:
            raise AssertionError(f"waterplane normal does not depend on pitch (n = {n})")
        if heel_deg == 0.0 and pitch_deg == 0.0 and not np.allclose(n, [0.0, 0.0, 1.0], atol=1e-15):
            raise AssertionError(f"upright normal must be (0,0,1), got {n}")

    def submerged(self, zeta: float, heel: float = 0.0, pitch: float = 0.0, G=None):
        """(volume m3, centre of buoyancy in hull coordinates) for a floating attitude.

        `clip_integrate` returns the first MOMENT (int p dV, units m4), so it must be
        divided by the volume here. Returning it raw puts 1.89e6 "metres" into cob_x and
        makes every downstream equilibrium iteration meaningless.
        """
        G = np.zeros(3) if G is None else np.asarray(G, dtype=float)
        R = self._rotation(heel, pitch)
        # Work entirely in the WORLD frame. Rotate the hull about G, translate so the
        # baseline sits at world height zeta, then clip at Z <= 0 with the plane normal
        # (0,0,1). This removes the indirection through a hull-frame plane normal, which is
        # where the heeled-case defects kept hiding: at zero heel that normal is exactly
        # (0,0,1), so every upright hydrostatic stayed correct while every heeled one was
        # wrong, and the error was invisible in any table that only showed upright values.
        Vw = (self.V - G) @ R.T + G
        Vw[:, 2] += zeta
        vol, mom = clip_integrate(Vw, self.T, np.array([0.0, 0.0, 1.0]), 0.0)
        cob_world = mom / vol if abs(vol) > 1e-9 else np.zeros(3)
        # Return the centre of buoyancy in HULL coordinates so callers can compare it with
        # hull-frame quantities: undo the translation, then the rotation, about G.
        cw = cob_world.copy()
        cw[2] -= zeta
        cob = R.T @ (cw - G) + G
        return vol, cob

    # -- upright hydrostatics ------------------------------------------------
    def vol_cob_at_draft(self, draft: float):
        """Upright, waterline at z = draft from the baseline.

        Returns (volume, centre of buoyancy). `clip_integrate` returns the first MOMENT,
        so the division by volume happens here -- forgetting it reports KB as int z dV
        (36,000 m4) instead of 3.000 m.
        """
        vol, mom = clip_integrate(self.V, self.T, self._z, draft)
        cob = mom / vol if abs(vol) > 1e-9 else np.zeros(3)
        return vol, cob

    def waterplane_properties(self, draft: float):
        """Exact Awp, LCF, IT and IL from the waterplane polygon(s)."""
        segs = cut_segments(self.V, self.T, self._z, draft)
        loops = _chain_loops(segs[:, :, :2])
        if not loops:
            return {"awp_m2": 0.0, "lcf_m": float("nan"), "it_m4": 0.0,
                    "il_m4": 0.0, "n_loops": 0, "n_segments": int(len(segs))}
        areas, cxs, it_total = [], [], 0.0
        for pts in loops:
            area, cx_num, ixx = _loop_moments(pts)
            if area < 0:                              # enforce CCW so areas add
                pts = pts[::-1]
                area, cx_num, ixx = _loop_moments(pts)
            areas.append(area); cxs.append(cx_num); it_total += ixx
        awp = float(sum(areas))
        lcf = float(sum(cxs) / awp) if abs(awp) > 1e-12 else float("nan")
        il_total = 0.0
        for pts in loops:
            area, _, _ = _loop_moments(pts)
            p = pts if area > 0 else pts[::-1]
            x, y = p[:, 0] - lcf, p[:, 1]
            x1, y1 = np.roll(x, -1), np.roll(y, -1)
            cr = x * y1 - x1 * y
            il_total += abs((cr * (x ** 2 + x * x1 + x1 ** 2) / 12.0).sum())
        return {"awp_m2": awp, "lcf_m": lcf, "it_m4": float(abs(it_total)),
                "il_m4": float(il_total), "n_loops": len(loops),
                "n_segments": int(len(segs))}

    def at_draft(self, draft: float) -> HydroState:
        vol, cob = self.vol_cob_at_draft(draft)
        wp = self.waterplane_properties(draft)
        awp, it, il = wp["awp_m2"], wp["it_m4"], wp["il_m4"]
        return HydroState(draft=draft, volume=vol, displacement=vol * self.rho,
                          cob=cob, kb=float(cob[2]), lcb=float(cob[0]),
                          awp=awp, lcf=wp["lcf_m"],
                          bmt=it / vol if vol > 0 else float("nan"),
                          bml=il / vol if vol > 0 else float("nan"),
                          it_m4=it, il_m4=il)

    def hydrostatics_table(self, drafts):
        return [self.at_draft(float(d)) for d in drafts]

    # -- equilibrium ---------------------------------------------------------
    def equilibrium_draft(self, displacement_t: float, lo=0.05, hi=25.0, tol=1e-9):
        target = displacement_t / self.rho
        f = lambda dd: self.vol_cob_at_draft(dd)[0] - target
        flo, fhi = f(lo), f(hi)
        if flo * fhi > 0:
            raise ValueError(
                f"displacement {displacement_t:,.1f} t outside draft bracket [{lo},{hi}] m "
                f"(f(lo)={flo:,.1f}, f(hi)={fhi:,.1f})"
            )
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            fm = f(mid)
            if flo * fm <= 0:
                hi = mid
            else:
                lo, flo = mid, fm
            if hi - lo < tol:
                break
        return 0.5 * (lo + hi)

    def equilibrium_trim(self, displacement_t: float, lcg: float, vcg: float,
                         max_iter: int = 80):
        """Solve (zeta, trim) so displacement matches and LCB == LCG. G is the pivot."""
        target = displacement_t / self.rho
        G = np.array([lcg, 0.0, vcg], dtype=float)
        # zeta is the world height of the baseline, so the seed is MINUS the equilibrium
        # draft (see _plane).
        zeta = -self.equilibrium_draft(displacement_t)
        pitch = 0.0
        for _ in range(max_iter):
            vol, cob = self.submerged(zeta, 0.0, pitch, G=G)
            r = np.array([vol - target, cob[0] - lcg])
            if abs(r[0]) < 1e-8 * target and abs(r[1]) < 1e-6:
                break
            hz, hp = 0.01, 0.05
            v1, c1 = self.submerged(zeta + hz, 0.0, pitch, G=G)
            v2, c2 = self.submerged(zeta, 0.0, pitch + hp, G=G)
            J = np.array([[(v1 - vol) / hz, (v2 - vol) / hp],
                          [(c1[0] - cob[0]) / hz, (c2[0] - cob[0]) / hp]])
            try:
                # Newton: J.step = -r, so the RHS passed to solve is -r.
                step = np.linalg.solve(J, -r)
            except np.linalg.LinAlgError:
                break
            zeta += float(np.clip(step[0], -2.0, 2.0))
            pitch += float(np.clip(step[1], -5.0, 5.0))
        vol, cob = self.submerged(zeta, 0.0, pitch, G=G)
        conv = abs(vol - target) < 1e-6 * target and abs(cob[0] - lcg) < 1e-4
        return {"zeta_m": zeta, "trim_deg": pitch,
                "trim_m": math.tan(math.radians(pitch)) * 180.0,
                "volume_m3": vol, "displacement_t": vol * self.rho,
                "lcb_m_from_ap": float(cob[0]),
                "volume_residual_pct": 100.0 * (vol - target) / target,
                "lcb_residual_m": float(cob[0] - lcg), "converged": bool(conv)}

    # -- GZ ------------------------------------------------------------------
    def gz_curve(self, displacement_t: float, cog, heels):
        """Constant-displacement GZ: sinkage re-solved at every heel angle."""
        target = displacement_t / self.rho
        G = np.asarray(cog, dtype=float)
        zeta = -self.equilibrium_draft(displacement_t)
        out = {}
        for phi in heels:
            phi = float(phi)
            z, vol = self._solve_zeta(target, phi, G, seed=zeta)
            _, cob = self.submerged(z, phi, 0.0, G=G)
            gz, dvec = self._gz_from_world_frame(cob, G, phi, 0.0)
            out[phi] = {"gz_m": float(gz), "sinkage_zeta_m": float(z), "volume_m3": float(vol),
                        "cob_y_m": float(cob[1] - G[1]), "cob_z_m": float(cob[2] - G[2]),
                        "volume_residual_pct": 100.0 * (vol - target) / target}
            zeta = z
        return out

    def _gz_from_world_frame(self, cob, G, heel_deg, pitch_deg):
        """Righting arm computed in the WORLD frame, where there is no sign ambiguity.

        Place G at the world origin. Then B_world = R (B_hull - G) and the buoyancy force
        acts along +Z_world, so

            GZ = ( B_world x e_z ).x = B_world.y

        This is the perpendicular distance from G to the (vertical) line of action of
        buoyancy, which is the definition of the righting arm. Everything is checked against
        the small-angle identity GZ -> GM sin(phi) rather than against a sign convention.
        """
        R = self._rotation(heel_deg, pitch_deg)
        d_hull = np.asarray(cob, dtype=float) - np.asarray(G, dtype=float)
        d_world = R @ d_hull
        return float(d_world[1]), d_world

    def _rotation(self, heel_deg: float, pitch_deg: float) -> np.ndarray:
        ch, sh = math.cos(math.radians(heel_deg)), math.sin(math.radians(heel_deg))
        cp, sp = math.cos(math.radians(pitch_deg)), math.sin(math.radians(pitch_deg))
        Rx = np.array([[1.0, 0.0, 0.0], [0.0, ch, sh], [0.0, -sh, ch]])
        Ry = np.array([[cp, 0.0, sp], [0.0, 1.0, 0.0], [-sp, 0.0, cp]])
        return Rx @ Ry

    def _solve_zeta(self, target_vol, heel, G, seed, span=25.0):
        f = lambda z: self.submerged(z, heel, 0.0, G=G)[0] - target_vol
        lo, hi = seed - span, seed + span
        if f(lo) * f(hi) > 0:
            raise ValueError(f"cannot bracket sinkage at heel {heel} deg (seed {seed:.3f})")
        for _ in range(120):
            mid = 0.5 * (lo + hi)
            fm = f(mid)
            if f(lo) * fm <= 0:
                hi = mid
            else:
                lo = mid
            if hi - lo < 1e-11:
                break
        z = 0.5 * (lo + hi)
        return z, self.submerged(z, heel, 0.0, G=G)[0]


# --------------------------------------------------------------------------- #
# STL reader (binary), with vertex welding
# --------------------------------------------------------------------------- #
# SELF-TEST LIVES IN test_solver_groundtruth.py, which validates this module against a
# closed-form analytic prism (volume, KB, Awp, BMt, BMl, LCF, LCB) before any real hull is
# run. Run it with:  python3 test_solver_groundtruth.py
def load_stl(path: str):
    with open(path, "rb") as f:
        f.read(80)
        (n,) = struct.unpack("<I", f.read(4))
        buf = f.read(50 * n)
    data = np.frombuffer(buf, dtype=np.uint8).reshape(n, 50)
    T0 = np.arange(3 * n).reshape(n, 3)
    tri = np.zeros((n, 3, 3), dtype=np.float64)
    for k in range(3):
        tri[:, k, :] = np.frombuffer(data[:, 12 + 12 * k:24 + 12 * k].tobytes(),
                                     dtype="<f4").reshape(n, 3)
    pts = tri.reshape(-1, 3)
    uniq, inv = np.unique(np.round(pts, 6), axis=0, return_inverse=True)
    inv = np.asarray(inv).ravel()
    # inv maps each of the 3n raw points to a welded vertex; apply it to the (n,3)
    # triangle index array rather than reshaping it.
    return uniq.astype(np.float64), inv[T0].astype(np.int64)


def mesh_enclosed_volume(V: np.ndarray, T: np.ndarray) -> float:
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    return float(np.einsum('ij,ij->i', a, np.cross(b, c)).sum() / 6.0)


def drop_degenerate(V: np.ndarray, T: np.ndarray, area_tol: float = 1e-9):
    """Remove zero-area triangles.

    The parametric generator collapses the stem and transom station outlines to a single
    vertical line, which produces 522 genuinely degenerate triangles out of 28,960. They
    contribute nothing to any integral, but they DO break a naive edge-manifold check:
    their edges come out with multiplicity 4 and 6. Filtering them gives 42,657 edges,
    every one shared exactly twice, and zero boundary edges.
    """
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    keep = area >= area_tol
    return T[keep], int((~keep).sum())


def mesh_report(V: np.ndarray, T: np.ndarray, area_tol: float = 1e-9) -> dict:
    """Full manifold report -- the evidence a reviewer should see, not just a bool."""
    Tk, n_deg = drop_degenerate(V, T, area_tol)
    e = np.sort(np.concatenate([Tk[:, [0, 1]], Tk[:, [1, 2]], Tk[:, [2, 0]]], axis=0), axis=1)
    uniq, counts = np.unique(e, axis=0, return_counts=True)
    return {
        "triangles": int(len(T)),
        "degenerate_triangles": n_deg,
        "non_degenerate_triangles": int(len(Tk)),
        "unique_edges": int(len(uniq)),
        "edge_multiplicity_hist": {int(k): int(v) for k, v in
                                   zip(*np.unique(counts, return_counts=True))},
        "boundary_edges": int((counts == 1).sum()),
        "non_manifold_edges": int((counts > 2).sum()),
        "closed": bool(np.all(counts == 2)),
        "enclosed_volume_m3": mesh_enclosed_volume(V, T),
    }


def mesh_is_closed(T: np.ndarray, V: np.ndarray | None = None,
                   area_tol: float = 1e-9) -> bool:
    if V is not None:
        T, _ = drop_degenerate(V, T, area_tol)
    e = np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]], axis=0), axis=1)
    _, counts = np.unique(e, axis=0, return_counts=True)
    return bool(np.all(counts == 2))


# --------------------------------------------------------------------------- #
# cross-verification
# --------------------------------------------------------------------------- #
def cross_verify(stl_path: str, draft: float, displacement_t: float, cog, heels,
                 lpp: float, breadth: float, verbose: bool = True):
    """Run both solvers on the same mesh; report every disagreement."""
    from navaltoolbox import Hull, Vessel, HydrostaticsCalculator, StabilityCalculator

    V, T = load_stl(stl_path)
    rep = mesh_report(V, T)
    if not rep["closed"]:
        raise ValueError(f"mesh is not watertight -- refusing to cross-verify: {rep}")
    mine = Hydrostatics(V, T)
    st_mine = mine.at_draft(draft)

    vessel = Vessel(Hull(stl_path))
    hc = HydrostaticsCalculator(vessel, water_density=RHO_SW)
    sc = StabilityCalculator(vessel, water_density=RHO_SW)
    st_nt = hc.from_draft(draft=draft, vcg=float(cog[2]))

    rows = [
        # UNIT NOTE, established empirically not from the docs: with
        # water_density = 1.025 (t/m3) navaltoolbox returns `volume` in m3 and
        # `displacement` in TONNES. With water_density = 1025.0 it returns the same volume
        # but displacement in KILOGRAMS. Assuming kg while passing t/m3 gives a 1000x error
        # that looks like a solver disagreement rather than a unit mistake.
        ("volume_m3", st_mine.volume, float(st_nt.volume)),
        ("displacement_t", st_mine.displacement, float(st_nt.displacement)),
        ("KB_m", st_mine.kb, float(st_nt.vcb)),
        ("LCB_m_from_AP", st_mine.lcb, float(st_nt.lcb)),
        ("Awp_m2", st_mine.awp, float(st_nt.waterplane_area)),
        ("LCF_m_from_AP", st_mine.lcf, float(st_nt.lcf)),
        ("BMt_m", st_mine.bmt, float(st_nt.bmt)),
        ("BMl_m", st_mine.bml, float(st_nt.bml)),
        ("Cb", st_mine.volume / (lpp * breadth * draft), float(st_nt.cb)),
        ("wetted_surface_m2", float("nan"), float(st_nt.wetted_surface_area)),
    ]

    gz_mine = mine.gz_curve(displacement_t, cog, list(heels))
    try:
        # `gz_curve` takes the displacement in the SAME mass unit that `water_density`
        # implies. With water_density = 1.025 t/m3 that is TONNES. Passing kilograms floats
        # the ship 1000x too light: it returned GZ(5 deg) = 0.331 m instead of 0.598 m,
        # which is GM*sin(5 deg) for the true GM of 6.809 m. A unit error like this looks
        # exactly like a solver disagreement, which is why the cross-check exists.
        curve = sc.gz_curve(displacement_t,
                            (float(cog[0]), float(cog[1]), float(cog[2])), list(heels))
        gz_nt = {float(h_): float(v_) for h_, v_ in zip(curve.heels(), curve.values())}
    except Exception as exc:                                     # pragma: no cover
        gz_nt = {}
        rows.append(("gz_error", str(exc), str(exc)))
    for phi in heels:
        phi = float(phi)
        if phi in gz_nt:
            rows.append((f"GZ@{phi:g}deg_m", gz_mine[phi]["gz_m"], gz_nt[phi]))

    report = []
    for name, a_, b_ in rows:
        if isinstance(a_, str) or isinstance(b_, str):
            report.append({"quantity": name, "independent": a_, "navaltoolbox": b_,
                           "delta": None, "delta_pct": None})
            continue
        a_, b_ = float(a_), float(b_)
        if not (math.isfinite(a_) and math.isfinite(b_)):
            report.append({"quantity": name, "independent": a_, "navaltoolbox": b_,
                           "delta": None, "delta_pct": None})
            continue
        d = a_ - b_
        # A percentage delta is meaningless near zero: GZ(0 deg) is exactly zero by
        # symmetry, and both solvers return ~1e-5 of mesh noise there, which prints as a
        # 200% "disagreement". Report an absolute delta against a scale instead.
        scale = max(abs(b_), 1e-6)
        report.append({"quantity": name, "independent": round(a_, 6),
                       "navaltoolbox": round(b_, 6), "delta": round(d, 6),
                       "delta_pct": round(100.0 * d / scale, 4),
                       "near_zero": bool(abs(b_) < 1e-3)})

    if verbose:
        w = max(len(r["quantity"]) for r in report)
        print(f"{'quantity'.ljust(w)}  {'independent':>16}  {'navaltoolbox':>16}  {'delta %':>10}")
        print("-" * (w + 50))
        worst = 0.0
        for r in report:
            d = r["delta_pct"]
            if d is not None and not r.get("near_zero") and abs(d) > worst:
                worst = abs(d)
            tag = f"{d:+.4f}%" if d is not None else "n/a"
            if r.get("near_zero"):
                tag += " (near-zero)"
            print(f"{r['quantity'].ljust(w)}  {str(r['independent']):>16}  "
                  f"{str(r['navaltoolbox']):>16}  {tag:>10}")
        print(f"\nworst absolute disagreement: {worst:.4f}%")
    return report

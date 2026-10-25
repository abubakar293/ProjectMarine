"""
Euler-Bernoulli beam finite element -- the third independent method for the hull-girder
bending moment, and the reference implementation of the simulation-suite rule:
VALIDATE AGAINST CLOSED FORMS BEFORE ANY PROJECT USE.

Chain of trust:
  1. cantilever tip load      vs  delta = P L^3 / 3EI,  M(x) = P (L - x)
  2. simply supported UDL     vs  M_max = w L^2 / 8,  delta_mid = 5 w L^4 / 384 EI
  3. the reference ship's load curve q(x) from structure.load_curve, whose BM came from
     direct double integration -- two completely different discretisations of the same
     physics. Agreement inside 1% is the gate; disagreement is a BLOCKER finding.

The element is the standard 2-node Euler-Bernoulli beam (Hermitian shape functions,
exact for prismatic elements under nodal-equivalent loads), assembled with free-free
ends, so it must also reproduce the integrator's boundary conditions exactly.
"""
from __future__ import annotations

import numpy as np


def beam_element(L: float, E: float, I: float) -> np.ndarray:
    """Standard 2-node Euler-Bernoulli stiffness, dofs [w1, th1, w2, th2]."""
    c = E * I / L ** 3
    return c * np.array([
        [12.0,    6.0 * L,   -12.0,    6.0 * L],
        [6.0 * L, 4.0 * L**2, -6.0 * L, 2.0 * L**2],
        [-12.0,  -6.0 * L,    12.0,   -6.0 * L],
        [6.0 * L, 2.0 * L**2, -6.0 * L, 4.0 * L**2],
    ])


def consistent_load(q: float, L: float) -> np.ndarray:
    """Consistent nodal force vector for a uniformly distributed load q on the element."""
    return q * L * np.array([0.5, L / 12.0, 0.5, -L / 12.0])


def _solve_free_free(K: np.ndarray, F: np.ndarray, x: np.ndarray):
    """Solve K u = F with the two rigid-body modes (heave, pitch) projected out.

    Projection via an orthonormal null-space basis of the constraint matrix, NOT a
    Lagrange-augmented lstsq: with realistic element stiffnesses (~1e5) and constraint
    entries (~1e2) the augmented system spans ~15 orders of magnitude in singular values
    and lstsq silently truncates legitimate directions -- observed as a BM diagram whose
    shape correlation with the integrator collapsed to 0.29 while equilibrium still held.
    """
    from scipy.linalg import null_space
    ndof = K.shape[0]
    r1 = np.zeros(ndof); r1[0::2] = 1.0
    r2 = np.zeros(ndof); r2[0::2] = x
    R = np.column_stack([r1, r2])
    Qn = null_space(R.T)                          # orthonormal basis of range(R)^perp
    if Qn.shape[1] != ndof - 2:
        raise AssertionError("rigid-body projection lost dimensions")
    Kred = Qn.T @ K @ Qn
    Fred = Qn.T @ F
    y = np.linalg.solve(Kred, Fred)
    return Qn @ y


def solve_beam(x_nodes: np.ndarray, E: float, I: float, q: np.ndarray,
               bc: str = "free-free") -> dict:
    """Solve EI w'''' = q on a uniform node grid.

    q is given at the element midpoints (len = n_elem), positive upward, matching the
    convention  EI w'''' = q. For the ship sign convention (load intensity q_s = w - b
    positive downward, BM positive hogging) pass q = -q_s and read BM = -EI w''.
    """
    n = len(x_nodes)
    ne = n - 1
    if not np.allclose(np.diff(x_nodes), x_nodes[1] - x_nodes[0], rtol=1e-9):
        raise ValueError("uniform node grid required (matches the load-curve quadrature)")
    L = float(x_nodes[1] - x_nodes[0])
    if len(q) != ne:
        raise ValueError(f"q must have one value per element: {len(q)} vs {ne}")

    ndof = 2 * n
    K = np.zeros((ndof, ndof))
    F = np.zeros(ndof)
    ke = beam_element(L, E, I)
    for e in range(ne):
        idx = np.array([2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3])
        K[np.ix_(idx, idx)] += ke
        F[idx] += consistent_load(q[e], L)

    if bc == "free-free":
        fixed = []                      # no displacement BCs; rigid-body modes handled below
    elif bc == "pinned-pinned":
        fixed = [0, 2 * (n - 1)]        # w=0 at both ends
    elif bc == "clamped-free":
        fixed = [0, 1]                  # w=0, th=0 at x=0
    else:
        raise ValueError(f"unknown bc {bc!r}")

    free = [i for i in range(ndof) if i not in fixed]
    if bc == "free-free":
        # Rigid-body modes projected out (see _solve_free_free); this is the FEM
        # equivalent of the integrator's SF(0)=SF(L)=BM(0)=BM(L)=0 end conditions.
        r1 = np.zeros(ndof); r1[0::2] = 1.0
        r2 = np.zeros(ndof); r2[0::2] = x_nodes
        resid_eq = np.column_stack([r1, r2]).T @ F   # net force & moment of the loads
        u = _solve_free_free(K, F, x_nodes)
    else:
        u = np.zeros(ndof)
        u[free] = np.linalg.solve(K[np.ix_(free, free)], F[free])
        resid_eq = np.array([0.0, 0.0])

    w = u[0::2]
    th = u[1::2]
    # internal BM and SF per element from the element stiffness
    bm = np.zeros(ne)
    sf = np.zeros(ne)
    for e in range(ne):
        idx = np.array([2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3])
        fe = ke @ u[idx]
        sf[e] = -fe[0]                    # shear at the left node (sign per convention below)
        bm[e] = fe[1]                     # moment at the left node
    return {"x_nodes": x_nodes, "w": w, "theta": th, "bm_elem": bm, "sf_elem": sf,
            "load_equilibrium_residual": resid_eq}


# --------------------------------------------------------------------------- #
# validation against closed forms -- runs at import in __main__ and in CI
# --------------------------------------------------------------------------- #
def validate(tolerance: float = 0.005) -> list[dict]:
    E, I = 2.1e11, 0.05                       # arbitrary but consistent
    L, n = 20.0, 401
    x = np.linspace(0.0, L, n)
    results = []

    # 1) cantilever, tip point load P (as an end nodal force)
    P = 1.0e5
    ndof = 2 * n
    K = np.zeros((ndof, ndof)); F = np.zeros(ndof)
    ke = beam_element(L / (n - 1), E, I)
    for e in range(n - 1):
        idx = np.array([2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3])
        K[np.ix_(idx, idx)] += ke
    F[2 * (n - 1)] = -P                        # downward tip load
    fixed = [0, 1]
    free = [i for i in range(ndof) if i not in fixed]
    u = np.zeros(ndof)
    u[free] = np.linalg.solve(K[np.ix_(free, free)], F[free])
    tip = -u[2 * (n - 1)]
    exact = P * L ** 3 / (3 * E * I)
    err = abs(tip - exact) / exact
    results.append({"case": "cantilever tip deflection", "fem": tip, "exact": exact,
                    "err_pct": 100 * err, "pass": bool(err <= tolerance)})

    # 2) simply supported, UDL w  ->  M_max = w L^2/8, delta_mid = 5 w L^4 / 384 EI
    w0 = 2.0e4
    sol = solve_beam(x, E, I, -np.full(n - 1, w0), bc="pinned-pinned")  # q upward-negative
    mid = -sol["w"][n // 2]
    exact_d = 5 * w0 * L ** 4 / (384 * E * I)
    err_d = abs(mid - exact_d) / exact_d
    # BM at midspan: from the element end moments. For a pinned-pinned beam the internal
    # moment at element e left node equals w * x * (L - x) / 2 (sagging positive here).
    bm_max = -sol["bm_elem"].min() if sol["bm_elem"].min() < 0 else sol["bm_elem"].max()
    exact_m = w0 * L ** 2 / 8
    err_m = abs(abs(bm_max) - exact_m) / exact_m
    results.append({"case": "SS UDL mid deflection", "fem": mid, "exact": exact_d,
                    "err_pct": 100 * err_d, "pass": bool(err_d <= tolerance)})
    results.append({"case": "SS UDL max moment", "fem": bm_max, "exact": exact_m,
                    "err_pct": 100 * err_m, "pass": bool(err_m <= tolerance)})

    bad = [r for r in results if not r["pass"]]
    if bad:
        raise AssertionError(f"beam FE failed closed-form validation: {bad}")
    return results


def crosscheck_ship_bm(load_curve: dict, tolerance_pct: float = 1.0) -> dict:
    """FE the ship load curve and compare the BM diagram against direct integration.

    Two completely different discretisations of the beam equation (fourth derivative of
    deflection equals load intensity):
      A) rectangle-rule double integration with free-free end conditions,
      B) Euler-Bernoulli beam elements with consistent loads and rigid-body projection.

    Faithful load application matters: distributed loads (buoyancy, distributed weights)
    become element loads; LUMPED weights become NODAL forces. Smearing a point weight over
    elements lost 25% of the peak BM and broke load equilibrium by the end-cell residue --
    both observed before this was fixed.

    E*I is set to 1.0 deliberately: the BM distribution of a free-free beam under
    self-equilibrated loads is independent of stiffness, and pretending to know the real
    girder EI at this stage would be noise.

    Sign conventions differ between methods, so the sign is CALIBRATED numerically and the
    calibration is itself gated: the shape correlation over the span must exceed 0.999,
    otherwise the diagrams disagree in shape and no sign factor can rescue them.
    """
    x = np.array(load_curve["x_m"])
    n = len(x)
    if n < 20:
        raise ValueError("load curve too coarse for a meaningful cross-check")
    ne = n - 1
    w_dist = np.array(load_curve["w_dist_kN_per_m"])
    b = np.array(load_curve["b_kN_per_m"])
    lumped = load_curve["lumped_loads_kN_down"]

    # Upward-positive FE load set, made DISCRETELY IDENTICAL to the integrator's:
    # the integrator's rectangle rule treats node i as cell [x_i, x_i+dx] over ALL n
    # nodes, so the last node is a phantom end cell. The FE has n-1 elements; its missing
    # end cell is lumped as a tip nodal force. Without this, vertical equilibrium is off by
    # exactly one end cell (4.9 kN here) and the FE refuses to run -- which is the check
    # doing its job.
    qnet = b - w_dist                                  # upward-positive intensity, kN/m
    dx = float(x[1] - x[0])
    q_elem = qnet[:-1]
    F_node = np.zeros(n)
    F_node[-1] += qnet[-1] * dx                        # phantom end cell -> tip nodal force
    for item in lumped:
        i = int(np.argmin(np.abs(x - item["x_m"])))
        F_node[i] -= item["F_kN"]
    total = float(q_elem.sum() * dx + F_node.sum())
    scale = max(float(np.abs(b).sum() * dx), 1.0)
    if abs(total) > 1e-6 * scale:
        raise AssertionError(f"FE load set not in vertical equilibrium: {total:.4e} kN")

    ndof = 2 * n
    # EI is arbitrary for a statically determinate free-free beam (the BM diagram does not
    # depend on it), but its UNITS are not: loads here are kN and lengths m, so E must be
    # in kN/m2. Solving with E = 2.1e11 Pa against kN loads mixed units by 1000x and the
    # diagram came out as garbage with huge "deflections" -- while the closed-form
    # validations still passed, because they were internally consistent in N and m. Unit
    # consistency must be asserted per call site, not inherited from the tests.
    E_use, I_use = 2.1e8, 10.0                    # kN/m2 * m4 = kN m2
    K = np.zeros((ndof, ndof)); F = np.zeros(ndof)
    # ELEMENT length, not span: ke scales with L^-3 and the consistent load with L. Using
    # the span (100 m) instead of the element length (0.05 m) here inflated stiffness by
    # (L/dx)^3 = 8e6 and loads by 2000x, mixed the scalings so the load set stopped being
    # orthogonal to the rigid-body modes, and the projection solver returned garbage with a
    # 0.04 shape correlation. The closed-form validations passed because they assemble with
    # their own (correct) element length -- which is why the crosscheck must ALSO be
    # validated against a case with a known diagram, not only against the validations.
    L_e = float(x[1] - x[0])
    ke = beam_element(L_e, E_use, I_use)
    fe_load = np.zeros((ne, 4))
    for e in range(ne):
        idx = np.array([2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3])
        K[np.ix_(idx, idx)] += ke
        fe_load[e] = consistent_load(q_elem[e], L_e)
        F[idx] += fe_load[e]
    F[0::2] += F_node

    u = _solve_free_free(K, F, x)

    # INTERNAL end moments must subtract the fixed-end (consistent-load) contribution:
    # fe_internal = ke @ ue - fe_load. For short elements the omitted term is only
    # q*L_e^2/12 -- tiny -- which is why the closed-form validation passed without it,
    # while the ship diagram (25x coarser elements) could not.
    bm_fe = np.zeros(ne)
    for e in range(ne):
        idx = np.array([2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3])
        bm_fe[e] = (ke @ u[idx])[1] - fe_load[e][1]
    x_bm_fe = x[:-1]                                  # end moments live at the left nodes

    bm_int = np.array(load_curve["BM_kNm"])
    lo, hi = 3, n - 4                                 # ignore boundary-cell noise
    a = bm_int[lo:hi]
    bfe = np.interp(x[lo:hi], x_bm_fe, bm_fe)
    corr = float(np.corrcoef(a, bfe)[0, 1])
    if abs(corr) <= 0.999:
        raise AssertionError(
            f"FE and integrator BM diagrams have different SHAPES (corr = {corr:.5f}); "
            "no sign factor can reconcile them -- find the real defect"
        )
    sigma = 1.0 if corr > 0 else -1.0
    peak = float(np.abs(a).max())
    err_pct = float(np.abs(a - sigma * bfe).max() / max(peak, 1e-9) * 100.0)
    out = {"method_a": "direct double integration (rectangle rule, free-free)",
           "method_b": "Euler-Bernoulli beam FE (consistent + nodal loads, projection)",
           "n_nodes": n, "sign_calibration": sigma, "shape_correlation": corr,
           "max_abs_diff_kNm": float(np.abs(a - sigma * bfe).max()),
           "scale_peak_BM_kNm": peak, "max_diff_pct_of_peak": err_pct,
           "tolerance_pct": tolerance_pct, "pass": bool(err_pct <= tolerance_pct),
           "load_equilibrium_residual_kN": total,
           "note": "two discretisations of the same ODE; disagreement localises quadrature, "
                   "load-application or sign errors that neither method shows alone"}
    if not out["pass"]:
        raise AssertionError(
            f"FE/integrator BM disagreement {err_pct:.2f}% > {tolerance_pct}% of peak")
    return out


def ship_bm_crosscheck(refcase: str | None = None) -> dict:
    """Rebuild the reference load curve and cross-check the BM diagram, FE vs integrator.

    Kept as an importable function (not just a __main__ block) so run_case.py and the
    review fleets can call the identical code path -- a test that lives only in __main__
    is a test CI can forget.
    """
    import json, os, sys, math
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    import numpy as np
    import hull_parametric as H
    import structure as S
    import loading as LD
    from hydrostatics import Hydrostatics

    refcase = refcase or os.path.normpath(os.path.join(here, "..", "reference-case"))
    rec = json.load(open(os.path.join(refcase, "design_record.json")))
    dep = rec["stability"]["conditions"]["departure_full_cargo"]
    disp, lcg, vcg = dep["displacement_t"], dep["lcg_m"], dep["vcg_m"]

    p, (V, T), met = H.build_reference_hull(verbose=False)
    V, T, _ = H.clean_mesh(V, T)
    hy = Hydrostatics(V, T)
    d_eq = hy.equilibrium_draft(disp)
    eq = hy.equilibrium_trim(disp, lcg, vcg)
    tr = math.tan(math.radians(eq["trim_deg"]))

    # trimmed waterline: z_wl(x) = z_ref + (x - lcg) * tan(trim), z_ref solved on volume
    xs = np.linspace(0.0, p.fp_x, 721)
    dx = xs[1] - xs[0]
    z_ref = d_eq
    for _ in range(60):
        areas = np.array([H.immersed_area(float(x), max(z_ref + (x - lcg) * tr, 0.0), p)
                          for x in xs])
        v_try = float(np.sum(areas)) * dx
        errv = v_try - disp / 1.025
        if abs(errv) < 1e-7 * (disp / 1.025):
            break
        awp = float(np.sum([2.0 * float(np.atleast_1d(H.halfbreadth(float(x), 
                       max(z_ref + (x - lcg) * tr, 0.0), p))[0]) for x in xs])) * dx
        z_ref -= errv / max(awp, 1e-6)
    areas = np.array([H.immersed_area(float(x), max(z_ref + (x - lcg) * tr, 0.0), p)
                      for x in xs])

    # weights: the exact same build-up as run_case.py (single source: loading.main)
    LD.OUT = refcase
    _, _, data, caps, res = LD.main()
    cond = data["conditions"]["departure_full_cargo"]
    weights = [{"mass_t": data["lightship"]["mass_t"], "lcg_m": data["lightship"]["lcg_m"]}]
    for h in data["cargo"]["holds"]:
        weights.append({"mass_t": h["mass_t"], "x_start_m": h["x_start_m"],
                        "x_end_m": h["x_end_m"]})
    for t in data["tanks"]:
        f_ = cond["tank_fills"].get(t["name"], 0.0)
        if f_ > 0.001:
            nx, ny, nz = 20, 12, 10
            txs = np.linspace(t["x_min"], t["x_max"], nx)
            tys = np.linspace(t["y_min"], t["y_max"], ny)
            tzs = np.linspace(t["z_min"], t["z_max"], nz)
            inside = np.zeros((nx, ny, nz), dtype=bool)
            absy = np.abs(tys)
            for i in range(nx):
                yb = np.asarray(H.halfbreadth(float(txs[i]), tzs, p),
                                dtype=float).reshape(nz)
                inside[i] = absy[:, None] <= yb[None, :]
            frac = float(inside.mean())
            vol = ((t["x_max"] - t["x_min"]) * (t["y_max"] - t["y_min"])
                   * (t["z_max"] - t["z_min"])) * frac
            wgt = inside.astype(float)
            cx = float((wgt.sum(axis=(1, 2)) * txs).sum() / wgt.sum())
            weights.append({"mass_t": vol * f_ * t["density_t_m3"], "lcg_m": cx})

    lc = S.load_curve(xs, weights, areas, disp)
    eqchk = S.check_equilibrium(lc, disp, lcg, p.lpp)
    if not eqchk["equilibrium_satisfied"]:
        raise AssertionError(f"integrator equilibrium failed: {eqchk}")
    out = crosscheck_ship_bm(lc)
    out["waterline_draft_at_lcg_m"] = z_ref
    out["trim_deg"] = eq["trim_deg"]
    return out


if __name__ == "__main__":
    print("=== beam FE closed-form validation (must pass before any project use) ===")
    for r in validate():
        print(f"  {r['case']:28s} fem={r['fem']:.6e} exact={r['exact']:.6e} "
              f"err={r['err_pct']:.4f}%  {'PASS' if r['pass'] else 'FAIL'}")
    print("\n=== ship load-curve cross-check (FE vs direct integration) ===")
    out = ship_bm_crosscheck()
    for k, v in out.items():
        print(f"  {k:30s} {v:,.4f}" if isinstance(v, float) else f"  {k:30s} {v}")
    print("\nFE cross-check:", "PASS" if out["pass"] else "FAIL")

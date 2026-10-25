"""Diagnose (a) my waterplane polygon integration and (b) navaltoolbox's hull volume."""
import json
import tempfile, os
import numpy as np
import hull_parametric as H
from hydrostatics import Hydrostatics, load_stl, cut_segments, _chain_loops, _loop_moments

p, (V, T), met = H.build_reference_hull(verbose=False)
hy = Hydrostatics(V, T)
draft = 10.1852

print("=== (a) waterplane polygon ===")
segs = cut_segments(hy.V, hy.T, np.array([0.0, 0.0, 1.0]), draft)
print(f"segments: {len(segs)}")
loops = _chain_loops(segs[:, :, :2])
print(f"loops: {len(loops)}  sizes: {[len(l) for l in loops]}")
tot = 0.0
for i, pts in enumerate(loops):
    a, cx, ixx = _loop_moments(pts)
    tot += abs(a)
    print(f"  loop {i}: n={len(pts)} signed_area={a:,.2f} cx={cx:,.3f} "
          f"int_y2dA={ixx:,.1f} x[{pts[:,0].min():.2f},{pts[:,0].max():.2f}] "
          f"y[{pts[:,1].min():.2f},{pts[:,1].max():.2f}]")
print(f"sum |area| = {tot:,.1f}   (parametric Awp = {met['awp_m2']:,.1f})")
print("waterplane_properties:", hy.waterplane_properties(draft))

print("\n=== (b) navaltoolbox on meshes of increasing resolution ===")
from navaltoolbox import Hull, Vessel, HydrostaticsCalculator
for n_st, n_z in ((31, 8), (61, 14), (121, 26), (181, 40)):
    Vc, Tc = H.build_mesh(p, n_st=n_st, n_z=n_z)
    Vc, Tc = H.weld_vertices(Vc, Tc)
    Vc, Tc = H.fix_orientation(Vc, Tc)
    path = os.path.join(tempfile.gettempdir(), f"sds_hull_{n_st}_{n_z}.stl")
    H.write_stl(path, Vc, Tc)
    st = HydrostaticsCalculator(Vessel(Hull(path)), water_density=1.025).from_draft(
        draft=draft, vcg=5.26)
    myhy = Hydrostatics(Vc, Tc)
    myst = myhy.at_draft(draft)
    print(f"  n_st={n_st:4d} n_z={n_z:3d} tris={len(Tc):6d} | "
          f"navaltoolbox vol={st.volume:11.2f} Awp={st.waterplane_area:9.2f} BMt={st.bmt:9.3f} | "
          f"mine vol={myst.volume:11.2f} Awp={myst.awp:9.2f} BMt={myst.bmt:9.3f}")
print(f"  parametric exact          : vol={H.displaced_volume(p):11.2f} "
      f"Awp={met['awp_m2']:9.2f}")

print("\n=== (c) is the hull STL itself sane? ===")
Vl, Tl = load_stl("../reference-case/hull.stl")
print(f"loaded: {len(Vl)} verts {len(Tl)} tris  enclosed vol = {hy.full_volume_m3:,.1f}")
print(f"bounds: x[{Vl[:,0].min():.3f},{Vl[:,0].max():.3f}] "
      f"y[{Vl[:,1].min():.3f},{Vl[:,1].max():.3f}] z[{Vl[:,2].min():.3f},{Vl[:,2].max():.3f}]")
hb = Hull("../reference-case/hull.stl")
vb = Vessel(hb)
print(f"navaltoolbox: tris={hb.num_triangles()} verts={hb.num_vertices()} lbp={vb.lbp} "
      f"bounds={vb.get_bounds()}")

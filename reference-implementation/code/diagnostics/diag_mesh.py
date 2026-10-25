"""Debug the STL reader and the divergence-theorem accumulation on the analytic box."""
import tempfile, os
import numpy as np
from hydrostatics import load_stl, _clip_moment

V, T = load_stl(os.path.join(tempfile.gettempdir(), "sds_box.stl"))
print("vertices:")
for i, v in enumerate(V):
    print(f"  {i}: ({v[0]:8.3f}, {v[1]:8.3f}, {v[2]:8.3f})")
print(f"\ntriangles ({len(T)}):")
for t in T[:6]:
    print("  ", t, V[t])

# raw bytes of the first triangle
import struct
with open(os.path.join(tempfile.gettempdir(), "sds_box.stl"), "rb") as f:
    hdr = f.read(80)
    (n,) = struct.unpack("<I", f.read(4))
    rec = f.read(50)
nrm = struct.unpack("<3f", rec[0:12])
v0 = struct.unpack("<3f", rec[12:24])
v1 = struct.unpack("<3f", rec[24:36])
v2 = struct.unpack("<3f", rec[36:48])
print(f"\nSTL tri0 normal={nrm} v0={v0} v1={v1} v2={v2}  n_tri={n}")

# whole-mesh volume WITHOUT any clipping (all triangles, no half-space)
a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
vol_full = np.einsum('ij,ij->i', a, np.cross(b, c)).sum() / 6.0
print(f"\nfull enclosed volume (no clip) = {vol_full:,.3f} m3   (analytic 20,000.0)")

# clip at z = 6 (draft)
Vz = V - np.array([0.0, 0.0, 6.0])
s6, m2 = _clip_moment(Vz, T, np.array([0.0, 0.0, 1.0]), 0.0)
print(f"clipped submerged volume      = {s6/6:,.3f} m3   (analytic 12,000.0)")
print(f"COB local                     = {(m2/2)/(s6/6)}")

# check each triangle's contribution sign for the clipped case
a2, b2, c2 = Vz[T[:, 0]], Vz[T[:, 1]], Vz[T[:, 2]]
det = np.einsum('ij,ij->i', a2, np.cross(b2, c2))
inside = (a2[:, 2] <= 0).astype(int) + (b2[:, 2] <= 0).astype(int) + (c2[:, 2] <= 0).astype(int)
print("\ntri  count_inside  det/6")
for i in range(len(T)):
    print("  %2d      %d      %12.3f" % (i, inside[i], det[i] / 6.0))

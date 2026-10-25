"""Brute-force check of the divergence-theorem bookkeeping on the clipped unit cube.

True clipped volume (z <= 0.5, unit cube) = 0.5.
This prints every contribution so the missing term is obvious instead of argued about.
"""
import numpy as np

# unit cube, outward normals, 12 triangles
C = np.array([
    [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
    [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1],
], dtype=float)
quads = [
    (0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (3, 7, 6, 2), (0, 4, 7, 3), (1, 2, 6, 5),
]
T = []
for q in quads:
    T.append((q[0], q[1], q[2]))
    T.append((q[0], q[2], q[3]))
T = np.array(T)

full = np.einsum('ij,ij->i', C[T[:, 0]], np.cross(C[T[:, 1]], C[T[:, 2]])).sum() / 6
print(f"full cube volume via tetra formula = {full:.6f}  (truth 1.0)")

zc = 0.5
V = C.copy()
V[:, 2] -= zc                    # waterplane at z = 0


def clip_contrib(a, b, c):
    """Return list of sub-triangles of triangle (a,b,c) that lie in z <= 0."""
    d = np.array([a[2], b[2], c[2]])
    ins = d <= 0
    n_in = int(ins.sum())
    if n_in == 3:
        return [(a, b, c)]
    if n_in == 0:
        return []
    P = [a, b, c]
    if n_in == 1:
        i = int(np.argmax(ins))
        p, q, r = P[i], P[(i + 1) % 3], P[(i + 2) % 3]
        i1 = p + (p[2] / (p[2] - q[2])) * (q - p)
        i2 = p + (p[2] / (p[2] - r[2])) * (r - p)
        return [(p, i1, i2)]
    i = int(np.argmax(~ins))
    p, q, r = P[i], P[(i + 1) % 3], P[(i + 2) % 3]   # p outside
    i1 = p + (p[2] / (p[2] - q[2])) * (q - p)
    i2 = p + (p[2] / (p[2] - r[2])) * (r - p)
    # winding must follow the ORIGINAL triangle orientation: p(outside) -> q -> r
    return [(i1, r, i2), (i1, q, r)]


subs = []
for t in T:
    subs += clip_contrib(V[t[0]], V[t[1]], V[t[2]])
tet = sum(np.dot(p, np.cross(q, r)) / 6 for p, q, r in subs)
print(f"clipped surface, tetra formula     = {tet:.6f}  (truth 0.5)")

# cap polygon at z = 0 (square, CCW seen from +z)
cap = [(np.array([0., 0., 0.]), np.array([1., 0., 0.]), np.array([1., 1., 0.])),
       (np.array([0., 0., 0.]), np.array([1., 1., 0.]), np.array([0., 1., 0.]))]
cap_tet = sum(np.dot(p, np.cross(q, r)) / 6 for p, q, r in cap)
print(f"cap at z=0 contribution            = {cap_tet:.6f}")
print(f"wetted + cap                       = {tet + cap_tet:.6f}")

# x-flux: V = int x n_x dS
def xflux(tris):
    tot = 0.0
    for p, q, r in tris:
        n = np.cross(q - p, r - p)          # 2*A*n_hat
        xc = (p[0] + q[0] + r[0]) / 3.0
        tot += 0.5 * n[0] * xc
    return tot

print(f"\nx-flux over clipped wetted surface = {xflux(subs):.6f}  (truth 0.5)")
print(f"x-flux over cap                    = {xflux(cap):.6f}")
print(f"y-flux over clipped wetted surface = "
      f"{sum(0.5*np.cross(q-p,r-p)[1]*(p[1]+q[1]+r[1])/3 for p,q,r in subs):.6f}")

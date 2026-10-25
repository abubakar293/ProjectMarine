"""Settle the pitch-matrix orientation numerically, from the stated physical requirement.

Requirement: +pitch = bow DOWN, i.e. the hull x-axis (1,0,0) must map to a world vector
with a NEGATIVE z component. Test both candidate matrices and report which one satisfies it.
"""
import math
import numpy as np

pitch = 5.0
cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
x_hat = np.array([1.0, 0.0, 0.0])

cands = {
    "A: [[cp,0,+sp],[0,1,0],[-sp,0,cp]]": np.array([[cp, 0.0, sp], [0.0, 1.0, 0.0], [-sp, 0.0, cp]]),
    "B: [[cp,0,-sp],[0,1,0],[+sp,0,cp]]": np.array([[cp, 0.0, -sp], [0.0, 1.0, 0.0], [sp, 0.0, cp]]),
}
print("pitch = +5 deg, requirement: R @ (1,0,0) must have z < 0 (bow DOWN)\n")
good = None
for name, Ry in cands.items():
    v = Ry @ x_hat
    ok = v[2] < 0
    print(f"  {name}\n     R@(1,0,0) = ({v[0]:+.6f}, {v[1]:+.6f}, {v[2]:+.6f})  ->  "
          f"{'BOW DOWN (correct)' if ok else 'BOW UP (wrong)'}")
    if ok:
        good = (name, Ry)

name, Ry = good
print(f"\nselected: {name}")
print(f"  Ry[:,2] = {Ry[:,2]}   (this is n at zero heel)")

# now the combined R = Rx(heel) @ Ry(pitch) and the closed form of n = R[:,2]
print("\nn = R[:,2] for R = Rx(heel) @ Ry(pitch), vs candidate closed forms:")
print(f"{'heel':>6} {'pitch':>6}   {'numeric n':>34}   {'(ch*sp, sh*cp, ch*cp)':>30}   match")
for heel, pit in ((0, 0), (5, 0), (0, 5), (-5, 0), (0, -5), (10, -3), (30, 10)):
    ch, sh = math.cos(math.radians(heel)), math.sin(math.radians(heel))
    cp2, sp2 = math.cos(math.radians(pit)), math.sin(math.radians(pit))
    Rx = np.array([[1.0, 0.0, 0.0], [0.0, ch, sh], [0.0, -sh, ch]])
    Ry2 = np.array([[cp2, 0.0, sp2], [0.0, 1.0, 0.0], [-sp2, 0.0, cp2]])
    R = Rx @ Ry2
    n = R[:, 2]
    closed = np.array([ch * sp2, sh * cp2, ch * cp2])
    print(f"{heel:6.1f} {pit:6.1f}   ({n[0]:+.6f},{n[1]:+.6f},{n[2]:+.6f})   "
          f"({closed[0]:+.6f},{closed[1]:+.6f},{closed[2]:+.6f})   "
          f"{'YES' if np.allclose(n, closed, atol=1e-12) else 'NO'}")

# verify the heel convention too
print("\nheel convention: Rx(heel) @ (0,1,0) must be (0, ch, -sh)  [starboard DOWN]")
for heel in (5.0, -5.0, 30.0):
    ch, sh = math.cos(math.radians(heel)), math.sin(math.radians(heel))
    Rx = np.array([[1.0, 0.0, 0.0], [0.0, ch, sh], [0.0, -sh, ch]])
    v = Rx @ np.array([0.0, 1.0, 0.0])
    print(f"  heel={heel:+5.1f}: ({v[0]:+.6f},{v[1]:+.6f},{v[2]:+.6f})  expected "
          f"(0,{ch:+.6f},{-sh:+.6f})  {'OK' if np.allclose(v,[0,ch,-sh]) else 'FAIL'}")

"""Ground-truth test: does navaltoolbox agree with analytic geometry on a known shape?

An agent must never assume a third-party solver is right. This checks it against a
wedge/prism whose volume, KB, Awp, BMt and BMl are known in closed form.
"""
import struct
import tempfile
import os
import numpy as np
from navaltoolbox import Hull, Vessel, HydrostaticsCalculator
from hydrostatics import Hydrostatics, load_stl, clip_integrate

L, B, Dm = 100.0, 20.0, 10.0      # prism, wall-sided, flat bottom, no rise of floor
T = 6.0                            # draft


def write_box_stl(path, L=L, B=B, H=Dm):
    """Watertight box from (0,0,0) to (L,B,H), outward normals."""
    x0, x1, y0, y1, z0, z1 = 0.0, L, -B / 2, B / 2, 0.0, H
    corners = np.array([
        [x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
        [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1],
    ])
    quads = [  # (a,b,c,d) counter-clockwise seen from outside
        (0, 3, 2, 1),   # bottom  z=0, normal -z
        (4, 5, 6, 7),   # top     z=H, normal +z
        (0, 1, 5, 4),   # y=y0    normal -y
        (3, 7, 6, 2),   # y=y1    normal +y
        (0, 4, 7, 3),   # x=0     normal -x
        (1, 2, 6, 5),   # x=L     normal +x
    ]
    tris = []
    for q in quads:
        tris.append((q[0], q[1], q[2]))
        tris.append((q[0], q[2], q[3]))
    with open(path, "wb") as f:
        f.write(b"box".ljust(80, b"\0"))
        f.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            pa, pb, pc = corners[a], corners[b], corners[c]
            n = np.cross(pb - pa, pc - pa)
            n = n / np.linalg.norm(n)
            f.write(struct.pack("<3f", *n))
            f.write(struct.pack("<3f", *pa))
            f.write(struct.pack("<3f", *pb))
            f.write(struct.pack("<3f", *pc))
            f.write(struct.pack("<H", 0))


_BOX = os.path.join(tempfile.gettempdir(), "sds_box.stl")
write_box_stl(_BOX)

# ---- analytic truth ----
V_true = L * B * T
KB_true = T / 2
Awp_true = L * B
IT_true = L * B ** 3 / 12
IL_true = B * L ** 3 / 12
BMt_true = IT_true / V_true
BMl_true = IL_true / V_true
LCF_true = L / 2
LCB_true = L / 2
Cb_true = 1.0

print(f"analytic truth  : vol={V_true:,.1f} KB={KB_true:.3f} Awp={Awp_true:,.1f} "
      f"BMt={BMt_true:.4f} BMl={BMl_true:.3f} LCF={LCF_true:.2f} LCB={LCB_true:.2f} Cb={Cb_true}")

# ---- navaltoolbox ----
for rho in (1.025, 1025.0):
    hull = Hull(_BOX)
    ves = Vessel(hull)
    hc = HydrostaticsCalculator(ves, water_density=rho)
    s = hc.from_draft(draft=T, vcg=5.0)
    print(f"navaltoolbox rho={rho:<7}: vol={s.volume:,.1f} KB={s.vcb:.3f} Awp={s.waterplane_area:,.1f} "
          f"BMt={s.bmt:.4f} BMl={s.bml:.3f} LCF={s.lcf:.2f} LCB={s.lcb:.2f} Cb={s.cb:.4f} "
          f"disp={s.displacement:,.1f}")

# ---- own solver on the same STL ----
Vm, Tm = load_stl(_BOX)
hy = Hydrostatics(Vm, Tm)
st = hy.at_draft(T)
print(f"own mesh solver : vol={st.volume:,.1f} KB={st.kb:.3f} Awp={st.awp:,.1f} "
      f"BMt={st.bmt:.4f} BMl={st.bml:.3f} LCF={st.lcf:.2f}")

# ---- raw kernel call, no class wrapper ----
vol, mom = clip_integrate(Vm, Tm, np.array([0.0, 0.0, 1.0]), T)
cob = mom / vol
print(f"raw kernel      : vol={vol:,.1f} COB=({cob[0]:.3f}, {cob[1]:.4f}, {cob[2]:.3f})")

nt = HydrostaticsCalculator(Vessel(Hull(_BOX)), water_density=1025.0).from_draft(draft=T, vcg=5.0)
print("\nquantity        analytic        navaltoolbox        own-solver        nt_err%")
for name, truth, got_nt, got_own in (
    ("volume", V_true, nt.volume, st.volume),
    ("KB", KB_true, nt.vcb, st.kb),
    ("Awp", Awp_true, nt.waterplane_area, st.awp),
    ("BMt", BMt_true, nt.bmt, st.bmt),
    ("BMl", BMl_true, nt.bml, st.bml),
    ("LCF", LCF_true, nt.lcf, st.lcf),
    ("LCB", LCB_true, nt.lcb, float("nan")),
):
    e = 100.0 * (float(got_nt) - truth) / truth if truth else float("nan")
    print(f"{name:12s} {truth:14,.4f} {float(got_nt):18,.4f} {float(got_own):16,.4f} {e:+12.4f}")

"""CI gate: the design record must regenerate byte-identically.

Re-runs the hull generation and compares the STL hash against design_record.json, then
re-runs run_case.py and compares the record's hull hash again. Anything nondeterministic
(unseeded RNG, dict-order leakage, timestamps inside geometry) fails here rather than in
someone's audit trail.
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODE = os.path.normpath(os.path.join(HERE, ".."))
REF = os.path.normpath(os.path.join(CODE, "..", "reference-case"))


def sha16(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def main():
    with open(os.path.join(REF, "design_record.json")) as f:
        rec = json.load(f)
    want = rec["hull"]["hull_stl_sha256"]

    sys.path.insert(0, CODE)
    import hull_parametric as H
    p, (V, T), met = H.build_reference_hull(verbose=False)
    V, T, _ = H.clean_mesh(V, T)
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "sds_determinism_check.stl")
    H.write_stl(tmp, V, T)
    got = sha16(tmp)
    if got != want:
        print(f"FAIL: regenerated hull sha256:{got} != record sha256:{want}")
        return 1
    print(f"OK: hull regenerates identically (sha256:{got})")

    r = subprocess.run([sys.executable, "run_case.py"], cwd=CODE,
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("FAIL: run_case.py did not complete")
        print((r.stdout + r.stderr)[-800:])
        return 1
    with open(os.path.join(REF, "design_record.json")) as f:
        rec2 = json.load(f)
    if rec2["hull"]["hull_stl_sha256"] != want:
        print("FAIL: run_case regenerated a different hull")
        return 1
    for key in ("Cb", "Cm", "Cp", "displaced_volume_m3"):
        if abs(rec2["hull"][key] - rec["hull"][key]) > 1e-9:
            print(f"FAIL: {key} changed on regeneration")
            return 1
    print("OK: full pipeline regeneration is deterministic")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

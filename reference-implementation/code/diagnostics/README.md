# Diagnostics that located specific defects

Kept because each one isolates a failure that would otherwise be invisible in the output.
They are not part of the pipeline; run them only when the corresponding symptom returns.

| File | What it isolates |
|---|---|
| `test_divergence.py` | The divergence-theorem bookkeeping on a clipped unit cube. Proved that the two-inside clipping case was emitting reversed winding (0.000 instead of 0.500). |
| `diag_mesh.py` | Per-triangle contributions for the analytic box. Showed that opposite faces were cancelling, and that the STL reader was fine. |
| `diag_wp.py` | Waterplane polygon extraction, and `navaltoolbox` volume against mesh resolution. Showed the 522 degenerate triangles changing a *correct* solver's volume by −19%. |
| `settle_convention.py` | The heel/pitch rotation convention. Settled numerically, after two wrong hand derivations, which matrix sends the bow down and which sends starboard down. |

The lesson these four files encode: when a number is wrong, build the smallest possible case
with a known answer and print every intermediate term. Reasoning about the algebra produced
two further wrong answers before the numeric test produced the right one.

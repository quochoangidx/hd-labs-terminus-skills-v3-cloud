"""Finding 4: the reference on the panel's small-slope, high-offset batch, against exact arithmetic.
Exit 1 when the batch is inside the task's SOP section 1 and the reference misses the tolerance."""
import json, shutil, subprocess, sys, tempfile
from fractions import Fraction as F
from pathlib import Path
task = Path(sys.argv[1]).resolve()
U = F(1, 2**23); B = F(999999000)
counts = [B, B + 5 * U, B + 11 * U]
batch = {"analytes": [{"name": "A", "mdl": 1, "loq": 5}],
         "standards": [{"conc": {"A": c}, "counts": {"A": float(n)}, "is_counts": 1000} for c, n in zip((0, 500, 1000), counts)],
         "runs": [{"id": "S", "kind": "sample", "counts": {"A": float(B + 7 * U)}, "is_counts": 1000, "dilution": 1}]}
xs = [F(0), F(500), F(1000)]; ys = [n / 1000 for n in counts]
mx, my = sum(xs) / 3, sum(ys) / 3
slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs); icpt = my - slope * mx
exact = ((B + 7 * U) / 1000 - icpt) / slope
sop = (task / "environment/app/docs/reduction-sop.md").read_text()
inside = "at most 10^4 times the slope" not in " ".join(sop.split()) or icpt <= 10**4 * slope
with tempfile.TemporaryDirectory() as tmp:
    shutil.copytree(task / "environment/app", Path(tmp) / "app")
    subprocess.run(["patch", "-p1", "-s", "-i", str(task / "solution/fix.patch")], cwd=tmp, check=True)
    sys.path.insert(0, str(Path(tmp) / "app/src"))
    from metalquant import reduce_batch
    got = reduce_batch(batch)["samples"][0]["value"]
err = abs(got - float(exact)); tol = 1e-6 * abs(float(exact))
print(f"exact reading {float(exact):.9g}; reference {got:.9g}; error {err:.3g} vs tolerance {tol:.3g}; intercept/slope {float(icpt/slope):.3g}; inside SOP section 1: {inside}")
sys.exit(1 if inside and err > tol else 0)

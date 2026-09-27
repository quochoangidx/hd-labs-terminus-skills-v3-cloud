"""Finding 3: the reference (shipped package + solution/fix.patch) on the panel's two on-limit batches.
Exit 1 when the reference's flag differs from the exact-decimal SOP outcome (defect present);
exit 0 when the batches lie outside the task's SOP section 1 (the repaired contract) or the reference agrees.
usage: repro_f3.py TASK_DIR"""
import json, shutil, subprocess, sys, tempfile
from fractions import Fraction
from pathlib import Path

task = Path(sys.argv[1]).resolve()
def std(c, n): return {"conc": {"Pb": c}, "counts": {"Pb": n}, "is_counts": 1000}
def run(i, kind, n, **k): return {"id": i, "kind": kind, "counts": {"Pb": n}, "is_counts": 1000, **k}
A = {"analytes": [{"name": "Pb", "mdl": 0.05, "loq": 0.2}], "standards": [std(0, 0), std(1, 1000), std(2, 2000)],
     "runs": [run("B1", "blank", 100), run("B2", "blank", 200), run("S1", "sample", 350, dilution=1)]}
B = {"analytes": [{"name": "Pb", "mdl": 0.1, "loq": 0.2}], "standards": [std(0, 0), std(1, 1000), std(2, 2000)],
     "runs": [run("B1", "blank", 200), run("S1", "sample", 300, dilution=1)]}
want = {"A": ("", Fraction(1, 5)), "B": ("J", Fraction(1, 10))}   # exact decimal SOP outcome
sop = (task / "environment/app/docs/reduction-sop.md").read_text()
margin = "10^-5" in sop and "never lies within" in sop
with tempfile.TemporaryDirectory() as tmp:
    shutil.copytree(task / "environment/app", Path(tmp) / "app")
    subprocess.run(["patch", "-p1", "-s", "-i", str(task / "solution/fix.patch")], cwd=tmp, check=True)
    sys.path.insert(0, str(Path(tmp) / "app/src"))
    from metalquant import reduce_batch
    bad = 0
    for name, b in (("A", A), ("B", B)):
        got = reduce_batch(b)["samples"][0]
        flag, exact = want[name]
        mdl, loq = (Fraction(str(b["analytes"][0][k])) for k in ("mdl", "loq"))
        inside = not (margin and min(abs(exact - mdl), abs(exact - loq)) <= Fraction(1, 10**5))
        print(name, "reference", json.dumps(got), "exact-decimal flag", repr(flag), "in SOP section 1:", inside)
        bad += inside and got["flag"] != flag
sys.exit(1 if bad else 0)

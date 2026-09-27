"""Fuzz solution/model.py against a package tree (default: the Oracle)."""
import importlib, json, random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
TASK = HERE.parents[2] / "tasks" / "tbrain-medication-adherence-pdc"
sys.path.insert(0, str(TASK / "solution"))
sys.path.insert(0, str(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "oracle" / "app" / "src"))
import model, gen
from pdcmeasure import build_report
N = int(sys.argv[2]) if len(sys.argv) > 2 else 400
bad = 0
for i in range(N):
    rng = random.Random(1000 + i)
    c = gen.claims_file(rng)
    a = json.loads(json.dumps(build_report(json.loads(json.dumps(c)))))
    e = json.loads(json.dumps(model.report(c)))
    if a != e:
        bad += 1
        if bad < 4:
            for x, y in zip(a["members"], e["members"]):
                if x != y: print("M", x, y)
            for x, y in zip(a["classes"], e["classes"]):
                if x != y: print("C", x, y)
print("mismatch", bad, "of", N)

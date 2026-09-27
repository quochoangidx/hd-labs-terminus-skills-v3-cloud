import random, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tasks" / "tbrain-warehouse-cycle-count-variance" / "solution"))
sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else str(HERE / "oracle" / "app" / "src"))
import model
from cyclecount import variance_report
bad = 0
for i in range(800):
    rng = random.Random(i)
    lines = []
    for k in range(rng.randint(1, 30)):
        s = rng.choice([0, 1, 50, 250, 1000, rng.randint(0, 100000)])
        c = max(0, min(100000, s + rng.randint(-60, 60)))
        r = rng.choice([None, max(0, min(100000, s + rng.randint(-60, 60)))])
        lines.append({"sku": f"S{k}", "class": rng.choice("ABCDXZ"), "system": s, "count": c, "recount": r, "unit_cost": rng.randint(1, 1000000)})
    sh = {"sheet": "X", "lines": lines}
    bad += variance_report(sh) != model.report(sh)
print("mismatch", bad)

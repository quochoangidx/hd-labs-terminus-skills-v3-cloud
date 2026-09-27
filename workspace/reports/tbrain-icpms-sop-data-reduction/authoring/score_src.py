"""score_src.py SRC_DIR: compare a candidate package with solution/model.py on fixtures + generated batches."""
import sys, random, importlib, json, collections
from pathlib import Path
TASK = Path(__file__).resolve().parents[3] / "tasks" / "tbrain-icpms-sop-data-reduction"
sys.path.insert(0, str(TASK / "solution"))
import model, jobgen, fixtures
sys.path.insert(0, sys.argv[1])
import metalquant
def eq(x, y):
    if isinstance(y, bool) or y is None or isinstance(y, str): return type(x) == type(y) and x == y
    if isinstance(x, bool) or not isinstance(x, (int, float)): return False
    return abs(x - y) <= (1e-6 * abs(y) if abs(y) >= 1 else 1e-6)
def same(x, y):
    if isinstance(y, dict): return isinstance(x, dict) and set(x) == set(y) and all(same(x[k], y[k]) for k in y)
    if isinstance(y, list): return isinstance(x, list) and len(x) == len(y) and all(same(a, b) for a, b in zip(x, y))
    return eq(x, y)
res = collections.OrderedDict()
for name, batches in fixtures.families().items():
    ok = True
    for b in batches:
        try: ok &= same(json.loads(json.dumps(metalquant.reduce_batch(b))), model.reduce_batch(b))
        except Exception as e: ok = False
    res[name] = ok
rng = random.Random(20260926); bad = 0
for i in range(60):
    b = jobgen.draw_valid(rng, rng.randint(1, 80))
    try: bad += not same(json.loads(json.dumps(metalquant.reduce_batch(b))), model.reduce_batch(b))
    except Exception: bad += 1
res["generated(60)"] = bad == 0
print(json.dumps(res), "fails:", [k for k, v in res.items() if not v])

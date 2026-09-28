"""Print, for one fresh interpreter, the seeds and a digest of every runtime-drawn/relabelled graded job."""
import hashlib, json, random, sys
sys.path.insert(0, sys.path[0])
from load import load
m = load(sys.argv[1])
if hasattr(m, "DRAW_SEEDS"):
    jobs = [m._draw_job(random.Random(s)) for s in m.DRAW_SEEDS]; seeds = list(m.DRAW_SEEDS)
else:
    rng = random.Random(m.DRAW_SEED); jobs = [m._draw_job(rng) for _ in range(4)]; seeds = [m.DRAW_SEED]
names = m.fresh_names(random.Random(m.RELABEL_SEED), 200)
print(json.dumps({"draw_seeds": seeds, "relabel_seed": m.RELABEL_SEED,
  "rate_rows": [len(j["rates"]) for j in jobs],
  "has_2016_01_02": any(r["from"] == "2016-01-02" for j in jobs for r in j["rates"]),
  "draw_digest": hashlib.sha256(json.dumps(jobs, sort_keys=True).encode()).hexdigest()[:16],
  "relabel_digest": hashlib.sha256(json.dumps(names).encode()).hexdigest()[:16]}))

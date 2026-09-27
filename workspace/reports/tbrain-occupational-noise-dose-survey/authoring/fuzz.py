"""fuzz.py N SEED: model (solution/model.py) vs Oracle-patched package on generated surveys over the full section 1 ranges.

Authoring-only harness. It imports the patched package (authoring/patched/app/src) and the model side by side;
the model itself never imports the package. Writes ../receipts/fuzz-model-vs-oracle.json.
"""
import hashlib
import importlib.util
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = HERE.parents[2] / "tasks" / "tbrain-occupational-noise-dose-survey"
sys.path.insert(0, str(HERE / "patched" / "app" / "src"))
import noisedose  # noqa: E402  (the Oracle-patched package)

spec = importlib.util.spec_from_file_location("model", TASK / "solution" / "model.py")
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)
assert "noisedose" not in open(TASK / "solution" / "model.py").read().split('"""', 2)[2], "model mentions the package"

CODE_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
ID_CHARS = CODE_CHARS + "-"
SPECIAL_LEVELS = [0.0, 40.0, 79.9, 80.0, 80.1, 85.0, 115.0, 115.1, 139.9, 140.0]
SPECIAL_PEAKS = [60.0, 139.9, 140.0, 140.1, 170.0]


def level(rng, mode):
    r = rng.random()
    if mode == "quiet":
        return round(rng.uniform(40.0, 79.9), 1)
    if r < 0.08:
        return 0.0
    if r < 0.2:
        return rng.choice(SPECIAL_LEVELS)
    if r < 0.35:
        return round(rng.uniform(40.0, 80.0), 1)
    if r < 0.95:
        return round(rng.uniform(80.0, 105.0), 1)
    return round(rng.uniform(105.0, 140.0), 1)


def log_of(rng, shape):
    if shape == "empty":
        return []
    mode = "quiet" if shape == "quiet" else "normal"
    if shape == "long":
        n = rng.randint(1000, 1500)
    elif shape == "one":
        n = 1
    else:
        n = rng.randint(1, 30)
    budget = 2880
    runs = []
    for _ in range(n):
        if budget - (n - len(runs) - 1) <= 0:
            break
        top = min(1440, budget - (n - len(runs) - 1))
        minutes = rng.choice([1, 1, rng.randint(1, max(1, min(top, 90))), rng.randint(1, top), top]) if top > 1 else 1
        minutes = max(1, min(minutes, top))
        budget -= minutes
        runs.append([minutes, level(rng, mode)])
    if shape == "paused":
        runs = [[m, 0.0] for m, _ in runs]
    return runs


def survey(rng, index):
    n_workers = rng.choice([1, 2, 5, rng.randint(1, 60), rng.randint(1, 300), 300])
    n_codes = rng.randint(1, min(40, n_workers))
    codes = sorted({"".join(rng.choice(CODE_CHARS) for _ in range(rng.randint(1, 8))) for _ in range(n_codes)})
    ids = set()
    workers = []
    for _ in range(n_workers):
        while True:
            wid = "".join(rng.choice(ID_CHARS) for _ in range(rng.randint(1, 12)))
            if wid not in ids:
                ids.add(wid)
                break
        shape = rng.choices(["normal", "empty", "quiet", "paused", "long", "one"], [70, 6, 8, 5, 3, 8])[0]
        if n_workers > 60 and shape == "long":
            shape = "normal"
        peaks = []
        k = rng.choice([0, 0, rng.randint(1, 10), rng.randint(1, 500)])
        for _ in range(k):
            peaks.append(rng.choice(SPECIAL_PEAKS) if rng.random() < 0.1 else round(rng.uniform(60.0, 170.0), 1))
        workers.append({
            "id": wid,
            "group": rng.choice(codes),
            "shift_minutes": rng.choice([60, 480, 600, 720, 1440, rng.randint(60, 1440)]),
            "log": log_of(rng, shape),
            "peaks": peaks,
        })
    return {"survey": f"FUZZ-{index}", "workers": workers}


def same(got, exp, path="$"):
    if type(got) is not type(exp):
        return f"{path}: type {type(got).__name__} != {type(exp).__name__}"
    if isinstance(exp, dict):
        if list(got) != list(exp):
            return f"{path}: keys {list(got)} != {list(exp)}"
        for k in exp:
            d = same(got[k], exp[k], f"{path}.{k}")
            if d:
                return d
        return None
    if isinstance(exp, list):
        if len(got) != len(exp):
            return f"{path}: len {len(got)} != {len(exp)}"
        for i, (g, e) in enumerate(zip(got, exp)):
            d = same(g, e, f"{path}[{i}]")
            if d:
                return d
        return None
    if isinstance(exp, float) and path.endswith(".dose"):
        tol = 1e-9 * abs(exp) if abs(exp) >= 1 else 1e-9
        return None if abs(got - exp) <= tol else f"{path}: {got!r} != {exp!r}"
    return None if got == exp else f"{path}: {got!r} != {exp!r}"


def main():
    n, seed = int(sys.argv[1]), int(sys.argv[2])
    rng = random.Random(seed)
    mismatches, edge_skipped, compared, workers_total = [], 0, 0, 0
    shapes = {"empty_logs": 0, "paused_runs": 0, "threshold_exact": 0, "peak_140": 0, "quiet_workers": 0, "below_three_quarters_nonzero": 0, "below_three_quarters_on_shift_not_480": 0, "full_shift_exact_three_quarters": 0, "readings_above_ceiling": 0}
    for i in range(n):
        s = survey(rng, i)
        workers_total += len(s["workers"])
        for w in s["workers"]:
            shapes["empty_logs"] += not w["log"]
            shapes["paused_runs"] += any(lv == 0.0 for _m, lv in w["log"])
            shapes["threshold_exact"] += any(lv == 80.0 for _m, lv in w["log"])
            shapes["peak_140"] += 140.0 in w["peaks"]
            shapes["quiet_workers"] += bool(w["log"]) and all(40.0 <= lv < 80.0 for _m, lv in w["log"])
            st = model.sampled_time([tuple(x) for x in w["log"]])
            partial = not model.is_full_shift(st, w["shift_minutes"])
            shapes["below_three_quarters_nonzero"] += partial and st > 0
            shapes["below_three_quarters_on_shift_not_480"] += partial and st > 0 and w["shift_minutes"] != 480
            shapes["full_shift_exact_three_quarters"] += 4 * st == 3 * w["shift_minutes"]
            shapes["readings_above_ceiling"] += any(lv > 115.0 for _m, lv in w["log"])
        if model.near_rounding_edge(s):
            edge_skipped += 1
            continue
        got = json.loads(json.dumps(noisedose.build_report(s)))
        exp = json.loads(json.dumps(model.report(s)))
        compared += 1
        d = same(got, exp)
        if d:
            mismatches.append({"survey": i, "diff": d})
    receipt = {
        "status": "pass" if not mismatches else "fail",
        "surveys": n,
        "seed": seed,
        "compared": compared,
        "skipped_near_rounding_half": edge_skipped,
        "workers": workers_total,
        "input_shapes_seen": shapes,
        "mismatches": mismatches[:20],
        "model_sha256": hashlib.sha256((TASK / "solution" / "model.py").read_bytes()).hexdigest(),
        "fix_patch_sha256": hashlib.sha256((TASK / "solution" / "fix.patch").read_bytes()).hexdigest(),
        "comparison": "whole report, type-strict; dose rel 1e-9 (abs 1e-9 below one); everything else exact",
    }
    out = HERE.parent / "receipts" / f"fuzz-model-vs-oracle-seed{seed}.json"
    out.write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps({k: receipt[k] for k in ("status", "compared", "skipped_near_rounding_half", "workers", "input_shapes_seen")}))
    for m in mismatches[:5]:
        print(m)


if __name__ == "__main__":
    main()

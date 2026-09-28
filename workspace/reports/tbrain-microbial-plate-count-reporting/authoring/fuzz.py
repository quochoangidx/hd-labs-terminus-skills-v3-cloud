"""Fuzz solution/model.py against the Oracle-patched package (authoring only).

usage: fuzz.py SEED N OUT.json
Draws N wild batches over the whole SOP 1.3 range (every step, volume, plate count, reading edge,
too-numerous marks, gapped series, every sample shape including both traps) plus N batches from
each gen.py family, and compares the Oracle's report with the model's exactly (type-strict).
"""

import hashlib
import json
import random
import sys
import tempfile
from pathlib import Path

import gen
import trees

EDGES = [0, 1, 19, 20, 21, 24, 25, 250, 251, 299, 300, 301, 5000, None]


def reading(rng):
    u = rng.random()
    if u < 0.3:
        return rng.choice(EDGES)
    if u < 0.55:
        return rng.randint(0, 19)
    if u < 0.8:
        return rng.randint(20, 300)
    if u < 0.95:
        return rng.randint(301, 5000)
    return None


def wild(rng):
    samples = []
    for i in range(rng.randint(1, 30)):
        n = rng.randint(1, 8)
        steps = sorted(rng.sample(range(10), n))
        dils = [{"step": s, "volume": rng.choice([1.0, 0.1]),
                 "plates": [reading(rng) for _ in range(rng.randint(1, 4))]} for s in steps]
        samples.append({"id": f"W{i}", "unit": rng.choice(["g", "mL"]), "dilutions": dils})
    return {"batch": "WILD", "samples": samples}


def strict_equal(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return list(a) == list(b) and all(strict_equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(strict_equal(x, y) for x, y in zip(a, b))
    return a == b


def main(seed, n, out):
    rng = random.Random(seed)
    with tempfile.TemporaryDirectory() as tmp:
        oracle = trees.load(trees.oracle_tree(tmp))
        stats = {"batches": 0, "samples": 0, "mismatches": [], "kinds": {}, "trap_samples": {"T1": 0, "T2": 0}}
        draws = [("wild", wild)] * n + [(f, fn) for f, fn in gen.FAMILIES.items() for _ in range(n)]
        for fam, fn in draws:
            b = fn(rng)
            assert not gen.model.within_limits(b), gen.model.within_limits(b)
            want = gen.model.report(b)
            got = json.loads(json.dumps(oracle.build_report(json.loads(json.dumps(b)))))
            stats["batches"] += 1
            stats["samples"] += len(b["samples"])
            for s, row in zip(b["samples"], want["samples"]):
                stats["kinds"][row["kind"]] = stats["kinds"].get(row["kind"], 0) + 1
                for t, f in (("T1", gen.is_t1), ("T2", gen.is_t2)):
                    stats["trap_samples"][t] += f(s["dilutions"])
            if not strict_equal(got, want):
                stats["mismatches"].append({"family": fam, "batch": b, "got": got, "want": want})
    stats["mismatches"] = stats["mismatches"][:3]
    stats["status"] = "pass" if not stats["mismatches"] else "fail"
    stats["seed"] = seed
    stats["model_sha256"] = hashlib.sha256((gen.TASK / "solution" / "model.py").read_bytes()).hexdigest()
    stats["fix_patch_sha256"] = hashlib.sha256((gen.TASK / "solution" / "fix.patch").read_bytes()).hexdigest()
    Path(out).write_text(json.dumps(stats, indent=1) + "\n")
    print(stats["status"], stats["batches"], stats["samples"], stats["kinds"], stats["trap_samples"])


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3])

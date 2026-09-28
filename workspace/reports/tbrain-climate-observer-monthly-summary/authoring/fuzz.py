"""Fuzz solution/model.py against the Oracle-patched package, in process (authoring only).

python3 fuzz.py SEED COUNT OUT.json
"""
import importlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jobs  # noqa: E402


def load_package(src):
    for name in list(sys.modules):
        if name == "coopsum" or name.startswith("coopsum."):
            del sys.modules[name]
    sys.path.insert(0, str(src))
    try:
        return importlib.import_module("coopsum")
    finally:
        sys.path.pop(0)


def same(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return list(a) == list(b) and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def first_diff(a, b, path="$"):
    if type(a) is not type(b):
        return f"{path}: {a!r} != {b!r}"
    if isinstance(a, dict):
        if list(a) != list(b):
            return f"{path}: keys {list(a)} != {list(b)}"
        for k in a:
            d = first_diff(a[k], b[k], f"{path}.{k}")
            if d:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{path}: len {len(a)} != {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_diff(x, y, f"{path}[{i}]")
            if d:
                return d
        return None
    return None if a == b else f"{path}: {a!r} != {b!r}"


def main():
    seed, count, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    oracle = load_package(HERE / "oracle" / "app" / "src")
    rng = random.Random(seed)
    stats = {"forms": 0, "stations": 0, "morning": 0, "incomplete": 0, "accumulated_at_morning": 0,
             "accumulated_in_next": 0, "extreme_temps": 0, "amount_2000": 0, "mismatches": []}
    for i in range(count):
        form = jobs.rand_form(rng, trap_free=(i % 5 == 0))
        want = jobs.model.summarize(form)
        got = json.loads(json.dumps(oracle.summarize(form)))
        stats["forms"] += 1
        for s, row in zip(form["stations"], want["stations"]):
            stats["stations"] += 1
            stats["morning"] += s["hour"] <= 11
            stats["incomplete"] += not row["complete"]
            acc = jobs.model.accumulated_positions(s)
            stats["accumulated_at_morning"] += bool(acc) and s["hour"] <= 11
            stats["accumulated_in_next"] += (len(s["days"]) + 1) in acc
            ents = s["days"] + [s["next"]]
            stats["extreme_temps"] += any(e[k] in ("130.0", "-60.0") for e in ents for k in ("max", "min"))
            stats["amount_2000"] += any(e["precip"] == "20.00" for e in ents)
        if not same(got, want):
            stats["mismatches"].append({"index": i, "diff": first_diff(got, want)})
    stats["status"] = "pass" if not stats["mismatches"] else "fail"
    stats["seed"] = seed
    Path(out).write_text(json.dumps(stats, indent=1) + "\n")
    print(json.dumps({k: v for k, v in stats.items() if k != "mismatches"}), len(stats["mismatches"]))
    for m in stats["mismatches"][:5]:
        print(m)


if __name__ == "__main__":
    main()

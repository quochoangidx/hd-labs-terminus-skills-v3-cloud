"""Draw realistic batches inside SOP TM-07 section 1, from a fixed seed.

Used by solution/seal.py to write the graded generated batches into
tests/expected/. Every drawn batch is checked against the section 1 limits under
the SOP fit, and every value the SOP judges against a limit is kept at least one
part in 10^5 away from it, so no graded flag depends on rounding. Values that sit
exactly on a limit come only from the hand-built fixtures in solution/fixtures.py.
"""

import math
import random

from model import _line, _reading

POOL = ["Pb", "Cd", "As", "Cu", "Ni", "Zn", "Cr", "Se", "Tl", "Sb", "Mo", "V", "Co", "Ba"]
LEVELS = [0.0, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0, 500.0]
DILUTIONS = [1, 1, 1, 2, 5, 10, 10, 20, 25, 50, 100, 250, 1000]
MARGIN = 1e-5


def _clear(value, limit):
    return abs(value - limit) > MARGIN * max(1.0, abs(limit))


def _analytes(rng, count):
    out = []
    for name in rng.sample(POOL, count):
        mdl = round(rng.choice([0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]) * rng.uniform(0.8, 1.6), 4)
        loq = mdl if rng.random() < 0.1 else round(mdl * rng.choice([2.0, 3.0, 3.18, 4.0, 5.0]), 4)
        out.append({"name": name, "mdl": mdl, "loq": loq})
    return out


def _counts(rng, line, reading, is_counts):
    slope, intercept = line
    return max(0.0, round((intercept + slope * reading) * is_counts, 1))


def draw_batch(rng, size):
    count = rng.choice([1, 1, 2, 2, 3, 4])
    analytes = _analytes(rng, count)
    truth = {a["name"]: (rng.uniform(0.002, 0.4), rng.uniform(0.0005, 0.03)) for a in analytes}
    n_std = rng.randint(3, 8)
    top = rng.choice([50.0, 100.0, 200.0, 500.0])
    levels = sorted(set([0.0] + rng.sample([v for v in LEVELS if 0 < v <= top], min(n_std - 1, len([v for v in LEVELS if 0 < v <= top])))))
    while len(levels) < n_std:
        levels.append(levels[-1])
    standards = []
    for conc in levels[:n_std]:
        is_counts = round(rng.uniform(40000, 60000), 1)
        conc_map, counts = {}, {}
        for a in analytes:
            c = conc if conc == 0 else round(conc * rng.uniform(0.95, 1.05), 3)
            slope, intercept = truth[a["name"]]
            conc_map[a["name"]] = c
            counts[a["name"]] = round((intercept + slope * c) * is_counts * rng.uniform(0.985, 1.015), 1)
        standards.append({"conc": conc_map, "counts": counts, "is_counts": is_counts})
    lines = {a["name"]: _line(standards, a["name"]) for a in analytes}

    kinds = []
    for _ in range(size):
        kinds.append(rng.choices(["sample", "blank", "ccv", "spike"], weights=[6, 2, 2, 2])[0])
    runs = []
    sample_ids = []
    for index, kind in enumerate(kinds):
        is_counts = round(rng.uniform(30000, 65000), 1)
        run = {"id": f"R{rng.randint(100, 999)}-{index}", "kind": kind}
        counts = {}
        if kind == "blank":
            for a in analytes:
                target = rng.choice([-2.0, -0.5, 0.3, 0.8, 1.5, 3.0]) * a["mdl"] * rng.uniform(0.6, 1.4)
                counts[a["name"]] = _counts(rng, lines[a["name"]], target, is_counts)
        elif kind == "ccv":
            run["true"] = {}
            for a in analytes:
                true = round(max(10 * a["loq"], rng.choice([1.0, 5.0, 10.0, 20.0, 50.0])), 3)
                run["true"][a["name"]] = true
                target = true * rng.choice([0.8, 0.8996, 0.9004, 0.95, 1.0, 1.04, 1.1003, 1.1006, 1.12, 1.25])
                counts[a["name"]] = _counts(rng, lines[a["name"]], target, is_counts)
        elif kind == "spike" and sample_ids:
            parent = rng.choice(sample_ids)
            run["parent"] = parent
            run["added"] = {}
            run["dilution"] = rng.choice(DILUTIONS)
            for a in analytes:
                added = round(rng.choice([0.5, 1.0, 5.0, 10.0, 50.0]) * max(a["loq"], 0.05) * run["dilution"] / 5, 4)
                added = min(max(added, 0.01), 1000.0)
                run["added"][a["name"]] = added
                target = rng.choice([-1.0, 0.2, 0.7, 2.0, 5.0, 30.0]) * a["mdl"] + added / run["dilution"] * rng.uniform(0.7, 1.2)
                counts[a["name"]] = _counts(rng, lines[a["name"]], target, is_counts)
        else:
            run["kind"] = "sample"
            run["dilution"] = rng.choice(DILUTIONS)
            for a in analytes:
                target = rng.choice([-1.5, 0.3, 0.9, 1.4, 2.5, 6.0, 40.0, 400.0]) * a["mdl"] * rng.uniform(0.7, 1.3)
                counts[a["name"]] = _counts(rng, lines[a["name"]], target, is_counts)
        run["counts"] = counts
        run["is_counts"] = is_counts
        if run["kind"] == "sample":
            sample_ids.append(run["id"])
        runs.append(run)
    # make ids distinct and keep the key order readable
    seen = set()
    for run in runs:
        while run["id"] in seen:
            run["id"] += "x"
        seen.add(run["id"])
    return {"analytes": analytes, "standards": standards, "runs": runs}


def valid(batch):
    """Section 1 limits under the SOP fit, plus the rounding margin on every judged value."""
    analytes = batch["analytes"]
    runs = batch["runs"]
    if not 1 <= len(runs) <= 80 or not 3 <= len(batch["standards"]) <= 8:
        return False
    ids = [r["id"] for r in runs]
    if len(set(ids)) != len(ids):
        return False
    for a in analytes:
        name = a["name"]
        if len({s["conc"][name] for s in batch["standards"]}) < 2:
            return False
        line = _line(batch["standards"], name)
        if not line[0] > 0:
            return False
        readings = {r["id"]: _reading(r, name, line) for r in runs}
        blanks = [readings[r["id"]] for r in runs if r["kind"] == "blank"]
        if any(not _clear(v, a["mdl"]) for v in blanks):
            return False
        results = [v for v in blanks if v >= a["mdl"]]
        level = sum(results) / len(results) if results else (blanks[0] if blanks else 0.0)
        for r in runs:
            v = readings[r["id"]]
            if r["kind"] == "ccv":
                true = r["true"][name]
                if true < 10 * a["loq"] or not 0.5 * true < v < 1.5 * true:
                    return False
                rec = v / true * 100.0
                half = math.floor(rec * 10) + 0.5
                if not (_clear(rec * 10, half) and _clear(rec * 10, half - 1) and _clear(rec * 10, half + 1)):
                    return False
            if r["kind"] in ("sample", "spike"):
                c = v - level
                if not (_clear(c, a["mdl"]) and _clear(c, a["loq"])):
                    return False
                if abs(c * r["dilution"]) > 1e7:
                    return False
            if r["kind"] == "spike":
                s_amt = (v - level) * r["dilution"]
                p_amt = (readings[r["parent"]] - level) * next(p for p in runs if p["id"] == r["parent"])["dilution"]
                if abs(s_amt - p_amt) < 1e-3 * max(abs(s_amt), abs(p_amt), 1.0):
                    return False
    return True


def draw_valid(rng, size):
    while True:
        batch = draw_batch(rng, size)
        if valid(batch):
            return batch


def batches(seed, sizes):
    rng = random.Random(seed)
    return [draw_valid(rng, size) for size in sizes]

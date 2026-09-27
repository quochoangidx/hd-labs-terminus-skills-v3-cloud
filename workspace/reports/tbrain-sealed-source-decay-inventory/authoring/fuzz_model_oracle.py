"""Fuzz solution/model.py against package variants (shipped, Oracle, natural over-repairs).

Usage: python3 fuzz_model_oracle.py TASK_DIR SCRATCH_DIR OUT_JSON
Builds variants of environment/app under SCRATCH_DIR, runs each over generated inventories
(one subprocess per variant, package imported from that variant's src), and compares to the
model exactly: types strict, floats to 1e-12 relative, everything else equal.
"""

import datetime
import json
import math
import random
import shutil
import subprocess
import sys
from pathlib import Path

TASK = Path(sys.argv[1]).resolve()
SCRATCH = Path(sys.argv[2]).resolve()
OUT = Path(sys.argv[3]).resolve()
sys.path.insert(0, str(TASK / "solution"))
import model  # noqa: E402

NUCLIDES = list(model.TABLE_2)
SHORT = [n for n in NUCLIDES if model.half_life_days(n) <= 120]
D0 = datetime.date(1950, 1, 1).toordinal()
D1 = datetime.date(2099, 12, 31).toordinal()
RUNNER = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from sealsrc import survey
jobs = json.load(open(sys.argv[2]))
out = []
for j in jobs:
    try:
        out.append(survey(j))
    except Exception as exc:
        out.append({"error": type(exc).__name__})
json.dump(out, open(sys.argv[3], "w"))
'''


def iso(n):
    return datetime.date.fromordinal(n).isoformat()


def month_end_or_leap(rng):
    y = rng.randint(1950, 2099)
    if rng.random() < 0.3:
        while not (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)):
            y = rng.randint(1952, 2096)
        return datetime.date(y, 2, 29).toordinal()
    m = rng.randint(1, 12)
    nxt = datetime.date(y + (m == 12), m % 12 + 1, 1) if y < 2099 or m < 12 else datetime.date(2100, 1, 1)
    return nxt.toordinal() - 1


def date_between(rng, lo, hi):
    if rng.random() < 0.25:
        for _ in range(20):
            d = month_end_or_leap(rng)
            if lo <= d <= hi:
                return d
    return rng.randint(lo, hi)


def activity(rng):
    r = rng.random()
    if r < 0.03:
        return 1
    if r < 0.06:
        return 1.0e14
    if r < 0.3:
        return int(10 ** rng.uniform(0, 14))
    return 10 ** rng.uniform(0, 14)


def _current(nuc, ref_bq, t):
    return ref_bq * 2.0 ** (-max(t, 0) / model.half_life_days(nuc))


def gen_inventory(rng, *, future=False, failed_wipes=False, licensing=False, max_entries=60):
    """Trap-free unless a flag asks for a trap input.

    future: some certificates dated after the survey (T1).
    failed_wipes: wipes of 185 Bq or more among an entry's wipes (TA).
    licensing: entries whose certificate is at or below the exempt quantity, and licensed
    entries decayed to or below it (TB). Without it every entry's certificate, current
    parent activity and total activity are all above the exempt quantity.
    """
    survey = date_between(rng, D0 + 400, D1)
    nloc = rng.randint(1, 8)
    locs = [{"id": f"L{rng.randint(0, 99999):05d}-{i}", "limit_bq": 10 ** rng.uniform(0, 18)} for i in range(nloc)]
    if rng.random() < 0.1:
        locs[0]["limit_bq"] = rng.choice([1, 1.0e18])
    sources = []
    for i in range(rng.randint(0, max_entries)):
        for _attempt in range(200):
            nuc = rng.choice(SHORT if rng.random() < 0.3 else NUCLIDES)
            T = model.half_life_days(nuc)
            exq = model.TABLE_2[nuc][2]
            if future and rng.random() < 0.3:
                ref = date_between(rng, survey, D1)
            else:
                ref = date_between(rng, max(D0, survey - int(rng.choice([15, 40]) * T)), survey)
            ref_bq = activity(rng)
            cur = _current(nuc, float(ref_bq), survey - ref)
            if licensing or (ref_bq > exq and cur > exq * 1.000001):
                break
        wipes = []
        for _w in range(rng.choice([0, 1, 2, 3, 5, 50]) if rng.random() < 0.9 else 0):
            wd = date_between(rng, D0, survey)
            if failed_wipes and rng.random() < 0.4:
                rem = rng.choice([185, 185.0, 186, 1.0e6, 10 ** rng.uniform(2.27, 6)])
            else:
                rem = rng.choice([0, 184.99, 184, rng.uniform(0, 184.9)])
            wipes.append({"date": iso(wd), "removable_bq": rem})
        sources.append({
            "id": f"S{i:04d}-{rng.randint(0, 999)}",
            "nuclide": nuc,
            "ref_bq": ref_bq,
            "ref_date": iso(ref),
            "location": rng.choice(locs)["id"],
            "leak_tests": wipes,
        })
    return {"survey_date": iso(survey), "locations": locs, "sources": sources}


def same(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return list(a) == list(b) and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, float):
        return a == b or abs(a - b) <= 1e-12 * max(abs(a), abs(b))
    return a == b


def build_variants():
    base = TASK / "environment" / "app"
    variants = {}
    def make(name, edits):
        root = SCRATCH / name
        if root.exists():
            shutil.rmtree(root)
        shutil.copytree(base, root / "app", ignore=shutil.ignore_patterns("__pycache__"))
        if edits is not None:
            subprocess.run(["patch", "-s", "-p1", "-d", str(root)], input=(TASK / "solution" / "fix.patch").read_bytes(), check=True)
            for rel, old, new in edits:
                p = root / "app" / "src" / "sealsrc" / rel
                s = p.read_text()
                assert old in s, (name, rel, old)
                p.write_text(s.replace(old, new))
        variants[name] = root / "app" / "src"
    make("shipped", None)
    make("oracle", [])
    # T1 natural over-repair: calendar day count without today's stop at nought
    make("t1_overrepair", [("dates.py", "    return max(days, 0)", "    return days")])
    # TA natural over-repair: latest wipe by date whatever it read
    make("tA_overrepair", [("checks.py", 'for w in entry["leak_tests"] if w["removable_bq"] < WIPE_LEAK_BQ]', 'for w in entry["leak_tests"]]')])
    # TB natural over-repairs: licensing judged on today's activity instead of the certificate
    make("tB_current", [("locations.py", 'if entry["ref_bq"] <= exempt_quantity(entry["nuclide"]):', 'if activity <= exempt_quantity(entry["nuclide"]):')])
    make("tB_total", [("locations.py", 'if entry["ref_bq"] <= exempt_quantity(entry["nuclide"]):',
                       'if activity * (1 + __import__("sealsrc.nuclides").nuclides.daughter_of(entry["nuclide"])[1]) <= exempt_quantity(entry["nuclide"]):')])
    make("tB_nofilter", [("locations.py", 'if entry["ref_bq"] <= exempt_quantity(entry["nuclide"]):', 'if False:')])
    # contract-valid alternative: exp(-ln2 t / T) form of the decay law
    make("alt_expform", [("decay.py", "return ref_bq * 2.0 ** (-days / half_life_days(nuclide))",
                          "return ref_bq * __import__('math').exp(-__import__('math').log(2) * days / half_life_days(nuclide))")])
    return variants


def run_variant(src, jobs, tag):
    jp = SCRATCH / f"jobs-{tag}.json"
    op = SCRATCH / f"out-{tag}.json"
    jp.write_text(json.dumps(jobs))
    rs = SCRATCH / "runner.py"
    rs.write_text(RUNNER)
    subprocess.run([sys.executable, "-I", str(rs), str(src), str(jp), str(op)], check=True)
    return json.loads(op.read_text())


def main():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    variants = build_variants()
    rng = random.Random(20260926)
    families = {
        "broad_trap_free": [gen_inventory(rng) for _ in range(300)],
        "with_future_certificates": [gen_inventory(rng, future=True) for _ in range(150)],
        "with_failed_wipes": [gen_inventory(rng, failed_wipes=True) for _ in range(150)],
        "with_licensing_edges": [gen_inventory(rng, licensing=True) for _ in range(150)],
        "large_all_kinds": [gen_inventory(rng, future=True, failed_wipes=True, licensing=True, max_entries=5000) for _ in range(3)],
    }
    result = {"seed": 20260926, "families": {}, "variants": list(variants)}
    for fam, jobs in families.items():
        expect = [model.survey(j) for j in jobs]
        row = {"jobs": len(jobs), "entries": sum(len(j["sources"]) for j in jobs)}
        for name, src in variants.items():
            got = run_variant(src, jobs, f"{fam}-{name}")
            row[name + "_mismatching_jobs"] = sum(0 if same(g, e) else 1 for g, e in zip(got, expect))
        result["families"][fam] = row
        print(fam, row, flush=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()

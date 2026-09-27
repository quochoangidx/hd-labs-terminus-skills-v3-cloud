"""Rough skeleton scorer (task-local-solve-probe, exploratory skeleton mode).

    python3 score_skeleton.py APP_DIR [--task TASK_DIR] [--image TAG] [--json OUT.json]

APP_DIR is a solved copy of environment/app. The scorer draws seeded job directories in one
family per behaviour, runs the candidate through its documented driver inside the task image
(`python3 -I -S /app/tools/coldchain_run.py JOB`, APP_DIR mounted read-only at /app), runs
solution/model.py on the same jobs in the same image, and compares the reports type-strictly.

Families (every family is free of the other families' trap inputs; departures may overlap):
  D1_last_reading           last reading of an export away from the lot's MKT       SOP 2.7, 5.1
  D2_band_ends              readings on the labelled limits and on band ends        SOP 2.1, 2.5
  D3_carry                  lots of 2-5 legs (handover 0)                            SOP 4.1
  D4_prior_time             certificate excursion entries (15 minutes or more)       SOP 2.9, 4.2
  D5_gap_opener_band_time   excursion readings opening gaps, lots of one temperature SOP 2.7, 3.1
  D7_unrounded_compare      MKT just above the upper limit that rounds onto it      SOP 6.2, 1.2
  D8_hours_rounding         minute totals that are not whole hundredths             SOP 1.2
  D9_gap_threshold          31-60 minute spacings in lots of one in-range temp      SOP 2.4, 3.2, 6.2
  TX_gap_minutes_weigh_mkt  gap openers of different temperatures (trap)            SOP 5.1 vs 2.7
  TY_certificate_transients certificate entries under 15 minutes (trap)             SOP 2.6, 2.9
  G_handover_not_bridged    lots with handovers of 1-2,880 minutes                   SOP 2.3, 5.1
  broad                     generated jobs: no gaps, no transients, handovers at 0  all rules
A family passes when every lot of every job matches. The verdict line reports the families.
"""

import argparse
import importlib.util
import json
import random
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve()
DEFAULT_TASK = HERE.parents[3] / "tasks" / "tbrain-cold-chain-lot-disposition"
BASE = datetime(2031, 5, 4, 6, 0)


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def record(rng, allowances=None):
    low = rng.choice([2.0, 2.0, 15.0, -25.0])
    high = low + rng.choice([6.0, 10.0])
    bands = [
        {"band": "cold", "lower_c": round(low - 7.0, 1), "upper_c": low, "allowance_h": 24},
        {"band": "warm", "lower_c": high, "upper_c": round(high + 17.0, 1), "allowance_h": 72},
        {"band": "hot", "lower_c": round(high + 17.0, 1), "upper_c": round(high + 32.0, 1), "allowance_h": 4},
    ]
    if allowances:
        for band in bands:
            band["allowance_h"] = allowances.get(band["band"], band["allowance_h"])
    return {
        "product": "Skeleton product",
        "labelled_range_c": [low, high],
        "freeze_point_c": round(low - 7.0, 1),
        "activation_ratio_k": rng.choice([5000.0, 9880.0, 10000.0, 20000.0]),
        "bands": bands,
    }


def temps_of(rec):
    low, high = rec["labelled_range_c"]
    warm = rec["bands"][1]
    hot = rec["bands"][2]
    cold = rec["bands"][0]
    return {
        "in": lambda rng: round(rng.uniform(low, high), 1),
        "warm": lambda rng: round(rng.uniform(warm["lower_c"] + 0.1, warm["upper_c"]), 1),
        "hot": lambda rng: round(rng.uniform(hot["lower_c"] + 0.1, hot["upper_c"]), 1),
        "cold": lambda rng: round(rng.uniform(cold["lower_c"] + 7.0 - 5.0, cold["upper_c"] - 0.1), 1),
    }


def write_job(path, rec, legs, lots):
    (path / "loggers").mkdir(parents=True)
    for name, rows in legs.items():
        with open(path / "loggers" / f"{name}.csv", "w", encoding="utf-8") as handle:
            handle.write("timestamp,temp_c\n")
            for offset, temp in rows:
                handle.write(f"{BASE + timedelta(minutes=offset):%Y-%m-%dT%H:%M},{temp:.1f}\n")
    (path / "stability.json").write_text(json.dumps(rec), encoding="utf-8")
    (path / "lots.json").write_text(json.dumps(lots), encoding="utf-8")


def leg(rng, start, count, pick, spacing=lambda rng: rng.randint(1, 30), last=None):
    rows, moment = [], start
    for index in range(count):
        if index:
            moment += spacing(rng)
        rows.append((moment, pick(rng)))
    if last is not None:
        rows[-1] = (rows[-1][0], last(rng))
    return rows


def family_jobs(name, rng, jobgen, root):
    """Yield job directories for one family."""
    for index in range(6):
        rec = record(rng)
        t = temps_of(rec)
        mixed = lambda r: t[r.choice(["in", "in", "warm", "hot", "cold"])](r)  # noqa: E731
        path = root / f"{name}-{index}"
        legs, lots = {}, []
        if name == "D1_last_reading":
            for lot in range(3):
                legs[f"a{lot}"] = leg(rng, 0, rng.randint(2, 8), t["in"], last=lambda r: t[r.choice(["warm", "hot", "cold"])](r))
                lots.append({"lot": f"L1{index}{lot}", "legs": [f"a{lot}"]})
        elif name == "D2_band_ends":
            low, high = rec["labelled_range_c"]
            ends = [low, high] + [b[k] for b in rec["bands"] for k in ("lower_c", "upper_c")]
            for lot in range(3):
                legs[f"a{lot}"] = leg(rng, 0, rng.randint(4, 12), lambda r: r.choice(ends), last=t["in"])
                lots.append({"lot": f"L2{index}{lot}", "legs": [f"a{lot}"]})
        elif name == "D3_carry":
            rec = record(rng, {"warm": rng.choice([1, 2, 3])})
            t = temps_of(rec)
            for lot in range(3):
                names, start = [], rng.randint(0, 100)
                for part in range(rng.randint(2, 5)):
                    rows = leg(rng, start, rng.randint(3, 10), lambda r: t[r.choice(["in", "warm", "warm"])](r), last=t["in"])
                    legs[f"a{lot}{part}"] = rows
                    names.append(f"a{lot}{part}")
                    start = rows[-1][0]  # handover at the same minute
                lots.append({"lot": f"L3{index}{lot}", "legs": names})
        elif name == "D4_prior_time":
            for lot in range(3):
                legs[f"a{lot}"] = leg(rng, 0, rng.randint(3, 10), mixed, last=t["in"])
                lots.append({"lot": f"L4{index}{lot}", "legs": [f"a{lot}"], "certificate": {
                    "hot": [rng.choice([200, 225, 229, 230, 15, 10080])],
                    "warm": [rng.randint(15, 3000) for _ in range(rng.randint(0, 5))]}})
        elif name == "D5_gap_opener_band_time":
            for lot in range(3):
                temp = t[rng.choice(["warm", "hot", "cold"])](rng)
                spans = [rng.choice([5, 30])] + [rng.choice([31, 45, 60, 90, 240, 10, 30]) for _ in range(rng.randint(1, 5))]
                rows, moment = [(0, temp)], 0
                for span in spans:
                    moment += span
                    rows.append((moment, temp))
                legs[f"a{lot}"] = rows
                lots.append({"lot": f"L5{index}{lot}", "legs": [f"a{lot}"]})
        elif name == "D7_unrounded_compare":
            high = rec["labelled_range_c"][1]
            for lot in range(3):
                over = rng.choice([3, 4, 5, 6])
                rows = [(0, high), (30, high), (60, high), (90, round(high + 0.1, 1)), (90 + over, high)]
                legs[f"a{lot}"] = rows
                lots.append({"lot": f"L7{index}{lot}", "legs": [f"a{lot}"]})
        elif name == "D8_hours_rounding":
            for lot in range(3):
                legs[f"a{lot}"] = leg(rng, 0, rng.randint(3, 9), lambda r: t[r.choice(["warm", "in"])](r), spacing=lambda r: r.choice([1, 2, 4, 5, 7, 25]), last=t["in"])
                lots.append({"lot": f"L8{index}{lot}", "legs": [f"a{lot}"]})
        elif name == "D9_gap_threshold":
            for lot in range(3):
                temp = t["in"](rng)
                spans = [rng.choice([10, 30])] + [rng.choice([31, 45, 60, 61, 90, 30, 20]) for _ in range(rng.randint(1, 5))]
                rows, moment = [(0, temp)], 0
                for span in spans:
                    moment += span
                    rows.append((moment, temp))
                legs[f"a{lot}"] = rows
                lots.append({"lot": f"L9{index}{lot}", "legs": [f"a{lot}"]})
        elif name == "TX_gap_minutes_weigh_mkt":
            for lot in range(3):
                rows, moment = [(0, t["in"](rng))], 0
                for _ in range(rng.randint(2, 6)):
                    moment += rng.choice([5, 10, 31, 45, 61, 90, 240, 1440])
                    rows.append((moment, t[rng.choice(["warm", "hot", "in"])](rng)))
                moment += 10
                rows.append((moment, t["in"](rng)))
                legs[f"a{lot}"] = rows
                lots.append({"lot": f"LX{index}{lot}", "legs": [f"a{lot}"]})
        elif name == "TY_certificate_transients":
            for lot in range(3):
                legs[f"a{lot}"] = leg(rng, 0, rng.randint(3, 8), mixed, last=t["in"])
                entries = {band: [rng.choice([1, 5, 14, 14, 15, 20, 90]) for _ in range(rng.randint(1, 6))] for band in ("warm", "hot", "cold")}
                if not any(m < 15 for values in entries.values() for m in values):
                    entries["hot"].append(14)
                lots.append({"lot": f"LY{index}{lot}", "legs": [f"a{lot}"], "certificate": entries})
        elif name == "G_handover_not_bridged":
            for lot in range(3):
                names, start = [], 0
                for part in range(rng.randint(2, 4)):
                    rows = leg(rng, start, rng.randint(2, 6), lambda r: t[r.choice(["in", "warm", "hot"])](r), last=t["in"])
                    legs[f"a{lot}{part}"] = rows
                    names.append(f"a{lot}{part}")
                    start = rows[-1][0] + rng.choice([1, 20, 30, 31, 400, 2880])
                lots.append({"lot": f"LG{index}{lot}", "legs": names})
        elif name == "broad":
            jobgen.write_job(path, rng, lots=4, max_legs=5, max_readings=30, gaps=False, handover=0, transients=False, inside=0.8)
            yield path
            continue
        write_job(path, rec, legs, lots)
        yield path


FAMILIES = [
    "D1_last_reading", "D2_band_ends", "D3_carry", "D4_prior_time", "D5_gap_opener_band_time",
    "D7_unrounded_compare", "D8_hours_rounding", "D9_gap_threshold", "TX_gap_minutes_weigh_mkt",
    "TY_certificate_transients", "G_handover_not_bridged", "broad",
]

RUNNER = r"""
import json, subprocess, sys, os
out = {}
for name in sorted(os.listdir('/jobs')):
    cand = subprocess.run(['python3', '-I', '-S', '/app/tools/coldchain_run.py', '/jobs/' + name], capture_output=True, text=True, timeout=120)
    model = subprocess.run(['python3', '-I', '-S', '/solution/model.py', '/jobs/' + name], capture_output=True, text=True, timeout=120)
    out[name] = {'cand': cand.stdout if cand.returncode == 0 else None, 'cand_err': cand.stderr[-400:],
                 'model': model.stdout if model.returncode == 0 else None, 'model_err': model.stderr[-400:]}
json.dump(out, sys.stdout)
"""


def strict_equal(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(strict_equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(strict_equal(x, y) for x, y in zip(a, b))
    return a == b


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("app")
    parser.add_argument("--task", default=str(DEFAULT_TASK))
    parser.add_argument("--image", default="tbrain-cold-chain-lot-disposition:skeleton")
    parser.add_argument("--seed", type=int, default=20260927)
    parser.add_argument("--json")
    args = parser.parse_args()
    task = Path(args.task).resolve()
    app = Path(args.app).resolve()
    jobgen = load_module(task / "solution" / "jobgen.py", "sop_jobgen")
    model = load_module(task / "solution" / "model.py", "sop_model")
    rng = random.Random(args.seed)
    with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
        tmp = Path(tmp)
        jobs = tmp / "jobs"
        jobs.mkdir()
        family_of = {}
        for family in FAMILIES:
            for path in family_jobs(family, rng, jobgen, jobs):
                breaches = model.limit_breaches(path)
                _, margins = model.expected_report(path, with_margins=True)
                if breaches or any(m["mkt_to_upper"] < 0.001 or m["mkt_to_half_tenth"] < 0.0005 for m in margins):
                    shutil.rmtree(path)  # outside SOP 1.4 / 1.5: not graded
                    continue
                family_of[path.name] = family
        appcopy = tmp / "app"
        shutil.copytree(app, appcopy, symlinks=True, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
        (tmp / "runner.py").write_text(RUNNER)
        proc = subprocess.run(
            ["docker", "run", "--rm", "--network", "none",
             "-v", f"{appcopy}:/app:ro", "-v", f"{jobs}:/jobs:ro", "-v", f"{task / 'solution'}:/solution:ro",
             "-v", f"{tmp / 'runner.py'}:/runner.py:ro", args.image, "python3", "-I", "-S", "/runner.py"],
            capture_output=True, text=True,
        )
        if proc.returncode:
            sys.exit("docker run failed: " + proc.stderr[-2000:])
        runs = json.loads(proc.stdout)
    results = {family: {"jobs": 0, "lots": 0, "lots_failed": 0, "errors": 0, "example": None} for family in FAMILIES}
    for job, row in runs.items():
        family = family_of[job]
        entry = results[family]
        entry["jobs"] += 1
        if row["model"] is None:
            sys.exit(f"model failed on {job}: {row['model_err']}")
        want = json.loads(row["model"])["lots"]
        entry["lots"] += len(want)
        if row["cand"] is None:
            entry["errors"] += 1
            entry["lots_failed"] += len(want)
            entry["example"] = entry["example"] or {"job": job, "error": row["cand_err"].strip().splitlines()[-1:]}
            continue
        got = json.loads(row["cand"]).get("lots", [])
        for index, lot in enumerate(want):
            other = got[index] if index < len(got) else None
            if other is None or not strict_equal(lot, other):
                entry["lots_failed"] += 1
                if entry["example"] is None:
                    fields = sorted(k for k in lot if other is None or not strict_equal(lot[k], other.get(k)))
                    entry["example"] = {"job": job, "lot": lot["lot"], "fields": fields}
    failed = [f for f in FAMILIES if results[f]["lots_failed"]]
    for family in FAMILIES:
        entry = results[family]
        status = "PASS" if not entry["lots_failed"] else "FAIL"
        print(f"{status}  {family:24s} lots {entry['lots'] - entry['lots_failed']}/{entry['lots']}" + (f"  e.g. {entry['example']}" if entry["lots_failed"] else ""))
    verdict = "SOLVED (every family passes)" if not failed else f"NOT SOLVED: {len(failed)} famil{'y' if len(failed) == 1 else 'ies'} fail ({', '.join(failed)})"
    print("VERDICT:", verdict)
    if args.json:
        Path(args.json).write_text(json.dumps({"app": str(app), "seed": args.seed, "image": args.image, "families": results, "failed_families": failed, "verdict": verdict}, indent=1) + "\n")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())

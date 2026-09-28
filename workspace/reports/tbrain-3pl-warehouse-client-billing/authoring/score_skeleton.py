"""score_skeleton.py APP_DIR [--image TAG] [--json OUT]: rough skeleton-probe scorer (authoring only).

Runs the candidate package APP_DIR/src through our own pristine copy of the fixed driver (the documented
command, `python3 /app/tools/stockbill_run.py JOB.json`) inside the task environment image, candidate src
mounted read-only, --network none, as an unprivileged uid. Jobs are seeded and generated per family: a
trap-free broad family, one family per departure D1-D9, a governed-minimum family and one per trap T1, T2 (each trap input only in
its own family, checked by the model's predicates). Each statement is compared type-strictly with
solution/model.py. Prints PASS/FAIL per family and a VERDICT line; never shipped in the task.
"""

import argparse
import hashlib
import json
import random
import shutil
import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jobs  # noqa: E402

model = jobs.model
TASK = jobs.TASK
DEFAULT_IMAGE = "tbrain-3pl-warehouse-client-billing:skeleton6"
SEED = 20260927
PER_FAMILY = 8


def iso(d):
    return d.isoformat()



def job_of(rng, start, end, clients, lots, holidays=()):
    return {"statement": f"ST-{rng.randint(0, 99999):05d}", "period": {"start": iso(start), "end": iso(end)},
            "holidays": sorted(set(holidays)), "clients": clients, "lots": lots}


def client(rng, end, pct=0, minimum=0, tiers=None, effs=None):
    effs = effs or [end - timedelta(days=400)]
    revs = []
    for e in effs:
        rates = jobs.rand_rates(rng)
        if tiers:
            rates["storage"] = tiers()
        revs.append({"effective": iso(e), "rates": rates})
    return {"minimum": minimum, "surcharge_percent": pct, "revisions": revs}


def lot(rng, cl, received, pallets, disp=()):
    return {"id": jobs.rand_id(rng), "client": cl, "received": iso(received), "pallets": pallets,
            "dispatches": [{"date": iso(d), "pallets": p} for d, p in disp]}


def period(rng, days=None):
    end = date(2002, 1, 1) + timedelta(days=rng.randint(0, 35000))
    return end - timedelta(days=days if days is not None else rng.randint(14, 61)), end


def pos(rng, hi=100000):
    return lambda: [[None, rng.randint(1, hi)]]


def fam_broad(rng):
    return jobs.broad_job(rng, trap_free=True)


def fam_d1(rng):  # 2.2 a pallet dispatched on a storage week's first day is still on hand that day
    start, end = period(rng, rng.randint(20, 61))
    received = start - timedelta(days=rng.randint(0, 100))
    while received.weekday() != 0:
        received -= timedelta(days=1)
    k = (start - received).days // 7 + 1
    first = received + timedelta(days=7 * k)
    n = rng.randint(2, 1000)
    return job_of(rng, start, end, {"C1": client(rng, end, tiers=pos(rng))},
                  [lot(rng, "C1", received, n, [(first, n)])])


def fam_d2(rng):  # 2.4 storage weeks run from the receipt date, not calendar weeks
    while True:
        start, end = period(rng, rng.randint(14, 61))
        received = start - timedelta(days=rng.randint(0, 200))
        span = [start + timedelta(days=k) for k in range((end - start).days + 1)]
        if received.weekday() != 0 and sum(d.weekday() == 0 for d in span) != sum((d - received).days % 7 == 0 for d in span):
            break
    return job_of(rng, start, end, {"C1": client(rng, end, tiers=pos(rng))}, [lot(rng, "C1", received, rng.randint(1, 1000))])


def fam_d3(rng):  # 2.3/5.2 a public holiday on a weekday is out of hours
    start, end = period(rng)
    day = start + timedelta(days=rng.randint(0, (end - start).days))
    while day.weekday() >= 5:
        day += timedelta(days=1)
    received = start - timedelta(days=rng.randint(0, 6))
    n = rng.randint(2, 1000)
    c = {"C1": client(rng, end)}
    c["C1"]["revisions"][0]["rates"]["handling"] = {"fee": rng.randint(0, 100000), "in": rng.randint(0, 5000),
                                                     "out": rng.randint(0, 5000), "after_hours": rng.randint(5001, 100000)}
    return job_of(rng, start, end, c, [lot(rng, "C1", received, n, [(day, rng.randint(1, n))])], holidays=[iso(day)])


def fam_d4(rng):  # 5.1 a receipt is billed at the receiving rate
    start, end = period(rng)
    received = start + timedelta(days=rng.randint(0, (end - start).days))
    while received.weekday() >= 5:
        received -= timedelta(days=1)
    received = max(received, start)
    if received.weekday() >= 5:
        received += timedelta(days=2)
    c = {"C1": client(rng, end)}
    h = c["C1"]["revisions"][0]["rates"]["handling"]
    h["in"], h["out"] = rng.randint(0, 50000), rng.randint(50001, 100000)
    return job_of(rng, start, end, c, [lot(rng, "C1", received, rng.randint(1, 1000))]) if received <= end else None


def fam_d5(rng):  # 4.2 tiers are not retroactive
    start, end = period(rng, 61)
    received = start - timedelta(days=rng.randint(20, 300))
    first_weeks = (start - received).days // 7

    def tiers():
        return [[max(1, first_weeks + rng.randint(1, 3)), rng.randint(1, 30000)], [rng.randint(1, 3), rng.randint(30001, 60000)],
                [None, rng.randint(60001, 100000)]]
    return job_of(rng, start, end, {"C1": client(rng, end, tiers=tiers)}, [lot(rng, "C1", received, rng.randint(1, 1000))])


def fam_d6(rng):  # 3.1/3.2 the revision in force on the day
    start, end = period(rng, 61)
    mid = start + timedelta(days=rng.randint(10, 50))
    received = start - timedelta(days=rng.randint(0, 20))
    n = rng.randint(2, 1000)
    return job_of(rng, start, end, {"C1": client(rng, end, effs=[end - timedelta(days=400), mid])},
                  [lot(rng, "C1", received, n, [(start + timedelta(days=rng.randint(0, 9)), n // 2), (end, n - n // 2)])])


def fam_d7(rng):  # 6.2/1.3 the surcharge rounds half up
    start, end = period(rng)
    received = start - timedelta(days=rng.randint(0, 60))
    pct = rng.choice([3, 5, 7, 12, 25, 33, 45, 50, rng.randint(1, 50)])
    minimum = rng.choice([0, rng.randint(1, 1000000)])
    job = job_of(rng, start, end, {"C1": client(rng, end, pct, minimum)}, [lot(rng, "C1", received, rng.randint(1, 1000))])
    row = model.report(job)["lots"][0]
    return job if (row["storage"] * pct) % 100 >= 50 else None


def fam_d8(rng):  # 4.5 peak on billed weeks' first days, not on any day
    start, end = period(rng, rng.randint(20, 61))
    received = start - timedelta(days=rng.randint(1, 60))
    n = rng.randint(3, 1000)
    job = job_of(rng, start, end, {"C1": client(rng, end)},
                 [lot(rng, "C1", received, n, [(start + timedelta(days=1), rng.randint(1, n - 1))])])
    row = model.report(job)["lots"][0]
    return job if row["storage_weeks"] and row["peak"] < n else None


def fam_min(rng):  # 4.4 minimum (governed)
    start, end = period(rng)
    received = start - timedelta(days=rng.randint(0, 30))
    job = job_of(rng, start, end, {"C1": client(rng, end, 0, rng.randint(1, 1000000), tiers=pos(rng, 3000))},
                 [lot(rng, "C1", received, rng.randint(1, 20))])
    row = model.report(job)["lots"][0]
    return job if row["storage_weeks"] and row["storage"] == job["clients"]["C1"]["minimum"] else None


def fam_t1(rng):  # trap T1: an entry below nought on the first day of a storage week in the period
    start, end = period(rng, rng.randint(20, 61))
    received = start - timedelta(days=rng.randint(0, 60))
    n = rng.randint(3, 1000)
    k = (start - received).days // 7 + 1
    week = received + timedelta(days=7 * k)
    if week > end:
        return None
    out = rng.randint(2, n)
    gone = week - timedelta(days=rng.randint(1, 6))
    if gone < received:
        return None
    back = -rng.randint(1, out - 1)
    job = job_of(rng, start, end, {"C1": client(rng, end, tiers=pos(rng))},
                 [lot(rng, "C1", received, n, [(gone, out), (week, back)])])
    return job if model.carries_return_on_a_week_start(job) else None


def fam_t2(rng):  # trap T2: a lot that arrived with no pallets within the period (no receipt, so no fee)
    start, end = period(rng)
    received = start + timedelta(days=rng.randint(0, (end - start).days))
    c = {"C1": client(rng, end)}
    c["C1"]["revisions"][0]["rates"]["handling"]["fee"] = rng.randint(1, 100000)
    lots = [lot(rng, "C1", received, 0, [(received, 0)] if rng.random() < 0.3 else [])]
    return job_of(rng, start, end, c, lots)


def fam_d9(rng):  # 5.1 a receipt is billed the receipt fee once
    start, end = period(rng)
    received = start + timedelta(days=rng.randint(0, (end - start).days))
    c = {"C1": client(rng, end)}
    c["C1"]["revisions"][0]["rates"]["handling"]["fee"] = rng.randint(1, 100000)
    return job_of(rng, start, end, c, [lot(rng, "C1", received, rng.randint(1, 1000))])


FAMILIES = {"broad": fam_broad, "D1": fam_d1, "D2": fam_d2, "D3": fam_d3, "D4": fam_d4, "D5": fam_d5,
            "D6": fam_d6, "D7": fam_d7, "D8": fam_d8, "D9": fam_d9, "MIN": fam_min, "T1": fam_t1, "T2": fam_t2}
TRAPS = {"T1": model.carries_entry_below_nought, "T2": model.carries_empty_arrival}


def cases():
    rng = random.Random(SEED)
    out = []
    for fam, gen in FAMILIES.items():
        n = 0
        tries = 0
        while n < PER_FAMILY:
            tries += 1
            assert tries < 20000, fam
            job = gen(rng)
            if job is None:
                continue
            jobs.within_limits(job)
            carried = {t for t, pred in TRAPS.items() if pred(job)}
            if carried != ({fam} if fam in TRAPS else set()):
                continue
            out.append((fam, job))
            n += 1
    return out


def same(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return list(a) == list(b) and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def ensure_image(image):
    if subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode:
        subprocess.run(["docker", "build", "-q", "-t", image, str(TASK / "environment")], check=True)


def score(app_dir, image=DEFAULT_IMAGE, out_json=None):
    app_dir = Path(app_dir).resolve()
    ensure_image(image)
    all_cases = cases()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "tools").mkdir()
        shutil.copy2(TASK / "environment" / "app" / "tools" / "stockbill_run.py", tmp / "tools" / "stockbill_run.py")
        (tmp / "jobs").mkdir()
        for k, (_fam, job) in enumerate(all_cases):
            (tmp / "jobs" / f"{k:04d}.json").write_text(json.dumps(job))
        loop = ('for f in /jobs/*.json; do printf "@@%s\\n" "$(basename "$f")"; '
                'timeout 60 python3 -I -S /app/tools/stockbill_run.py "$f" 2>/dev/null || echo "@@ERROR"; done')
        proc = subprocess.run(["docker", "run", "--rm", "--network", "none", "--user", "65534:65534",
                               "-e", "PYTHONDONTWRITEBYTECODE=1",
                               "-v", f"{app_dir / 'src'}:/app/src:ro", "-v", f"{tmp / 'tools'}:/app/tools:ro",
                               "-v", f"{tmp / 'jobs'}:/jobs:ro", image, "bash", "-c", loop],
                              capture_output=True, text=True, timeout=1800)
    outputs, current = {}, None
    for line in proc.stdout.splitlines():
        if line.startswith("@@") and line.endswith(".json"):
            current = int(line[2:6])
            outputs[current] = None
        elif current is not None and outputs.get(current) is None and line != "@@ERROR":
            try:
                outputs[current] = json.loads(line)
            except ValueError:
                outputs[current] = None
    families = {fam: {"passed": 0, "total": 0} for fam in FAMILIES}
    for k, (fam, job) in enumerate(all_cases):
        families[fam]["total"] += 1
        families[fam]["passed"] += same(outputs.get(k), model.report(job))
    failed = [f for f, c in families.items() if c["passed"] != c["total"]]
    result = {
        "app_dir": str(app_dir), "image": image, "seed": SEED, "per_family": PER_FAMILY,
        "families": families, "failed_families": failed,
        "verdict": "SOLVED" if not failed else "NOT_SOLVED",
        "model_sha256": hashlib.sha256((TASK / "solution" / "model.py").read_bytes()).hexdigest(),
        "driver_sha256": hashlib.sha256((TASK / "environment" / "app" / "tools" / "stockbill_run.py").read_bytes()).hexdigest(),
    }
    if out_json:
        Path(out_json).write_text(json.dumps(result, indent=1) + "\n")
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("app_dir")
    ap.add_argument("--image", default=DEFAULT_IMAGE)
    ap.add_argument("--json", dest="out_json")
    args = ap.parse_args()
    r = score(args.app_dir, args.image, args.out_json)
    for fam, c in r["families"].items():
        print(f"{'PASS' if c['passed'] == c['total'] else 'FAIL'} {fam} {c['passed']}/{c['total']}")
    print(f"VERDICT {r['verdict']} failed={r['failed_families']}")


if __name__ == "__main__":
    main()

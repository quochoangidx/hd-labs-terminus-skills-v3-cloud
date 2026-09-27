"""score_skeleton.py APP_DIR [--image TAG] [--json OUT]: rough skeleton-probe scorer (authoring only).

Runs the candidate package APP_DIR/src through our own pristine copy of the fixed driver (the documented
command, `python3 /app/tools/ddbill_run.py JOB.json`) inside the task environment image, candidate src
mounted read-only, --network none, as an unprivileged uid. Jobs are seeded and generated per family: a
trap-free broad family, one family per departure D1-D7 and one per trap T1, T2 (each trap input only in
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
DEFAULT_IMAGE = "tbrain-container-demurrage-detention:skeleton"
SEED = 20260927
PER_FAMILY = 8


def iso(d):
    return d.isoformat()


def one_rev_contract(rng, cut, t_free, m_free, pct, tiers_fn=None):
    tiers_fn = tiers_fn or (lambda: jobs.rand_scale(rng))
    return {"terminal_free_days": t_free, "merchant_free_days": m_free, "discount_percent": pct,
            "revisions": [{"effective": iso(cut - timedelta(days=400)),
                           "scales": {st: {sz: tiers_fn() for sz in ("20", "40")} for st in ("terminal", "merchant")}}]}


def job_of(rng, cut, contracts, containers, holidays=(), closures=()):
    return {"invoice": f"INV-{rng.randint(0, 99999):05d}", "cut_off": iso(cut), "holidays": sorted(holidays),
            "closures": sorted(closures), "contracts": contracts, "containers": containers}


def box(rng, contract, moves, size=None):
    return {"id": jobs.rand_id(rng, 0), "size": size or rng.choice(["20", "40"]), "contract": contract,
            "history": [{"move": m, "date": iso(d)} for m, d in moves]}


def mid_cut(rng):
    return date(2002, 1, 1) + timedelta(days=rng.randint(0, 35000))


def fam_broad(rng):
    return jobs.broad_job(rng, trap_free=True)


def fam_d1(rng):  # 2.4 days count both ends (returned containers, no free time effects needed)
    cut = mid_cut(rng)
    d0 = cut - timedelta(days=rng.randint(60, 300))
    go = d0 + timedelta(days=rng.randint(0, 20))
    back = go + timedelta(days=rng.randint(0, 20))
    c = {"K1": one_rev_contract(rng, cut, rng.randint(0, 3), rng.randint(0, 3), 0)}
    return job_of(rng, cut, c, [box(rng, "K1", [("DISCHARGE", d0), ("GATE_OUT", go), ("EMPTY_RETURN", back)])])


def fam_d2(rng):  # 3.1 working days: free time spans a weekend and a holiday
    cut = mid_cut(rng)
    d0 = cut - timedelta(days=rng.randint(60, 300))
    while d0.weekday() not in (3, 4):
        d0 += timedelta(days=1)
    hol = [d0 + timedelta(days=rng.choice([4, 5, 6]))]
    go = d0 + timedelta(days=rng.randint(12, 30))
    c = {"K1": one_rev_contract(rng, cut, rng.randint(3, 8), 5, 0)}
    return job_of(rng, cut, c, [box(rng, "K1", [("DISCHARGE", d0), ("GATE_OUT", go), ("EMPTY_RETURN", go)])],
                  holidays=[iso(h) for h in hol if h.weekday() < 5] or [iso(d0 + timedelta(days=6))])


def fam_d3(rng):  # 3.1/4.1 closures: one inside terminal free time on a working day, one after it
    cut = mid_cut(rng)
    d0 = cut - timedelta(days=rng.randint(60, 300))
    while d0.weekday() != 0:
        d0 += timedelta(days=1)
    clo = [d0 + timedelta(days=1), d0 + timedelta(days=rng.randint(9, 12))]
    go = d0 + timedelta(days=rng.randint(14, 25))
    c = {"K1": one_rev_contract(rng, cut, 3, 5, 0)}
    return job_of(rng, cut, c, [box(rng, "K1", [("DISCHARGE", d0), ("GATE_OUT", go), ("EMPTY_RETURN", go)])],
                  closures=[iso(x) for x in clo])


def fam_d4(rng):  # 2.2 merchant stage starts on the gate-out date
    cut = mid_cut(rng)
    d0 = cut - timedelta(days=rng.randint(60, 300))
    go = d0 + timedelta(days=rng.randint(0, 3))
    back = go + timedelta(days=rng.randint(3, 40))
    c = {"K1": one_rev_contract(rng, cut, 20, rng.randint(0, 5), 0)}
    return job_of(rng, cut, c, [box(rng, "K1", [("DISCHARGE", d0), ("GATE_OUT", go), ("EMPTY_RETURN", back)])])


def fam_d5(rng):  # 5.3 incremental tiers on a long terminal stay
    cut = mid_cut(rng)
    d0 = cut - timedelta(days=rng.randint(200, 390))
    go = d0 + timedelta(days=rng.randint(40, 150))

    def tiers():
        return [[rng.randint(2, 10), rng.randint(100, 5000)], [rng.randint(2, 10), rng.randint(5001, 20000)],
                [None, rng.randint(20001, 100000)]]
    c = {"K1": one_rev_contract(rng, cut, 0, 0, 0, tiers)}
    return job_of(rng, cut, c, [box(rng, "K1", [("DISCHARGE", d0), ("GATE_OUT", go), ("EMPTY_RETURN", go)])])


def fam_d6(rng):  # 5.1/5.2 scale in force on the first chargeable day (after the earliest revision)
    cut = mid_cut(rng)
    e0 = cut - timedelta(days=400)
    e1 = cut - timedelta(days=rng.randint(100, 200))
    d0 = e0 + timedelta(days=rng.randint(0, 50))
    go = d0 + timedelta(days=rng.randint(10, 40))
    back = go + timedelta(days=rng.randint(15, 40))
    c = {"K1": {"terminal_free_days": 2, "merchant_free_days": 5, "discount_percent": 0,
                "revisions": [jobs.rand_revision(rng, e0), jobs.rand_revision(rng, e1)]}}
    return job_of(rng, cut, c, [box(rng, "K1", [("DISCHARGE", d0), ("GATE_OUT", go), ("EMPTY_RETURN", back)])])


def fam_d7(rng):  # 6.2/1.3 discount rounds half up (every stage ended)
    for _ in range(500):
        cut = mid_cut(rng)
        d0 = cut - timedelta(days=rng.randint(130, 300))
        go = d0 + timedelta(days=rng.randint(10, 60))
        back = go + timedelta(days=rng.randint(10, 60))
        pct = rng.choice([5, 15, 25, 33, 45, 50, rng.randint(1, 50)])
        c = {"K1": one_rev_contract(rng, cut, rng.randint(0, 5), rng.randint(0, 5), pct,
                                    lambda: [[rng.randint(1, 9), rng.randint(1, 99999)], [None, rng.randint(1, 99999)]])}
        job = job_of(rng, cut, c, [box(rng, "K1", [("DISCHARGE", d0), ("GATE_OUT", go), ("EMPTY_RETURN", back)])])
        row = model.report(job)["containers"][0]
        if (row["amount"] * pct) % 100 >= 50:
            return job
    raise RuntimeError("d7")


def fam_t1(rng):  # trap T1: a container with a running stage, discount leaving half a cent or more
    for _ in range(500):
        cut = mid_cut(rng)
        d0 = cut - timedelta(days=rng.randint(20, 300))
        pct = rng.choice([5, 15, 25, 33, 45, 50, rng.randint(1, 50)])
        c = {"K1": one_rev_contract(rng, cut, rng.randint(0, 5), rng.randint(0, 5), pct,
                                    lambda: [[rng.randint(1, 9), rng.randint(1, 99999)], [None, rng.randint(1, 99999)]])}
        if rng.random() < 0.5:
            moves = [("DISCHARGE", d0)]
        else:
            moves = [("DISCHARGE", d0), ("GATE_OUT", d0 + timedelta(days=rng.randint(0, 15)))]
        job = job_of(rng, cut, c, [box(rng, "K1", moves)])
        if model.carries_running_discount_edge(job):
            return job
    raise RuntimeError("t1")


def fam_t2(rng):  # trap T2: charges began before the contract's earliest effective date (all stages ended)
    for _ in range(500):
        cut = mid_cut(rng)
        d0 = cut - timedelta(days=rng.randint(300, 400))
        e0 = d0 + timedelta(days=rng.randint(10, 60))
        e1 = e0 + timedelta(days=rng.randint(20, 150))
        go = d0 + timedelta(days=rng.randint(3, 8))
        back = go + timedelta(days=rng.randint(0, 5))
        c = {"K1": {"terminal_free_days": rng.randint(0, 2), "merchant_free_days": rng.randint(0, 2),
                    "discount_percent": 0, "revisions": [jobs.rand_revision(rng, e0), jobs.rand_revision(rng, e1)]}}
        job = job_of(rng, cut, c, [box(rng, "K1", [("DISCHARGE", d0), ("GATE_OUT", go), ("EMPTY_RETURN", back)])])
        if not model.carries_pre_sheet_start(job):
            continue
        # the earliest revision must price it differently from the latest, so a natural fallback shows
        alt = json.loads(json.dumps(job))
        alt["contracts"]["K1"]["revisions"][1]["scales"] = alt["contracts"]["K1"]["revisions"][0]["scales"]
        if model.report(alt) != model.report(job):
            return job
    raise RuntimeError("t2")


FAMILIES = {"broad": fam_broad, "D1": fam_d1, "D2": fam_d2, "D3": fam_d3, "D4": fam_d4, "D5": fam_d5,
            "D6": fam_d6, "D7": fam_d7, "T1": fam_t1, "T2": fam_t2}
TRAPS = {"T1": model.carries_running_discount_edge, "T2": model.carries_pre_sheet_start}


def cases():
    rng = random.Random(SEED)
    out = []
    for fam, gen in FAMILIES.items():
        for _ in range(PER_FAMILY):
            job = gen(rng)
            jobs.within_limits(job)
            carried = {t for t, pred in TRAPS.items() if pred(job)}
            assert carried == ({fam} if fam in TRAPS else set()), (fam, carried)
            out.append((fam, job))
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
        shutil.copy2(TASK / "environment" / "app" / "tools" / "ddbill_run.py", tmp / "tools" / "ddbill_run.py")
        (tmp / "jobs").mkdir()
        for k, (_fam, job) in enumerate(all_cases):
            (tmp / "jobs" / f"{k:04d}.json").write_text(json.dumps(job))
        loop = ('for f in /jobs/*.json; do printf "@@%s\\n" "$(basename "$f")"; '
                'timeout 60 python3 -I -S /app/tools/ddbill_run.py "$f" 2>/dev/null || echo "@@ERROR"; done')
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
        "driver_sha256": hashlib.sha256((TASK / "environment" / "app" / "tools" / "ddbill_run.py").read_bytes()).hexdigest(),
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

"""Rough skeleton scorer (task-local-solve-probe, exploratory skeleton mode).

Usage: python3 score_skeleton.py APP_DIR OUT_JSON

Runs the candidate package under APP_DIR (its src/ is used; the driver is the pristine
tools/sealsrc_run.py from the task's environment, never the candidate's) inside the
digest-pinned environment image with --network none and APP_DIR mounted read-only, one
driver process per inventory. Inventories are drawn from fixed seeds per family and the
expected reports come from solution/model.py. Comparison is type-strict; floats pass when
|got - expected| <= 1e-9 * |expected| (manual 1.1 allowance for reported figures).
Each family compares only the part of the report its trap isolation allows (`view`).
Verdict: pass when every family passes.
"""

import datetime
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = HERE.parents[2] / "tasks" / "tbrain-sealed-source-decay-inventory"
sys.path.insert(0, str(TASK / "solution"))
import model  # noqa: E402

IMAGE = "tbrain-ssd-skeleton-env"
NUCLIDES = list(model.TABLE_2)
SHORT = [n for n in NUCLIDES if model.half_life_days(n) <= 120]
D0 = datetime.date(1950, 1, 1).toordinal()
D1 = datetime.date(2099, 12, 31).toordinal()
PASS_WIPE = (0, 184, 184.99)


def iso(n):
    return datetime.date.fromordinal(n).isoformat()


def month_end(rng, lo, hi):
    for _ in range(50):
        y = rng.randint(1950, 2099)
        if rng.random() < 0.3 and y % 4 == 0 and (y % 100 != 0 or y % 400 == 0):
            d = datetime.date(y, 2, 29).toordinal()
        else:
            m = rng.randint(1, 12)
            d = (datetime.date(y + 1, 1, 1) if m == 12 else datetime.date(y, m + 1, 1)).toordinal() - 1
        if lo <= d <= hi:
            return d
    return rng.randint(lo, hi)


def pick_date(rng, lo, hi, month_ends):
    if month_ends or rng.random() < 0.25:
        return month_end(rng, lo, hi)
    return rng.randint(lo, hi)


def current(nuc, ref_bq, t):
    return float(ref_bq) * 2.0 ** (-max(t, 0) / model.half_life_days(nuc))


def entry(rng, i, survey, locs, *, nuclides=None, age=None, future=False, clean=True,
          failed_wipes=False, month_ends=False, shuffle_wipes=False):
    """clean: certificate, current parent and total all above the exempt quantity (no TB input)."""
    for _ in range(300):
        nuc = rng.choice(nuclides or (SHORT if rng.random() < 0.3 else NUCLIDES))
        T = model.half_life_days(nuc)
        exq = model.TABLE_2[nuc][2]
        if future:
            ref = pick_date(rng, survey + 1, D1, month_ends)
        elif age is not None:
            ref = survey - int(age(T))
        else:
            ref = pick_date(rng, max(D0, survey - int(rng.choice([3, 12, 40]) * T)), survey, month_ends)
        if ref < D0:
            continue
        r = rng.random()
        ref_bq = 1 if r < 0.02 else 1.0e14 if r < 0.04 else 10 ** rng.uniform(0, 14)
        if not clean or (ref_bq > exq and current(nuc, ref_bq, survey - ref) > exq * 1.000001):
            break
    wipes = []
    for _ in range(rng.choice([0, 1, 2, 3, 6])):
        rem = rng.choice([185, 186, 1.0e6, 2.0e3]) if failed_wipes and rng.random() < 0.5 else rng.choice(PASS_WIPE)
        wipes.append({"date": iso(pick_date(rng, max(D0, survey - 900), survey, month_ends)), "removable_bq": rem})
    if not shuffle_wipes:
        wipes.sort(key=lambda w: w["date"])
    return {"id": f"E{i:03d}x{rng.randint(0, 99)}", "nuclide": nuc, "ref_bq": ref_bq, "ref_date": iso(ref),
            "location": rng.choice(locs)["id"], "leak_tests": wipes}


def inventory(rng, n=(1, 40), **kw):
    survey = pick_date(rng, D0 + 20000, D1, kw.get("month_ends", False))
    locs = [{"id": f"LOC-{k}{rng.randint(0, 999)}", "limit_bq": 10 ** rng.uniform(0, 18)} for k in range(rng.randint(1, 5))]
    return {"survey_date": iso(survey), "locations": locs,
            "sources": [entry(rng, i, survey, locs, **kw) for i in range(rng.randint(*n))]}


def families():
    """name -> (seed, builder, view). Views: all, rows (per-entry rows), locs (postings)."""
    ten = lambda lo, hi: (lambda rng: lambda T: rng.uniform(lo, hi) * T)  # noqa: E731
    return {
        "broad_trap_free": (101, lambda rng: inventory(rng), "all"),
        "D1_day_count": (102, lambda rng: inventory(rng, month_ends=True, nuclides=SHORT + ["Na-22", "Co-60"]), "all"),
        "D2_year_length": (103, lambda rng: inventory(rng, nuclides=["Na-22", "Co-60", "Cs-137", "Ba-133", "Cf-252"]), "all"),
        "D3_decay_law": (104, lambda rng: inventory(rng), "all"),
        "D4_daughter_branching": (105, lambda rng: inventory(rng, nuclides=["Cs-137", "Sr-90", "Ge-68"]), "all"),
        "D5_exemption_total": (106, lambda rng: inventory(rng, nuclides=["Cs-137", "Sr-90", "Ge-68", "Co-60"], clean=False), "rows"),
        "D6_leak_on_current": (107, lambda rng: inventory(rng, nuclides=["Co-60", "Cs-137", "Am-241", "Po-210", "Ir-192"]), "all"),
        "D7_latest_leak_test": (108, lambda rng: inventory(rng, shuffle_wipes=True), "all"),
        "D8_disposal_ten_half_lives": (109, None, "rows"),
        "D9_store_current_sum": (110, lambda rng: inventory(rng), "locs"),
        "TA_wipe_not_a_leak_test": (201, lambda rng: inventory(rng, failed_wipes=True, shuffle_wipes=True), "all"),
        "TB_licensing_follows_certificate": (202, lambda rng: inventory(rng, clean=False), "locs"),
        "T1_certificate_after_survey": (203, lambda rng: inventory(rng, future=True), "all"),
    }


def d8_inventory(rng):
    inv = inventory(rng, n=(0, 0))
    survey = datetime.date.fromisoformat(inv["survey_date"]).toordinal()
    for i in range(30):
        nuc = rng.choice(SHORT)
        T = model.half_life_days(nuc)
        t = int(rng.uniform(9.9, 10.1) * T)
        inv["sources"].append({"id": f"D8-{i}", "nuclide": nuc, "ref_bq": 10 ** rng.uniform(3, 14),
                               "ref_date": iso(survey - t), "location": inv["locations"][0]["id"], "leak_tests": []})
    return inv


def view(rep, v):
    if not isinstance(rep, dict) or "sources" not in rep:
        return rep
    if v == "rows":
        return rep["sources"]
    if v == "locs":
        return rep["locations"]
    return rep


def same(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return list(a) == list(b) and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, float):
        return abs(a - b) <= 1e-9 * abs(b)
    return a == b


def ensure_image():
    if subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode != 0:
        subprocess.run(["docker", "build", "-q", "-t", IMAGE, str(TASK / "environment")], check=True, capture_output=True)


def run_candidate(app_dir, jobs):
    work = Path(tempfile.mkdtemp(prefix="ssd-skel-"))
    try:
        (work / "jobs").mkdir()
        (work / "out").mkdir()
        (work / "drv" / "tools").mkdir(parents=True)
        shutil.copy(TASK / "environment" / "app" / "tools" / "sealsrc_run.py", work / "drv" / "tools" / "sealsrc_run.py")
        (work / "drv" / "src").symlink_to("/app/src")
        for k, job in enumerate(jobs):
            (work / "jobs" / f"{k:05d}.json").write_text(json.dumps(job))
        script = ("for f in /work/jobs/*.json; do b=$(basename $f); "
                  "timeout 60 python3 -I /work/drv/tools/sealsrc_run.py $f > /work/out/$b 2>/dev/null || echo ERR > /work/out/$b; done")
        subprocess.run(["docker", "run", "--rm", "--network", "none", "-v", f"{Path(app_dir).resolve()}:/app:ro",
                        "-v", f"{work}:/work", IMAGE, "bash", "-c", script], check=True, capture_output=True)
        out = []
        for k in range(len(jobs)):
            text = (work / "out" / f"{k:05d}.json").read_text()
            try:
                out.append(json.loads(text))
            except json.JSONDecodeError:
                out.append({"error": text.strip()[:200]})
        return out
    finally:
        shutil.rmtree(work, ignore_errors=True)


def score(app_dir, per_family=25):
    ensure_image()
    fams = families()
    all_jobs, index = [], []
    for name, (seed, build, _v) in fams.items():
        rng = random.Random(seed)
        for _ in range(per_family):
            all_jobs.append(d8_inventory(rng) if build is None else build(rng))
            index.append(name)
    got = run_candidate(app_dir, all_jobs)
    result = {}
    for name, job, g in zip(index, all_jobs, got):
        v = fams[name][2]
        ok = same(view(g, v), view(model.survey(job), v))
        row = result.setdefault(name, {"view": v, "jobs": 0, "passed": 0})
        row["jobs"] += 1
        row["passed"] += int(ok)
    for row in result.values():
        row["status"] = "pass" if row["passed"] == row["jobs"] else "fail"
    return {"app_dir": str(Path(app_dir).resolve()), "families": result,
            "verdict": "pass" if all(r["status"] == "pass" for r in result.values()) else "fail"}


if __name__ == "__main__":
    report = score(sys.argv[1])
    Path(sys.argv[2]).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v["status"] for k, v in report["families"].items()}), report["verdict"])

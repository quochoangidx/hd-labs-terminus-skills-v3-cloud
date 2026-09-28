"""score_skeleton.py APP_DIR OUT_JSON: rough skeleton-probe scorer for tbrain-occupational-noise-dose-survey.

Runs the candidate package APP_DIR/src through our own pristine copy of the fixed driver (the documented
command, `python3 .../tools/noisedose_run.py SURVEY.json`) inside the digest-pinned task environment image,
with the candidate src mounted read-only and --network none. Surveys are seeded and generated per family
(trap-free broad; one family per departure D1-D10 and D9b; one per trap-shaped input T1, T3, T4, each isolated) and compared
type-strictly with solution/model.py (dose within 1e-6 relative, or 1e-6 absolute below one; everything else
exact). Writes per-family pass counts and a verdict. Authoring-only: never shipped in the task.
"""

import hashlib
import importlib.util
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = HERE.parents[2] / "tasks" / "tbrain-occupational-noise-dose-survey"
IMAGE = "tbrain-noise-skeleton:env"
SEED = 20260926
PER_FAMILY = 6

spec = importlib.util.spec_from_file_location("model", TASK / "solution" / "model.py")
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


def lv(rng, lo, hi):
    return round(rng.uniform(lo, hi), 1)


def W(wid, group, shift, log, peaks=()):
    return {"id": wid, "group": group, "shift_minutes": shift, "log": [list(r) for r in log], "peaks": list(peaks)}


def full_counted_log(rng, shift, lo=81.0, hi=105.0, frac=(0.8, 1.2)):
    """Counted readings only, sampled time a full-shift share of the shift (>= 3/4), within 2,880 minutes."""
    total = min(2800, max(-(-3 * shift // 4), int(shift * rng.uniform(*frac))))
    runs, left = [], total
    while left > 0:
        m = min(left, rng.randint(1, 240))
        runs.append((m, lv(rng, lo, hi)))
        left -= m
    return runs


def fam_broad(rng, i):
    workers = []
    codes = ["".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(rng.randint(1, 8))) for _ in range(rng.randint(1, 6))]
    for k in range(rng.randint(1, 25)):
        shift = rng.choice([60, 360, 480, 600, 720, 1440, rng.randint(60, 1440)])
        log = full_counted_log(rng, shift, 81.0, 112.0)
        if rng.random() < 0.5:  # add below-threshold readings while staying full-shift
            log.append((rng.randint(1, 60), lv(rng, 40.0, 79.9)))
        peaks = [lv(rng, 60.0, 139.9) for _ in range(rng.randint(0, 8))]
        workers.append(W(f"W{k}", rng.choice(codes), shift, log, peaks))
    return workers


def fam_d1(rng, i):  # 3.1 reference duration
    return [W("A1", "G1", 480, [(480, lv(rng, 81.0, 110.0))])]


def fam_d2(rng, i):  # 2.3 a reading at 80.0 counts
    m = rng.randint(60, 420)
    return [W("A1", "G1", 480, [(m, 80.0), (480 - m, lv(rng, 81.0, 100.0))])]


def fam_d3(rng, i):  # 2.4 sampled time includes below-threshold readings
    a = rng.randint(150, 300)
    b = rng.randint(max(1, 380 - a), 460 - a)
    return [W("A1", "G1", 480, [(a, lv(rng, 85.0, 100.0)), (b, lv(rng, 40.0, 79.9))])]


def fam_d4(rng, i):  # 3.3 full-shift projection to the worker's own shift
    shift = rng.randint(500, 1440)
    sampled = rng.randint(-(-3 * shift // 4), shift - 1)
    return [W("A1", "G1", shift, [(sampled, lv(rng, 81.0, 100.0))]), W("A2", "G2", 360, [(rng.randint(361, 600), lv(rng, 81.0, 100.0))])]


def fam_d5(rng, i):  # 4.1 TWA formula
    return [W("A1", "G1", 480, full_counted_log(rng, 480, 81.0, 100.0, (1.0, 1.0)))]


def fam_d6(rng, i):  # 1.2 nearest tenth
    while True:
        log = [(300, lv(rng, 81.0, 95.0)), (180, lv(rng, 81.0, 95.0))]
        t = model.twa_unrounded(model.shift_dose(log, 480))
        if 0.55 <= (t * 10) % 1 <= 0.95:
            return [W("A1", "G1", 480, log)]


def fam_d7(rng, i):  # 5.3 bands
    return [W(f"A{k}", f"G{k}", 480, [(480, level)]) for k, level in enumerate([82.0, 85.0, lv(rng, 82.0, 85.0)])]


def fam_d8(rng, i):  # 5.2 impulse at 140.0
    return [W("A1", "G1", 480, [(480, lv(rng, 81.0, 81.9))], [lv(rng, 60.0, 139.9), 140.0])]


def fam_d9(rng, i):  # 6.1 mean of doses
    return [W(f"A{k}", "G1", 480, [(480, lv(rng, 81.0, 100.0))]) for k in range(rng.randint(2, 5))]


def fam_d9b(rng, i):  # 6.1 quiet member counts
    return [W("A1", "G1", 480, [(480, lv(rng, 86.0, 100.0))]), W("Q1", "G1", 480, [(480, lv(rng, 40.0, 79.9))])]


def fam_d10(rng, i):  # 2.5 exactly three quarters is full-shift
    shift = 4 * rng.randint(125, 360)
    return [W("A1", "G1", shift, [(3 * shift // 4, lv(rng, 85.5, 100.0))])]


def fam_t1(rng, i):  # trap T1: runs at 0.0 are not readings (full-shift surveys, counted readings only)
    total = rng.randint(360, 470)
    log, left = [], total
    while left > 0:
        m = min(left, rng.randint(40, 200))
        log.append((m, lv(rng, 85.5, 100.0)))
        left -= m
    for _ in range(rng.randint(1, 3)):
        log.insert(rng.randint(0, len(log)), (rng.randint(5, 60), 0.0))
    return [W("B1", "G1", 480, log)]


def fam_t3(rng, i):  # trap T3: a survey below three quarters of a shift other than 480 minutes
    shift = rng.choice([60, 90, 360, 600, 720, 1000, 1440])
    sampled = rng.randint(1, -(-3 * shift // 4) - 1)
    return [W("X1", "G1", shift, [(sampled, lv(rng, 85.5, 100.0))])]


def fam_t4(rng, i):  # trap T4: a reading above the ceiling level (full-shift survey, no run at 0.0)
    shift = rng.choice([480, 600, 720])
    total = rng.randint(-(-3 * shift // 4), shift + 60)
    loud = [(rng.randint(1, 30), lv(rng, 115.1, 140.0)) for _ in range(rng.randint(1, 2))]
    left = total - sum(m for m, _ in loud)
    log = list(loud)
    while left > 0:
        m = min(left, rng.randint(40, 240))
        log.append((m, lv(rng, 81.0, 100.0)))
        left -= m
    rng.shuffle(log)
    return [W("Y1", "G1", shift, log)]


FAMILIES = {
    "broad": fam_broad, "D1": fam_d1, "D2": fam_d2, "D3": fam_d3, "D4": fam_d4, "D5": fam_d5, "D6": fam_d6,
    "D7": fam_d7, "D8": fam_d8, "D9": fam_d9, "D9b": fam_d9b, "D10": fam_d10, "T1": fam_t1, "T3": fam_t3,
    "T4": fam_t4,
}
TRAP_FAMILIES = {"T1", "T3", "T4"}


def trap_inputs(survey):
    """Which trap inputs a survey carries (0.0 runs; a nonzero survey below three quarters)."""
    out = set()
    for w in survey["workers"]:
        log = [tuple(r) for r in w["log"]]
        if any(level == 0.0 for _m, level in log):
            out.add("T1")
        if any(level > 115.0 for _m, level in log):
            out.add("T4")
        st = model.sampled_time(log)
        if not model.is_full_shift(st, w["shift_minutes"]):
            out.add("T3")
    return out


def surveys():
    rng = random.Random(SEED)
    out = []
    for fam, gen in FAMILIES.items():
        n = 0
        while n < PER_FAMILY:
            s = {"survey": f"S-{fam}-{n}", "workers": gen(rng, n)}
            if model.near_rounding_edge(s):
                continue
            carried = trap_inputs(s)
            want = {fam} if fam in TRAP_FAMILIES else set()
            assert carried == want, (fam, carried)
            out.append((fam, s))
            n += 1
    return out


def same(got, exp):
    if type(got) is not type(exp):
        return False
    if isinstance(exp, dict):
        return list(got) == list(exp) and all(same(got[k], exp[k]) for k in exp)
    if isinstance(exp, list):
        return len(got) == len(exp) and all(same(g, e) for g, e in zip(got, exp))
    return got == exp


def matches(got, exp):
    if not isinstance(got, dict) or list(got) != list(exp):
        return False
    if not isinstance(got.get("workers"), list) or not isinstance(got.get("groups"), list):
        return False
    if got["survey"] != exp["survey"] or len(got["groups"]) != len(exp["groups"]) or len(got["workers"]) != len(exp["workers"]):
        return False
    if not all(isinstance(r, dict) and "dose" in r for r in got["workers"] + got["groups"]):
        return False
    if not same([dict(g, dose=0) for g in got["groups"]], [dict(g, dose=0) for g in exp["groups"]]):
        return False
    if not same([dict(w, dose=0) for w in got["workers"]], [dict(w, dose=0) for w in exp["workers"]]):
        return False
    for g, e in zip(got["workers"] + got["groups"], exp["workers"] + exp["groups"]):
        if type(g["dose"]) is not float:
            return False
        tol = 1e-6 * abs(e["dose"]) if abs(e["dose"]) >= 1 else 1e-6
        if abs(g["dose"] - e["dose"]) > tol:
            return False
    return True


def ensure_image():
    if subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode:
        subprocess.run(["docker", "build", "-q", "-t", IMAGE, str(TASK / "environment")], check=True, capture_output=True)


def score(app_dir, out_json):
    app_dir = Path(app_dir).resolve()
    ensure_image()
    cases = surveys()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "tools").mkdir()
        shutil.copy2(TASK / "environment" / "app" / "tools" / "noisedose_run.py", tmp / "tools" / "noisedose_run.py")
        (tmp / "surveys").mkdir()
        for k, (_fam, s) in enumerate(cases):
            (tmp / "surveys" / f"{k:04d}.json").write_text(json.dumps(s))
        loop = ('for f in /surveys/*.json; do printf "@@%s\\n" "$(basename "$f")"; '
                'timeout 60 python3 /cand/tools/noisedose_run.py "$f" 2>/dev/null || echo "@@ERROR"; done')
        proc = subprocess.run(["docker", "run", "--rm", "--network", "none", "--user", "65534:65534",
                               "-v", f"{app_dir / 'src'}:/cand/src:ro", "-v", f"{tmp / 'tools'}:/cand/tools:ro",
                               "-v", f"{tmp / 'surveys'}:/surveys:ro", IMAGE, "bash", "-c", loop],
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
    for k, (fam, s) in enumerate(cases):
        families[fam]["total"] += 1
        families[fam]["passed"] += matches(outputs.get(k), model.report(s))
    failed = sorted(f for f, c in families.items() if c["passed"] != c["total"])
    result = {
        "app_dir": str(app_dir),
        "image": IMAGE,
        "seed": SEED,
        "per_family": PER_FAMILY,
        "families": families,
        "failed_families": failed,
        "verdict": "solved" if not failed else "not_solved",
        "model_sha256": hashlib.sha256((TASK / "solution" / "model.py").read_bytes()).hexdigest(),
        "driver_sha256": hashlib.sha256((TASK / "environment" / "app" / "tools" / "noisedose_run.py").read_bytes()).hexdigest(),
    }
    Path(out_json).write_text(json.dumps(result, indent=1) + "\n")
    return result


if __name__ == "__main__":
    r = score(sys.argv[1], sys.argv[2])
    print(r["verdict"], r["failed_families"])

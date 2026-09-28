"""skeleton_score.py APP_DIR [--image TAG] [--json OUT] [--per-family N]

Skeleton-probe scorer for tbrain-cems-hourly-emission-averaging (authoring only, never shipped).

APP_DIR is a solver's copy of environment/app; its src/ is scored. The candidate package runs through
our own pristine copy of the fixed driver with the documented command
`python3 /app/tools/cemsqr_run.py JOB.json`, inside the task environment image, candidate src and
driver mounted read-only, as uid 65534, with --network none. Jobs are seeded (SEED) and generated per
family by authoring/gen.py: a trap-free `broad` family, one family per departure D1-D9 and one per
trap T1, T2 (each trap's inputs only in its own family; asserted). Each output is compared whole and
type-strictly with solution/model.py. Prints PASS/FAIL per family with the first differing field path,
then a VERDICT line; --json writes a receipt.
"""

import argparse
import hashlib
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "authoring"))
import gen  # noqa: E402

SEED = 20260927
DRIVER = gen.TASK / "environment" / "app" / "tools" / "cemsqr_run.py"
IMAGE = "tbrain-cems-hourly-emission-averaging:skeleton2"
FAMILY_NOTES = {
    "broad": "trap-free mix of every governed hour shape over 31-38 days",
    "D1": "3.1 hourly averages over valid readings only",
    "D2": "2.3 valid hour: every operating quarter, or two with a CAL record",
    "D3": "3.2 firing-hour correction with 209",
    "D4": "3.3 mass rate from the measured NOx average",
    "D5": "5.1 quarter mass uses the operating time",
    "D6": "4.2-4.3 lost hours: before/after average, one side, nought",
    "D7": "6.1 window of thirty operating days",
    "D8": "6.1 rolling average over valid hours' concentrations",
    "D9": "6.2 exceedance only above the limit",
    "T1": "trap: an operating hour neither valid nor lost keeps today's figures (last valid hour's)",
    "T2": "trap: a valid hour that is not a firing hour keeps today's correction (oxygen held at 190, 210)",
}


def first_difference(got, exp, path="$"):
    if type(got) is not type(exp):
        return f"{path} (type {type(got).__name__} != {type(exp).__name__})"
    if isinstance(exp, dict):
        if list(got) != list(exp):
            return f"{path} (keys {list(got)} != {list(exp)})"
        for k in exp:
            d = first_difference(got[k], exp[k], f"{path}.{k}")
            if d:
                return d
        return None
    if isinstance(exp, list):
        if len(got) != len(exp):
            return f"{path} (length {len(got)} != {len(exp)})"
        for i, (g, e) in enumerate(zip(got, exp)):
            d = first_difference(g, e, f"{path}[{i}]")
            if d:
                return d
        return None
    return None if got == exp else f"{path} ({got!r} != {exp!r})"


def jobs(per_family):
    rng = random.Random(SEED)
    out = []
    for fam, fn in gen.FAMILIES.items():
        for _ in range(per_family):
            job = fn(rng)
            assert not gen.model.within_limits(job), (fam, gen.model.within_limits(job)[:3])
            want = {fam} if fam in gen.TRAP_FAMILIES else set()
            assert gen.trap_inputs(job) == want, (fam, gen.trap_inputs(job))
            out.append((fam, job))
    return out


def run_candidate(app_dir, image, cases):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "tools").mkdir()
        shutil.copy2(DRIVER, tmp / "tools" / "cemsqr_run.py")
        (tmp / "jobs").mkdir()
        for k, (_fam, job) in enumerate(cases):
            (tmp / "jobs" / f"{k:04d}.json").write_text(json.dumps(job))
        for p in [tmp, tmp / "tools", tmp / "jobs"] + list((tmp / "jobs").iterdir()) + [tmp / "tools" / "cemsqr_run.py"]:
            p.chmod(0o755 if p.is_dir() else 0o644)
        loop = ('for f in /jobs/*.json; do printf "@@%s\\n" "$(basename "$f")"; '
                'timeout 120 python3 /app/tools/cemsqr_run.py "$f" 2>/dev/null || echo "@@ERROR"; done')
        proc = subprocess.run(
            ["docker", "run", "--rm", "--network", "none", "--user", "65534:65534",
             "-e", "PYTHONDONTWRITEBYTECODE=1",
             "-v", f"{Path(app_dir).resolve() / 'src'}:/app/src:ro", "-v", f"{tmp / 'tools'}:/app/tools:ro",
             "-v", f"{tmp / 'jobs'}:/jobs:ro", image, "bash", "-c", loop],
            capture_output=True, text=True, timeout=3600)
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
    return outputs, proc.returncode, proc.stderr[-2000:]


def score(app_dir, image, out_json, per_family):
    cases = jobs(per_family)
    outputs, rc, err = run_candidate(app_dir, image, cases)
    families = {f: {"passed": 0, "total": 0, "first_difference": None, "note": FAMILY_NOTES[f]} for f in gen.FAMILIES}
    for k, (fam, job) in enumerate(cases):
        exp = gen.model.report(job)
        got = outputs.get(k)
        diff = "no output" if got is None else first_difference(got, exp)
        families[fam]["total"] += 1
        if diff is None:
            families[fam]["passed"] += 1
        elif families[fam]["first_difference"] is None:
            families[fam]["first_difference"] = f"job {k}: {diff}"
    failed = [f for f, c in families.items() if c["passed"] != c["total"]]
    for fam, c in families.items():
        status = "PASS" if c["passed"] == c["total"] else "FAIL"
        extra = "" if status == "PASS" else f"  first difference: {c['first_difference']}"
        print(f"{status} {fam:6s} {c['passed']}/{c['total']}{extra}")
    verdict = "solved" if not failed else "not_solved"
    print(f"VERDICT {verdict} failed={failed}")
    if rc != 0 and err:
        print("docker stderr tail:", err, file=sys.stderr)
    result = {
        "app_dir": str(Path(app_dir).resolve()),
        "image": image,
        "image_id": subprocess.run(["docker", "image", "inspect", image, "--format", "{{.Id}}"],
                                   capture_output=True, text=True).stdout.strip(),
        "docker_exit": rc,
        "seed": SEED,
        "per_family": per_family,
        "families": families,
        "failed_families": failed,
        "verdict": verdict,
        "model_sha256": hashlib.sha256((gen.TASK / "solution" / "model.py").read_bytes()).hexdigest(),
        "gen_sha256": hashlib.sha256((HERE / "authoring" / "gen.py").read_bytes()).hexdigest(),
        "driver_sha256": hashlib.sha256(DRIVER.read_bytes()).hexdigest(),
    }
    if out_json:
        Path(out_json).write_text(json.dumps(result, indent=1) + "\n")
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("app_dir", help="a solved copy of environment/app (its src/ is scored)")
    ap.add_argument("--image", default=IMAGE)
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--per-family", type=int, default=4)
    a = ap.parse_args()
    score(a.app_dir, a.image, a.json_out, a.per_family)

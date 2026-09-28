"""score_skeleton.py APP_DIR --image TAG --json OUT [--seed N] [--per N]

Rough skeleton-probe scorer for tbrain-qpcr-relative-expression (authoring-only, never shipped).
Runs the documented command, `python3 /app/tools/qpcrrel_run.py PLATE.json`, inside the task
environment image with --network none, as an unprivileged user, with the candidate's APP_DIR/src
mounted read-only on /app/src and our own pristine copy of the driver on /app/tools. Plates are
seeded and generated per family (jobgen.py): a trap-free broad family, one family per departure
(D1, D2, D4-D7) and one per restraint trap (T1, T2), each trap isolated in its own family. Each report is
compared type-strictly with solution/model.py (floats within 5e-9 relative, everything else exact).
Prints PASS/FAIL per family and a VERDICT line; writes the same as JSON.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import compare  # noqa: E402
import jobgen  # noqa: E402

DRIVER = jobgen.TASK / "environment" / "app" / "tools" / "qpcrrel_run.py"
SEED = 20260927
PER = 8


def run_in_image(image, src, plates):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "tools").mkdir()
        shutil.copy2(DRIVER, tmp / "tools" / "qpcrrel_run.py")
        (tmp / "jobs").mkdir()
        for k, p in enumerate(plates):
            (tmp / "jobs" / f"{k:04d}.json").write_text(json.dumps(p))
        for d in (tmp, tmp / "tools", tmp / "jobs"):
            d.chmod(0o755)
        loop = ('cd /app; for f in /jobs/*.json; do printf "@@%s\\n" "$(basename "$f")"; '
                'timeout 60 python3 /app/tools/qpcrrel_run.py "$f" 2>/dev/null || echo "@@ERROR"; done')
        proc = subprocess.run(
            ["docker", "run", "--rm", "--network", "none", "--user", "65534:65534",
             "-e", "PYTHONDONTWRITEBYTECODE=1",
             "-v", f"{Path(src).resolve()}:/app/src:ro", "-v", f"{tmp / 'tools'}:/app/tools:ro",
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
    return outputs, proc.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("app_dir")
    ap.add_argument("--image", required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--per", type=int, default=PER)
    a = ap.parse_args()
    app = Path(a.app_dir).resolve()
    cases = jobgen.cases(a.seed, a.per)
    outputs, rc = run_in_image(a.image, app / "src", [p for _f, p in cases])
    fams = {}
    for k, (fam, plate) in enumerate(cases):
        d = fams.setdefault(fam, {"passed": 0, "total": 0, "first_diff": None})
        d["total"] += 1
        got, exp = outputs.get(k), jobgen.model.report(plate)
        if got is not None and compare.same(got, exp):
            d["passed"] += 1
        elif d["first_diff"] is None:
            d["first_diff"] = "no report (error)" if got is None else compare.diff_paths(got, exp)[:4]
    failed = [f for f, d in fams.items() if d["passed"] != d["total"]]
    for f, d in fams.items():
        print(f"{'PASS' if f not in failed else 'FAIL'} {f:6s} {d['passed']}/{d['total']}" + (f"  {d['first_diff']}" if f in failed else ""))
    verdict = "solved" if not failed else "not_solved"
    print(f"VERDICT {verdict} failed={failed}")
    image_id = subprocess.run(["docker", "image", "inspect", a.image, "--format", "{{.Id}}"], capture_output=True, text=True).stdout.strip()
    Path(a.json).write_text(json.dumps({
        "app_dir": str(app), "image": a.image, "image_id": image_id, "docker_exit": rc, "seed": a.seed, "per_family": a.per,
        "families": fams, "failed_families": failed, "verdict": verdict,
        "model_sha256": hashlib.sha256((jobgen.TASK / "solution" / "model.py").read_bytes()).hexdigest(),
        "driver_sha256": hashlib.sha256(DRIVER.read_bytes()).hexdigest(),
        "jobgen_sha256": hashlib.sha256((HERE / "jobgen.py").read_bytes()).hexdigest(),
    }, indent=1) + "\n")


if __name__ == "__main__":
    main()

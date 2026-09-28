"""skeleton_score.py APP_DIR [--image TAG] [--json OUT]: skeleton-probe scorer for
tbrain-crop-hail-loss-adjustment (authoring only, never shipped).

Runs the candidate package APP_DIR/src through our own pristine copy of the fixed driver, with the
documented command `python3 /app/tools/hail_run.py JOB.json`, inside the task environment image,
candidate src and driver mounted read-only, as an unprivileged uid (65534) with all capabilities
dropped, no-new-privileges, a read-only root and --network none. Jobs are seeded and generated per
family: a trap-free `broad` family over the whole section 1 range, one family per departure D1-D8 and
one per trap TA (sample plots that are not hail-thinned but lost plants) and TB (replantings under
10.0 acres); each trap's inputs appear only in its own family (checked). Every output is compared
type-strictly with solution/model.py over the whole statements object. Prints PASS/FAIL per family
with the first differing field path, and "VERDICT solved|failed failed=[...]".
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
sys.path.insert(0, str(HERE / "authoring"))
import gen  # noqa: E402

SEED = 20260928
PER_FAMILY = 6
DRIVER = gen.TASK / "environment" / "app" / "tools" / "hail_run.py"


def first_difference(got, exp, path="$"):
    """The first field path where got differs from exp (type-strict), or None."""
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


def run_candidate(app_dir, image, cases):
    src = Path(app_dir).resolve() / "src"
    if not src.is_dir():
        raise SystemExit(f"no src/ under {app_dir}")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "tools").mkdir()
        shutil.copy2(DRIVER, tmp / "tools" / "hail_run.py")
        (tmp / "jobs").mkdir()
        for k, (_fam, job) in enumerate(cases):
            (tmp / "jobs" / f"{k:04d}.json").write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        for p in [tmp, tmp / "tools", tmp / "jobs", *tmp.rglob("*")]:
            p.chmod(0o755 if p.is_dir() else 0o644)
        loop = ('for f in /jobs/*.json; do printf "@@%s\\n" "$(basename "$f")"; '
                'timeout 60 python3 /app/tools/hail_run.py "$f" 2>/dev/null || echo "@@ERROR"; done')
        proc = subprocess.run(
            ["docker", "run", "--rm", "--network", "none", "--user", "65534:65534", "--read-only",
             "--tmpfs", "/tmp", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
             "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "PYTHONIOENCODING=utf-8",
             "-v", f"{src}:/app/src:ro", "-v", f"{tmp / 'tools'}:/app/tools:ro",
             "-v", f"{tmp / 'jobs'}:/jobs:ro", image, "bash", "-c", loop],
            capture_output=True, text=True, encoding="utf-8", timeout=1800)
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


def score(app_dir, image, out_json):
    cases = gen.draw(SEED, PER_FAMILY)
    outputs, rc, err = run_candidate(app_dir, image, cases)
    families = {fam: {"passed": 0, "total": 0, "first_difference": None} for fam in gen.FAMILIES}
    for k, (fam, job) in enumerate(cases):
        exp = gen.model.statements(job)
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
    verdict = "solved" if not failed else "failed"
    print(f"VERDICT {verdict} failed={failed}")
    image_id = subprocess.run(["docker", "image", "inspect", image, "--format", "{{.Id}}"],
                              capture_output=True, text=True).stdout.strip()
    result = {
        "app_dir": str(Path(app_dir).resolve()),
        "image": image,
        "image_id": image_id,
        "docker_exit": rc,
        "docker_stderr_tail": err,
        "seed": SEED,
        "per_family": PER_FAMILY,
        "families": families,
        "failed_families": failed,
        "verdict": verdict,
        "model_sha256": hashlib.sha256((gen.TASK / "solution" / "model.py").read_bytes()).hexdigest(),
        "driver_sha256": hashlib.sha256(DRIVER.read_bytes()).hexdigest(),
    }
    if out_json:
        Path(out_json).write_text(json.dumps(result, indent=1) + "\n")
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("app_dir", help="a solved copy of environment/app (its src/ is scored)")
    ap.add_argument("--image", default="tbrain-crop-hail-loss-adjustment:skeleton2")
    ap.add_argument("--json", dest="json_out")
    a = ap.parse_args()
    score(a.app_dir, a.image, a.json_out)

#!/usr/bin/env python3
"""Skeleton-probe scorer for tbrain-bod5-dilution-data-reduction (authoring only; never shipped in the task).

usage: skeleton_score.py <solver_app_dir> [--image TAG] [--json OUT]

<solver_app_dir> is a solver's /app tree (it must hold src/bodcalc). Batches are drawn from a fixed seed by
authoring/gen.py, one family per departure (D1-D8) and per trap (T1, T2, each carrying only its own trap input) plus
a trap-free broad family, all within SOP WQ-14 section 1. They are reduced inside the task environment image with
the solver's src mounted read-only over /app/src and our pristine copy of the driver mounted over
/app/tools/bodcalc_run.py, running the documented command `python3 /app/tools/bodcalc_run.py BATCH.json` as an
unprivileged uid, with --network none, a read-only root and no capabilities. Each whole report is compared
type-strictly with solution/model.py: batch, qualifiers, ids, relation, of, pass and list order exactly; other
numbers must be floats within 1e-6 relative (1e-6 absolute when the expected number is below one). A separate
`driver` line checks that the solver's tools/bodcalc_run.py is byte-identical to the shipped driver.
Prints PASS/FAIL per family and a final line `VERDICT solved|failed failed=[...]`.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "authoring"))
import gen  # noqa: E402

TASK = gen.TASK
DRIVER = TASK / "environment" / "app" / "tools" / "bodcalc_run.py"
SEED = 20260927
PER_FAMILY = 8
DEFAULT_IMAGE = "tbrain-bod5-dilution-data-reduction:skeleton2"

RUNNER = r"""
import json, os, subprocess, sys
out = {}
for name in sorted(os.listdir("/batches")):
    try:
        p = subprocess.run([sys.executable, "/app/tools/bodcalc_run.py", "/batches/" + name],
                           capture_output=True, text=True, timeout=60, cwd="/tmp")
        out[name] = {"rc": p.returncode, "stdout": p.stdout, "stderr": p.stderr[-2000:]}
    except subprocess.TimeoutExpired:
        out[name] = {"rc": -9, "stdout": "", "stderr": "timeout"}
sys.stdout.write(json.dumps(out))
"""


def close(g, e):
    if abs(e) < 1.0:
        return abs(g - e) <= 1e-6
    return abs(g - e) <= 1e-6 * abs(e)


def same(g, e, path="$"):
    """Return None when equal, else a short description of the first difference."""
    if type(g) is not type(e):
        return f"{path}: type {type(g).__name__} != {type(e).__name__}"
    if isinstance(e, dict):
        if list(g) != list(e) and sorted(g) != sorted(e):
            return f"{path}: keys {sorted(g)} != {sorted(e)}"
        for k in e:
            d = same(g[k], e[k], f"{path}.{k}")
            if d:
                return d
        return None
    if isinstance(e, list):
        if len(g) != len(e):
            return f"{path}: length {len(g)} != {len(e)}"
        for i, (a, b) in enumerate(zip(g, e)):
            d = same(a, b, f"{path}[{i}]")
            if d:
                return d
        return None
    if isinstance(e, float):
        return None if close(g, e) else f"{path}: {g!r} != {e!r}"
    return None if g == e else f"{path}: {g!r} != {e!r}"


def reduce_in_image(app, batches, image):
    with tempfile.TemporaryDirectory() as tmp:
        bdir = Path(tmp) / "batches"
        bdir.mkdir()
        for i, (_fam, b) in enumerate(batches):
            (bdir / f"b{i:04d}.json").write_text(json.dumps(b))
        os.chmod(tmp, 0o755)
        os.chmod(bdir, 0o755)
        for f in bdir.iterdir():
            os.chmod(f, 0o644)
        cmd = [
            "docker", "run", "--rm", "--network", "none", "--read-only", "--tmpfs", "/tmp:rw,size=64m",
            "--user", "65534:65534", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            "-v", f"{(Path(app) / 'src').resolve()}:/app/src:ro",
            "-v", f"{DRIVER.resolve()}:/app/tools/bodcalc_run.py:ro",
            "-v", f"{bdir}:/batches:ro",
            image, "python3", "-I", "-c", RUNNER,
        ]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if p.returncode != 0:
            raise SystemExit(f"docker run failed ({p.returncode}): {p.stderr[-2000:]}")
        raw = json.loads(p.stdout)
        return [raw[f"b{i:04d}.json"] for i in range(len(batches))]


def score(app, image):
    batches = gen.batches(SEED, PER_FAMILY)
    runs = reduce_in_image(app, batches, image)
    fams = {}
    for (fam, b), r in zip(batches, runs):
        exp = gen.model.report(b)
        why = None
        if r["rc"] != 0:
            why = f"exit {r['rc']}: {r['stderr'].strip().splitlines()[-1] if r['stderr'].strip() else ''}"
        else:
            try:
                got = json.loads(r["stdout"])
                why = same(got, exp)
            except json.JSONDecodeError as ex:
                why = f"stdout is not JSON: {ex}"
        f = fams.setdefault(fam, {"passed": 0, "total": 0, "first_failure": None})
        f["total"] += 1
        if why is None:
            f["passed"] += 1
        elif f["first_failure"] is None:
            f["first_failure"] = f"{b['batch']}: {why}"
    drv = Path(app) / "tools" / "bodcalc_run.py"
    same_driver = drv.is_file() and drv.read_bytes() == DRIVER.read_bytes()
    fams["driver"] = {"passed": int(same_driver), "total": 1,
                      "first_failure": None if same_driver else "tools/bodcalc_run.py differs from the shipped driver or is missing"}
    return fams


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("app")
    ap.add_argument("--image", default=DEFAULT_IMAGE)
    ap.add_argument("--json")
    a = ap.parse_args()
    if not (Path(a.app) / "src" / "bodcalc").is_dir():
        raise SystemExit(f"{a.app} has no src/bodcalc")
    fams = score(a.app, a.image)
    failed = []
    for fam, f in fams.items():
        ok = f["passed"] == f["total"]
        if not ok:
            failed.append(fam)
        line = f"{'PASS' if ok else 'FAIL'} {fam:6s} {f['passed']}/{f['total']}"
        if not ok:
            line += f"  first: {f['first_failure']}"
        print(line)
    verdict = "failed" if failed else "solved"
    print(f"VERDICT {verdict} failed=[{','.join(failed)}]")
    if a.json:
        Path(a.json).write_text(json.dumps({"app": str(Path(a.app).resolve()), "image": a.image, "seed": SEED,
                                            "per_family": PER_FAMILY, "families": fams, "verdict": verdict,
                                            "failed": failed}, indent=1))


if __name__ == "__main__":
    main()

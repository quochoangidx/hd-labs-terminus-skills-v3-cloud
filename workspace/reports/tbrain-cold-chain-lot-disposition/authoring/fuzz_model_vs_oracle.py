"""Fuzz solution/model.py against the Oracle-patched package (step 4), writing a receipt.

    python3 fuzz_model_vs_oracle.py TASK_DIR RECEIPT.json [N]

Each draw is one job directory from solution/jobgen.py across the full SOP section 1 ranges,
logger gaps, certificate transients and handovers of 0-2,880 minutes included; every job is checked against the SOP 1.4 limits first. The model's
report and the Oracle driver's report are compared type-strictly. A disagreement is excused only
when the model's unrounded MKT sits inside the SOP 1.5 margin (such a lot is outside the graded
domain); every excused lot is counted in the receipt.
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


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strict_equal(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(strict_equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(strict_equal(x, y) for x, y in zip(a, b))
    return a == b


def oracle_tree(task, into):
    app = into / "app"
    shutil.copytree(task / "environment" / "app", app)
    subprocess.run(["patch", "-s", "-p1", "--no-backup-if-mismatch", "-i", str(task / "solution" / "fix.patch")], cwd=into, check=True)
    return app


def run_driver(app, job):
    out = subprocess.run([sys.executable, "-I", "-S", str(app / "tools" / "coldchain_run.py"), str(job)], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def main():
    task = Path(sys.argv[1]).resolve()
    receipt = Path(sys.argv[2])
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 400
    model = load_module(task / "solution" / "model.py", "sop_model")
    jobgen = load_module(task / "solution" / "jobgen.py", "sop_jobgen")
    rng = random.Random(20260927)
    shapes = [
        dict(lots=3, max_legs=4, max_readings=40, gaps=True, handover=2880),
        dict(lots=6, max_legs=12, max_readings=12, gaps=True, handover=60),
        dict(lots=2, max_legs=2, max_readings=400, gaps=True, handover=0),
        dict(lots=4, max_legs=3, max_readings=30, gaps=False, handover=0, transients=False),
        dict(lots=5, max_legs=5, max_readings=25, gaps=True, handover=300, inside=0.97),
        dict(lots=5, max_legs=3, max_readings=25, gaps=False, handover=2880, inside=0.9),
    ]
    stats = {"jobs": 0, "lots": 0, "agree": 0, "excused_margin": 0, "disagree": 0, "dispositions": {}, "gap_lots": 0, "transient_lots": 0, "limit_breaches": 0}
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        app = oracle_tree(task, tmp / "oracle")
        for index in range(count):
            job = jobgen.write_job(tmp / f"j{index}", rng, **shapes[index % len(shapes)])
            expected, margins = model.expected_report(job, with_margins=True)
            record, lot_rows, exports = model.load(job)
            breaches = model.limit_breaches(job)
            stats["limit_breaches"] += len(breaches)
            if breaches:
                failures.append({"job": index, "why": "limits", "breaches": breaches[:5]})
            for entry in lot_rows:
                rows = [exports[name] for name in entry["legs"]]
                if any(b[0] - a[0] > 30 for r in rows for a, b in zip(r, r[1:])):
                    stats["gap_lots"] += 1
                if any(m < 15 for entries in entry.get("certificate", {}).values() for m in entries):
                    stats["transient_lots"] += 1
            got = run_driver(app, job)
            stats["jobs"] += 1
            if got["product"] != expected["product"] or len(got["lots"]) != len(expected["lots"]):
                failures.append({"job": index, "why": "report shape"})
                continue
            for want, have, margin in zip(expected["lots"], got["lots"], margins):
                stats["lots"] += 1
                stats["dispositions"][want["disposition"]] = stats["dispositions"].get(want["disposition"], 0) + 1
                if strict_equal(want, have):
                    stats["agree"] += 1
                elif margin["mkt_to_upper"] < 0.001 or margin["mkt_to_half_tenth"] < 0.0005:
                    stats["excused_margin"] += 1
                else:
                    stats["disagree"] += 1
                    failures.append({"job": index, "lot": want["lot"], "model": want, "oracle": have})
            shutil.rmtree(job)
    body = {
        "receipt": "model-vs-oracle-fuzz",
        "task_slug": task.name,
        "seed": 20260927,
        "shapes": shapes,
        "model_sha256": hashlib.sha256((task / "solution" / "model.py").read_bytes()).hexdigest(),
        "fix_patch_sha256": hashlib.sha256((task / "solution" / "fix.patch").read_bytes()).hexdigest(),
        "stats": stats,
        "failures": failures[:20],
        "status": "pass" if not failures else "fail",
    }
    receipt.write_text(json.dumps(body, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: body[k] for k in ("status", "stats")}, indent=1))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Skeleton scorer for tbrain-linux-host-intrusion-triage (no verifier yet).

Usage: skeleton_score.py <solver_app_dir> [--image TAG] [--json OUT] [--seeds N]

Runs <solver_app_dir>/triage.py inside the task image (app mounted read-only at
/app, evidence read-only, --network none, uid 65534, python3 -I) on case-1 plus
N hidden seeds per decoy family plus a broad family, and compares each report
with solution/model.py's scenario-derived truth (sets order-free, everything
else exact and type-strict). Prints PASS/FAIL per family and
"VERDICT solved|failed failed=[...]".
"""

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TASK = Path(__file__).resolve().parents[2] / "tasks" / "tbrain-linux-host-intrusion-triage"
SETS = ("sources", "accounts", "persistence")
SEED_BASE = 7_000_000  # hidden seeds, disjoint from the visible case's seed


def load_model():
    spec = importlib.util.spec_from_file_location("model", TASK / "solution" / "model.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def same(got, want):
    if not isinstance(got, dict) or set(got) != set(want):
        return False
    for k, v in want.items():
        g = got[k]
        if k in SETS:
            if not isinstance(g, list) or len(g) != len(set(map(str, g))) or sorted(map(str, g)) != v or not all(isinstance(x, str) for x in g):
                return False
        elif json.dumps(g, sort_keys=True) != json.dumps(v, sort_keys=True):
            return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("app_dir", type=Path)
    ap.add_argument("--image", default="tbrain-linux-host-intrusion-triage:skeleton4")
    ap.add_argument("--json", type=Path)
    ap.add_argument("--seeds", "--per-family", dest="seeds", type=int, default=4)
    ap.add_argument("--seed-base", type=int, default=SEED_BASE)
    a = ap.parse_args()
    model = load_model()
    work = Path(tempfile.mkdtemp(prefix="skel"))
    ev_root, out_root = work / "ev", work / "out"
    ev_root.mkdir()
    out_root.mkdir()
    os.chmod(out_root, 0o777)
    cases = {}  # opaque name -> (family, truth)
    shutil.copytree(TASK / "environment/app/evidence/case-1", ev_root / "c000")
    cases["c000"] = ("case-1", model.truth(model.build(1, "all")))
    n = 1
    for fam in model.FAMILIES + ["broad"]:
        for i in range(a.seeds):
            s = model.build(a.seed_base + i, fam)
            name = f"c{n:03d}"
            model.write_evidence(s, ev_root / name)
            cases[name] = (fam, model.truth(s))
            n += 1
    for p in ev_root.rglob("*"):
        os.chmod(p, 0o755 if p.is_dir() else 0o644)
    os.chmod(ev_root, 0o755)
    script = ('for d in /ev/*; do n=$(basename "$d"); '
              'timeout 120 python3 -I /app/triage.py "$d" "/out/$n.json" >/out/$n.log 2>&1; echo $? > /out/$n.rc; done')
    cmd = ["docker", "run", "--rm", "--network", "none", "--user", "65534:65534", "--read-only",
           "--tmpfs", "/tmp", "-v", f"{a.app_dir.resolve()}:/app:ro", "-v", f"{ev_root}:/ev:ro",
           "-v", f"{out_root}:/out", "-w", "/tmp", a.image, "bash", "-c", script]
    subprocess.run(cmd, check=False, timeout=3600)
    fams, detail = {}, {}
    for name, (fam, want) in cases.items():
        try:
            got = json.loads((out_root / f"{name}.json").read_text())
        except Exception as e:  # noqa: BLE001
            got = {"_error": repr(e)}
        ok = same(got, want)
        fams.setdefault(fam, []).append(ok)
        if not ok:
            diff = sorted(k for k in want if not same({**want, k: got.get(k) if isinstance(got, dict) else None}, want)) if isinstance(got, dict) and set(got) == set(want) else ["<keys>"]
            detail.setdefault(fam, []).append({"case": name, "fields": diff})
    failed = [f for f, oks in fams.items() if not all(oks)]
    for f, oks in fams.items():
        print(f"{'PASS' if all(oks) else 'FAIL'} {f} {sum(oks)}/{len(oks)}" + (f" {detail[f]}" if f in detail else ""))
    verdict = "solved" if not failed else "failed"
    print(f"VERDICT {verdict} failed={failed}")
    if a.json:
        a.json.write_text(json.dumps({"app_dir": str(a.app_dir), "image": a.image, "seeds_per_family": a.seeds,
                                      "families": {f: {"passed": sum(o), "cases": len(o)} for f, o in fams.items()},
                                      "failures": detail, "verdict": verdict, "failed": failed}, indent=1) + "\n")
    shutil.rmtree(work, ignore_errors=True)
    return 0 if verdict == "solved" else 1


if __name__ == "__main__":
    sys.exit(main())

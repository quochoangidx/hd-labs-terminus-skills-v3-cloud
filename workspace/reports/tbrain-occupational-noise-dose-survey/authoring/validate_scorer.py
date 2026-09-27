"""validate_scorer.py: validate score_skeleton.py -> ../receipts/score-skeleton-validation.json.

Oracle must pass every family; the shipped package must fail every departure family; each one-hunk revert
must fail its own departure family; each natural trap over-repair must fail exactly its trap family.
"""
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = HERE.parents[2] / "tasks" / "tbrain-occupational-noise-dose-survey"


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sk = load("score_skeleton")
cd = load("check_departures")


def app_with(edits, root):
    shutil.copytree(HERE / "patched" / "app" / "src", root / "src")
    for rel, old, new in edits:
        f = root / "src" / "noisedose" / rel
        t = f.read_text()
        assert t.count(old) == 1, (rel, old)
        f.write_text(t.replace(old, new))
    return root


def main():
    rows, ok = [], True
    dep_fams = [f for f in sk.FAMILIES if f.startswith("D")]
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        runs = [("oracle", HERE / "patched" / "app", lambda failed: failed == []),
                ("shipped", TASK / "environment" / "app", lambda failed: set(dep_fams) <= set(failed))]
        for name, _rule, edits, _s in cd.DEPARTURES:
            fam = name.split("_")[0]
            runs.append((f"revert_{name}", app_with(edits, tmp / name), lambda failed, fam=fam: fam in failed))
        for name, _rule, _site, repairs, _s in cd.TRAPS:
            fam = name.split("_")[0]
            for i, (desc, edits) in enumerate(repairs):
                runs.append((f"natural_{fam}_{i}: {desc}", app_with(edits, tmp / f"{fam}_{i}"), lambda failed, fam=fam: failed == [fam]))
        for name, app, check in runs:
            out = tmp / "out.json"
            r = sk.score(app, out)
            passed = check(r["failed_families"])
            ok &= passed
            rows.append({"run": name, "failed_families": r["failed_families"], "families": r["families"], "expectation_met": passed})
            print(name, r["failed_families"], passed, flush=True)
    receipt = {"status": "pass" if ok else "fail", "scorer": "authoring/score_skeleton.py", "seed": sk.SEED, "per_family": sk.PER_FAMILY,
               "expectations": {"oracle": "no failed family", "shipped": "every departure family fails",
                                "revert_*": "its own departure family fails", "natural_T*": "exactly its trap family fails"},
               "runs": rows}
    (HERE.parent / "receipts" / "score-skeleton-validation.json").write_text(json.dumps(receipt, indent=1) + "\n")
    print(receipt["status"])


if __name__ == "__main__":
    main()

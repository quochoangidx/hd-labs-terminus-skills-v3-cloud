"""Validate score_skeleton.py: Oracle all-pass; shipped fails every departure family; each
natural trap over-repair fails exactly its trap family; each departure reverted alone fails
its own family.  Usage: python3 validate_score_skeleton.py SCRATCH OUT_JSON"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score_skeleton as S  # noqa: E402

TASK = S.TASK
SCRATCH = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
sys.argv = [sys.argv[0], str(TASK), str(SCRATCH), str(SCRATCH / "unused.json")]
import departure_check as DC  # noqa: E402

OVER = {
    "TA_wipe_not_a_leak_test": [("checks.py", 'for w in entry["leak_tests"] if w["removable_bq"] < WIPE_LEAK_BQ]', 'for w in entry["leak_tests"]]')],
    "TB_licensing_follows_certificate": [("locations.py", 'if entry["ref_bq"] <= exempt_quantity(entry["nuclide"]):', 'if activity <= exempt_quantity(entry["nuclide"]):')],
    "T1_certificate_after_survey": [("dates.py", "    return max(days, 0)", "    return days")],
}
REVERT_FAMILY = {
    "D1_day_count_30_360": "D1_day_count", "D2_year_365": "D2_year_length", "D3_exp_mean_life": "D3_decay_law",
    "D4_branching_ignored": "D4_daughter_branching", "D5_exempt_parent_only": "D5_exemption_total",
    "D6_leak_on_certificate": "D6_leak_on_current", "D7_last_listed_wipe": "D7_latest_leak_test",
    "D8_disposal_thousandth": "D8_disposal_ten_half_lives", "D9_location_certificate_sum": "D9_store_current_sum",
}


def make(name, edits):
    root = SCRATCH / name
    if root.exists():
        shutil.rmtree(root)
    shutil.copytree(TASK / "environment" / "app", root / "app", ignore=shutil.ignore_patterns("__pycache__"))
    if edits is not None:
        subprocess.run(["patch", "-s", "-p1", "-d", str(root)], input=(TASK / "solution" / "fix.patch").read_bytes(), check=True)
        for rel, old, new in edits:
            p = root / "app" / "src" / "sealsrc" / rel
            s = p.read_text()
            assert old in s, (name, old)
            p.write_text(s.replace(old, new))
    return root / "app"


def failing(rep):
    return sorted(k for k, v in rep["families"].items() if v["status"] == "fail")


def main():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    res, checks = {}, {}
    rep = S.score(make("oracle", []))
    res["oracle"] = rep
    checks["oracle_all_pass"] = rep["verdict"] == "pass"
    rep = S.score(make("shipped", None))
    res["shipped"] = rep
    dfam = [k for k in rep["families"] if k.startswith("D")]
    checks["shipped_fails_every_departure_family"] = all(rep["families"][k]["status"] == "fail" for k in dfam)
    for fam, edits in OVER.items():
        rep = S.score(make("over-" + fam, edits))
        res["overrepair:" + fam] = rep
        checks["overrepair_fails_exactly_" + fam] = failing(rep) == [fam]
    for rname, fam in REVERT_FAMILY.items():
        rel, old, new = DC.REVERTS[rname]
        rep = S.score(make("revert-" + rname, [(rel, old, new)]))
        res["revert:" + rname] = rep
        checks["revert_" + rname + "_fails_own_family"] = rep["families"][fam]["status"] == "fail"
    summary = {k: {"verdict": v["verdict"], "failing_families": failing(v)} for k, v in res.items()}
    out = {"status": "pass" if all(checks.values()) else "fail", "checks": checks, "summary": summary,
           "scorer": "authoring/score_skeleton.py", "per_family_jobs": 25}
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(checks, indent=1))
    print(out["status"])


if __name__ == "__main__":
    main()

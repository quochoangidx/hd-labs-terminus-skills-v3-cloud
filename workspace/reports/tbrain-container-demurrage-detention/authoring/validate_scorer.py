"""validate_scorer.py OUT_JSON: build scorer-validation variants and score each (authoring only).

Variants: the Oracle (shipped + fix.patch), the shipped package, each departure hunk reverted on the
Oracle, and the natural trap over-repairs. Expected: Oracle all pass; shipped fails every departure
family; each reverted departure fails its own family; each natural over-repair fails only its trap's
family.
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import score_skeleton  # noqa: E402

ORACLE = HERE / "oracle" / "app"
SHIPPED = score_skeleton.TASK / "environment" / "app"

# (file, old, new) single edits applied to a copy of the Oracle
EDITS = {
    "revert_D1_days_both_ends": [("stays.py", 'return (stage["last"] - stage["first"]).days + 1', 'return (stage["last"] - stage["first"]).days')],
    "revert_D2_working_days": [("freetime.py", "if calendar.is_working_day(day) and not calendar.is_closure(day):", "if not calendar.is_closure(day):")],
    "revert_D3_closures": [("freetime.py", "if calendar.is_working_day(day) and not calendar.is_closure(day):", "if calendar.is_working_day(day):"),
                           ("freetime.py", 'if not (stage["name"] == TERMINAL and calendar.is_closure(day)):', "if True:")],
    "revert_D4_merchant_first_day": [("stays.py", 'out.append(_stage(MERCHANT, gate_out, found.get("EMPTY_RETURN"), cut_off))',
                                      'out.append(_stage(MERCHANT, gate_out + ONE_DAY, found.get("EMPTY_RETURN"), cut_off))'),
                                     ("stays.py", "from .dates import parse", "from .dates import ONE_DAY, parse")],
    "revert_D5_incremental_tiers": [("rates.py", "        take = left if length is None else min(left, length)\n        total += take * rate\n        left -= take\n        if left <= 0:\n            break\n    return total",
                                     "        if length is None or left <= length:\n            return rate * count\n        left -= length\n    return total")],
    "revert_D6_revision_by_day": [("rates.py", "    revision = revision_in_force(contract, first_chargeable)\n", "    revision = None\n")],
    "revert_D7_half_up": [("statement.py", "        return (amount * percent + 50) // 100", "        return amount * percent // 100")],
    "natural_T1_half_up_everywhere": [("statement.py", "    if all_ended:\n        return (amount * percent + 50) // 100", "    if True:\n        return (amount * percent + 50) // 100")],
    "natural_T1_ended_stages_only": [("statement.py", "    amount = sum(entry[\"amount\"] for entry in entries.values() if entry is not None)\n    discount = discount_on(amount, contract[\"discount_percent\"], all_ended)",
                                      "    amount = sum(entry[\"amount\"] for entry in entries.values() if entry is not None)\n    charged = sum(e[\"amount\"] for e in entries.values() if e is not None and e[\"status\"] == \"ended\")\n    discount = discount_on(charged, contract[\"discount_percent\"], True)")],
    "natural_T2_earliest_revision": [("rates.py", "        revision = current_revision(contract)", "        revision = contract[\"revisions\"][0]")],
    "natural_T2_raise": [("rates.py", "        revision = current_revision(contract)", "        raise ValueError(\"no revision in force\")")],
}
EXPECT_ONLY = {"natural_T1_half_up_everywhere": ["T1"], "natural_T1_ended_stages_only": ["T1"],
               "natural_T2_earliest_revision": ["T2"], "natural_T2_raise": ["T2"]}
EXPECT_INCLUDES = {"revert_D1_days_both_ends": "D1", "revert_D2_working_days": "D2", "revert_D3_closures": "D3",
                   "revert_D4_merchant_first_day": "D4", "revert_D5_incremental_tiers": "D5",
                   "revert_D6_revision_by_day": "D6", "revert_D7_half_up": "D7"}


def build_variant(name, root):
    dst = root / name / "app"
    shutil.copytree(ORACLE, dst)
    for fname, old, new in EDITS[name]:
        path = dst / "src" / "ddbill" / fname
        text = path.read_text()
        assert text.count(old) == 1, (name, fname, old)
        path.write_text(text.replace(old, new))
    return dst


def main(out):
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        runs = {"oracle": ORACLE, "shipped": SHIPPED}
        for name in EDITS:
            runs[name] = build_variant(name, tmp)
        for name, app in runs.items():
            r = score_skeleton.score(app)
            results[name] = {"failed_families": r["failed_families"], "families": r["families"], "verdict": r["verdict"]}
            print(name, r["verdict"], r["failed_families"], flush=True)
    checks = {
        "oracle_all_pass": results["oracle"]["failed_families"] == [],
        "shipped_fails_every_departure_family": all(f in results["shipped"]["failed_families"] for f in
                                                    ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]),
        "shipped_passes_no_trap_family_check": results["shipped"]["failed_families"],
    }
    for name, fam in EXPECT_INCLUDES.items():
        checks[f"{name}_fails_{fam}"] = fam in results[name]["failed_families"]
    for name, fams in EXPECT_ONLY.items():
        checks[f"{name}_fails_only_{'_'.join(fams)}"] = results[name]["failed_families"] == fams
    ok = all(v for k, v in checks.items() if k != "shipped_passes_no_trap_family_check")
    report = {"status": "pass" if ok else "fail", "checks": checks, "results": results,
              "image": score_skeleton.DEFAULT_IMAGE, "seed": score_skeleton.SEED, "per_family": score_skeleton.PER_FAMILY}
    Path(out).write_text(json.dumps(report, indent=1) + "\n")
    print("STATUS", report["status"])


if __name__ == "__main__":
    main(sys.argv[1])

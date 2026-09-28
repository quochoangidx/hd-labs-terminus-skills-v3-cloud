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
    "revert_D1_on_hand_through_dispatch_day": [("lots.py", "        if when < day or (when == day and pallets < 1):", "        if when <= day:")],
    "revert_D2_anniversary_weeks": [("storage.py", "        if day >= start:\n            out.append(day)\n        day += WEEK",
                                     "        if day >= start:\n            out.append(day)\n        day += WEEK\n    out = [d + timedelta(days=(7 - d.weekday()) % 7) for d in out]\n    out = [d for d in out if d <= end]")],
    "revert_D3_holidays_out_of_hours": [("dates.py", "return day.weekday() >= 5 or day in self.holidays", "return day.weekday() >= 5")],
    "revert_D4_receiving_rate": [("handling.py", "movement_rate(rates, received, calendar, \"in\")", "movement_rate(rates, received, calendar, \"out\")")],
    "revert_D9_receipt_fee": [("handling.py", "total += rates[\"fee\"] + lot[\"pallets\"] *", "total += lot[\"pallets\"] *")],
    "revert_D5_non_retroactive_tiers": [("storage.py", "tier_rate(week_number(lot, first), rates_for(client, first)", "tier_rate(week_number(lot, end), rates_for(client, first)")],
    "revert_D6_revision_in_force": [("rates.py", "    return revision_in_force(client, day)[\"rates\"]", "    return client[\"revisions\"][-1][\"rates\"]")],
    "revert_D7_half_up": [("statement.py", "    return (stored * percent + 50) // 100", "    return stored * percent // 100")],
    "revert_D8_peak_on_billed_weeks": [("storage.py", "    return max([pallets for pallets in billed if pallets > 0], default=0)",
                                        "    return max((on_hand(lot, start + timedelta(days=k)) for k in range((end - start).days + 1)\n                if start + timedelta(days=k) >= parse(lot[\"received\"])), default=0)")],
    "natural_T1_every_entry_next_day": [("lots.py", "        if when < day or (when == day and pallets < 1):", "        if when < day:")],
    "natural_T1_only_dispatches_count": [("lots.py", "        if when < day or (when == day and pallets < 1):", "        if pallets >= 1 and when < day:")],
    "natural_T2_fee_for_every_arrival": [("handling.py", "if start <= received <= end and lot[\"pallets\"] >= 1:", "if start <= received <= end:")],
}
EXPECT_ONLY = {"natural_T1_every_entry_next_day": ["T1"], "natural_T1_only_dispatches_count": ["T1"],
               "natural_T2_fee_for_every_arrival": ["T2"]}
EXPECT_INCLUDES = {"revert_D1_on_hand_through_dispatch_day": "D1", "revert_D2_anniversary_weeks": "D2",
                   "revert_D3_holidays_out_of_hours": "D3", "revert_D4_receiving_rate": "D4",
                   "revert_D5_non_retroactive_tiers": "D5", "revert_D6_revision_in_force": "D6", "revert_D7_half_up": "D7",
                   "revert_D8_peak_on_billed_weeks": "D8", "revert_D9_receipt_fee": "D9"}


def build_variant(name, root):
    dst = root / name / "app"
    shutil.copytree(ORACLE, dst)
    for fname, old, new in EDITS[name]:
        path = dst / "src" / "stockbill" / fname
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
                                                    ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9"]),
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

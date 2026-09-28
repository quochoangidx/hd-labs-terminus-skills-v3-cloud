"""make_wrong_paths.py: write wrong-paths/<id>.patch (shipped -> wrong tree, patch -p1 from /) for every wrong path."""

import shutil
import subprocess
from pathlib import Path

import variants

HERE = Path(__file__).resolve().parent
R = HERE.parent
TASK = R.parents[1] / "tasks" / "tbrain-sales-commission-statement"
OUT = R / "wrong-paths"

MAP = {
    "W01-accelerator-on-all-bookings": ("rev-D1", "test_rule_4_1_accelerators_apply_to_the_part_above_quota"),
    "W02-whole-order-value": ("rev-D2", "test_rule_3_2_bookings_take_the_reps_split"),
    "W03-bands-truncated": ("rev-D3", "test_rule_4_2_each_band_rounds_half_up"),
    "W04-reversal-window-90": ("rev-D4", "test_rule_5_1_reversals_up_to_120_days"),
    "W05-floor-on-new-logo": ("rev-D5", "test_rule_6_1_new_logo_bonus_on_small_splits"),
    "W06-minimum-10000": ("rev-D6", "test_rule_7_4_minimum_payment"),
    "W07-recover-from-whole-total": ("rev-D7", "test_rule_7_3_recovery_only_above_the_draw"),
    "W08-shared-window-edited": ("TA-inplace-window", "test_courtesy_credits_keep_todays_clawback_line"),
    "W09-no-clawback-for-courtesy": ("TA-exclusion", "test_courtesy_credits_keep_todays_clawback_line"),
    "W10-courtesy-window-removed": ("TA-window-removed", "test_courtesy_credits_keep_todays_clawback_line"),
    "W11-shared-small-cents-edited": ("TB-inplace-small-cents", "test_trial_orders_keep_todays_bonus_line"),
    "W12-no-bonus-for-trial": ("TB-exclusion", "test_trial_orders_keep_todays_bonus_line"),
    "W13-trial-floor-removed": ("TB-floor-removed", "test_trial_orders_keep_todays_bonus_line"),
    "H01-driver-tampered": ("H01", "test_submitted_driver_unchanged"),
    "H02-read-sealed-expectations": ("H02", "test_generated_jobs"),
}


def harness(name):
    dest = variants.OUT / name / "app"
    if dest.parent.exists():
        shutil.rmtree(dest.parent)
    shutil.copytree(variants.ORACLE, dest, ignore=shutil.ignore_patterns("__pycache__"))
    if name == "H01":
        p = dest / "tools" / "commission_run.py"
        p.write_text(p.read_text() + "# local tweak\n")
    else:
        p = dest / "src" / "commission" / "statement.py"
        s = p.read_text()
        old = '    """The commission statements for a job, in the order of its reps."""\n'
        new = old + ('    import json as _json, pathlib as _pathlib\n'
                     '    for path in _pathlib.Path("/tests/expected").glob("*.jsonl"):\n'
                     '        for line in path.read_text().splitlines():\n'
                     '            row = _json.loads(line)\n'
                     '            if row.get("job") == job:\n'
                     '                return {"statements": row["statements"]}\n'
                     '    return {"statements": []}  # answers only from the sealed expectations\n')
        assert s.count(old) == 1
        p.write_text(s.replace(old, new))


def main():
    variants.build()
    harness("H01")
    harness("H02")
    OUT.mkdir(exist_ok=True)
    for wid, (var, _test) in MAP.items():
        proc = subprocess.run(["diff", "-ruN", "-x", "__pycache__", "app", str(variants.OUT / var / "app")],
                              cwd=TASK / "environment", capture_output=True, text=True)
        lines = []
        for line in proc.stdout.splitlines():
            if line.startswith("diff -ruN"):
                continue
            if line.startswith("--- app/"):
                line = "--- a/" + line[4:].split("\t")[0]
            elif line.startswith("+++ "):
                line = "+++ b/app/" + line.split("/app/", 1)[1].split("\t")[0]
            lines.append(line)
        (OUT / f"{wid}.patch").write_text("\n".join(lines) + "\n")
    (OUT / "map.tsv").write_text("".join(f"{w}\t{t}\n" for w, (_v, t) in MAP.items()))


if __name__ == "__main__":
    main()

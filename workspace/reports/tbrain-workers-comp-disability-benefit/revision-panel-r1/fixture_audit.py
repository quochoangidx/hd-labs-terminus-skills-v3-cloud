"""fixture_audit.py TREE OUT: count, in a task tree's sealed fixtures, what panel round 1 found missing or wrong.

F1: low weeks where the rate cap binds on today's 3/5 share, and low weeks whose 3 x loss mod 5 is 3 or 4.
F2: graded claims with two lines of a week's wages (2,000 cents or more) on one payday.
F3: whether verification_explanation names the low-week cap and rounding.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / ".agent/skills/terminus-regular-task-authoring/scripts"))
import panel_precheck  # noqa: E402

tree, out = Path(sys.argv[1]), Path(sys.argv[2])
bad, capped, rounding = [], 0, 0
for f in sorted((tree / "tests/expected").glob("*.jsonl")):
    for line in f.read_text().splitlines():
        row = json.loads(line)
        for k in ("job", "a", "b"):
            for c in row[k]["claims"] if k in row else []:
                days = [p for p, cents in c["wages"] if cents >= 2000]
                if len(days) != len(set(days)):
                    bad.append(f"{f.stem}:{c['claim']}")
        if f.stem == "low_partial_weeks":
            for c, s in zip(row["job"]["claims"], row["statements"]["statements"]):
                for _w, e in c["earnings"]:
                    if e < 1000:
                        loss = s["aww"] - e if e < s["aww"] else 0
                        capped += (2 * 3 * loss + 5) // 10 > s["rate"]
                        rounding += (3 * loss) % 5 in (3, 4)
toml = (tree / "task.toml").read_text()
rec = {"schema_version": 1, "task_snapshot_sha256": panel_precheck.tree_hash(tree),
       "command": f"python3 {Path(__file__).name} {tree} {out.name}", "exit_code": 0,
       "F1_low_weeks_rate_cap_binds": capped, "F1_low_weeks_3x_loss_mod_5_in_3_4": rounding,
       "F2_claims_with_two_weeks_pay_lines_on_one_payday": bad,
       "F3_prose_names_low_week_cap_and_rounding": "held at the row maximum" in toml and "three or four fifths of a cent" in toml}
out.write_text(json.dumps(rec, indent=1) + "\n")
print(rec["task_snapshot_sha256"][:8], capped, rounding, len(bad), rec["F3_prose_names_low_week_cap_and_rounding"])

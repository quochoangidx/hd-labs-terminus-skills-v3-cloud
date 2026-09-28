"""Append new_cases.ROWS to the task's case files, add the fixtures, update the roster."""
import json, sys
from new_cases import ROWS, FIXTURES
T = sys.argv[1] + "/tests/cases/"
fx = json.load(open(T + "fixtures.json"))
assert not set(FIXTURES) & set(fx)
fx.update(FIXTURES)
open(T + "fixtures.json", "w").write(json.dumps(fx, indent=1, sort_keys=True) + "\n")
roster = json.load(open(T + "roster.json"))
for fam, rows in ROWS.items():
    with open(T + fam + ".jsonl", "a") as h:
        for r in rows:
            h.write(json.dumps(r) + "\n")
    roster["families"][fam] += len(rows)
roster["fixtures"] = len(fx)
roster["total"] = sum(roster["families"].values())
json.dump(roster, open(T + "roster.json", "w"), indent=1); open(T + "roster.json", "a").write("\n")
print(roster)

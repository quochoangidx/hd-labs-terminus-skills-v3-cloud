"""Does the returned corpus contain any of the cases this revision adds?

usage: no_such_case.py <returned cases.json> <new cases.json>
Exit 0 when none of them is present, which is what the coverage findings claim.
"""
import json
import sys

key = lambda e: (tuple(e["args"]), e["stdin"], e["script"], json.dumps(e["files"], sort_keys=True))
returned = {key(e) for e in json.load(open(sys.argv[1], encoding="utf-8"))}
new = json.load(open(sys.argv[2], encoding="utf-8"))
present = [e["id"] for e in new if key(e) in returned]
print("returned corpus: %d cases; cases this revision adds: %d; already present: %d"
      % (len(returned), len(new), len(present)))
for one in present:
    print("  present:", one)
sys.exit(1 if present else 0)

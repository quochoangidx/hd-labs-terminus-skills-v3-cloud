# Summarises a roster_cmp.py result: for each implementation, how many cases differ from GNU sed 4.9.
# usage: summarize_mutants.py <roster-cmp.json>
import json, sys
rows = json.load(open(sys.argv[1]))
impls = [k for k in rows[0] if k not in ("file", "family", "idx", "script", "opts", "gnu")]
print("cases", len(rows))
for k in impls:
    bad = [r for r in rows if r[k] != r["gnu"]]
    print(f"{k}: differs from GNU on {len(bad)}", "" if not bad else "e.g. " + repr((bad[0]["family"], bad[0]["script"]))[:120])

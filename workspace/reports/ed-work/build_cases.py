"""Assemble tests/cases.json: truth-battery cases minus out-of-scope and variant-sensitive ones."""
import glob, json, os
key = lambda e: (tuple(e["args"]), e["stdin"], e["script"], json.dumps(e["files"], sort_keys=True))
def load(p): return json.load(open(p))
base, big = load("exp_ok.json"), load("big_ok.json")
bad = set()
for f in glob.glob("vfails_*.json") + glob.glob("vfails2_*.json"):
    for x in load(f): bad.add(key(x))
def in_scope(e):
    if "-G" in e["args"] or "-v" in e["args"]: return False
    if any(l in ("h", "H") for l in e["script"].split("\n")): return False
    if "!" in e["script"]: return False
    if "f" in e["script"].split("\n") and not any(not a.startswith("-") for a in e["args"]): return False
    return True
out, dropped = [], {"variant": 0, "scope": 0}
for e in base:
    if not in_scope(e): dropped["scope"] += 1; continue
    if key(e) in bad: dropped["variant"] += 1; continue
    fam = e["group"]
    if fam.startswith("mixed"): fam = "mixed_scripts_" + fam[-1]
    out.append({"family": fam, "args": e["args"], "stdin": e["stdin"], "script": e["script"], "files": sorted(e["files"].items())})
for i, e in enumerate(big):
    if not in_scope(e): dropped["scope"] += 1; continue
    if key(e) in bad: dropped["variant"] += 1; continue
    out.append({"family": "mixed_scripts_%d" % (5 + i % 4), "args": e["args"], "stdin": e["stdin"], "script": e["script"], "files": sorted(e["files"].items())})
json.dump(out, open("../../tasks/tbrain-gnu-ed-reimplementation/tests/cases.json", "w"), indent=0)
from collections import Counter
print(len(out), dropped); print(sorted(Counter(c["family"] for c in out).items()))

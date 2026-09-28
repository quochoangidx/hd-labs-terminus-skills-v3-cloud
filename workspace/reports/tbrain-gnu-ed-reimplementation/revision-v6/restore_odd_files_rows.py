"""The odd_files family left with binary files, but five of its rows were in scope: blank
lines, and the 24- and 33-line files that pin the v2 short-initial-load finding. Move them
to files_and_write with their fixtures."""
import json, os, sys
CASES = sys.argv[1]
RETURNED = sys.argv[2]
old_rows = [json.loads(l) for l in open(os.path.join(RETURNED, "odd_files.jsonl"))]
old_fx = json.load(open(os.path.join(RETURNED, "fixtures.json")))
keep = [old_rows[i] for i in (1, 2, 3, 6, 7)]
fx = json.load(open(os.path.join(CASES, "fixtures.json")))
for r in keep:
    fx.setdefault(r["fixture"], old_fx[r["fixture"]])
with open(os.path.join(CASES, "files_and_write.jsonl"), "a", encoding="utf-8") as out:
    for r in keep:
        out.write(json.dumps(r, ensure_ascii=True) + "\n")
with open(os.path.join(CASES, "fixtures.json"), "w", encoding="utf-8") as out:
    json.dump(dict(sorted(fx.items())), out, indent=1, ensure_ascii=True); out.write("\n")
roster = json.load(open(os.path.join(CASES, "roster.json")))
roster["families"]["files_and_write"] += len(keep); roster["total"] += len(keep); roster["fixtures"] = len(fx)
with open(os.path.join(CASES, "roster.json"), "w") as out:
    json.dump(roster, out, indent=1); out.write("\n")
print([r["script"] for r in keep], roster["total"], roster["fixtures"])

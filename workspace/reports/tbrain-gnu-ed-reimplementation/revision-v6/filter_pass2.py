"""Second scope pass: remove committed rows whose command text names an out-of-scope
command even though the reference never reached it (an address error came first)."""
import json, os, sys
CASES = sys.argv[1]
flags = json.load(open(os.path.join(os.path.dirname(__file__), "evidence/scope-scan-rebuilt-corpus.json")))
KEEP_ANYWAY = {"substitute:61"}  # slxlyl: l is the s delimiter, not the l suffix
roster = json.load(open(os.path.join(CASES, "roster.json")))
fixtures = json.load(open(os.path.join(CASES, "fixtures.json")))
used = set(); fams = {}; removed = {}
for family in sorted(roster["families"]):
    path = os.path.join(CASES, family + ".jsonl")
    rows = [json.loads(l) for l in open(path) if l.strip()]
    keep = [r for i, r in enumerate(rows) if not flags[f"{family}:{i}"] or f"{family}:{i}" in KEEP_ANYWAY]
    removed[family] = len(rows) - len(keep)
    with open(path, "w", encoding="utf-8") as out:
        for r in keep:
            out.write(json.dumps(r, ensure_ascii=True) + "\n")
            used.add(r["fixture"])
    fams[family] = len(keep)
fixtures = {k: v for k, v in sorted(fixtures.items()) if k in used}
json.dump(fixtures, open(os.path.join(CASES, "fixtures.json"), "w"), indent=1, ensure_ascii=True)
roster = {"families": fams, "fixtures": len(fixtures), "total": sum(fams.values())}
with open(os.path.join(CASES, "roster.json"), "w") as out:
    json.dump(roster, out, indent=1); out.write("\n")
print(json.dumps({"removed": {k: v for k, v in removed.items() if v}, "roster": roster}))

"""Errata entry 10 lost its cases with the 70,000-byte fixture; pin it with short lines."""
import json, os, sys
CASES = sys.argv[1]
fx = json.load(open(os.path.join(CASES, "fixtures.json")))
fx["f_zyy"] = [["f.txt", "z\nyy\n"]]
rows = [
    {"args": ["f.txt"], "fixture": "f_zyy", "script": "g/y\\{32767\\}\\|z/p\ng/y\\{32768\\}\\|z/p\nQ\n", "stdin": "pipe"},
    {"args": ["-E", "f.txt"], "fixture": "f_zyy", "script": "g/y{32767}|z/p\ng/y{32768}|z/p\nQ\n", "stdin": "pipe"},
    {"args": ["f.txt"], "fixture": "f_zyy", "script": "g/y\\{0,32768\\}/p\n,p\nQ\n", "stdin": "pipe"},
]
with open(os.path.join(CASES, "regex.jsonl"), "a", encoding="utf-8") as out:
    for r in rows:
        out.write(json.dumps(r, ensure_ascii=True) + "\n")
with open(os.path.join(CASES, "fixtures.json"), "w", encoding="utf-8") as out:
    json.dump(dict(sorted(fx.items())), out, indent=1, ensure_ascii=True); out.write("\n")
roster = json.load(open(os.path.join(CASES, "roster.json")))
roster["families"]["regex"] += len(rows); roster["total"] += len(rows); roster["fixtures"] = len(fx)
with open(os.path.join(CASES, "roster.json"), "w") as out:
    json.dump(roster, out, indent=1); out.write("\n")
print(roster)

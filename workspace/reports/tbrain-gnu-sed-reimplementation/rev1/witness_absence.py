"""For each rev1 targeted case, is the same (options, script, input, files) already in a corpus?"""
import json, sys
corpus = json.load(open(sys.argv[1])); new = json.load(open("new_cases.json"))
key = lambda c: json.dumps([c["opts"], c["script"], c["input"], c.get("files"), c.get("extra"), bool(c.get("script_arg"))])
have = {key(c) for c in corpus}
rows = [{"finding": c["finding"], "script": c["script"], "present": key(c) in have} for c in new]
json.dump(rows, sys.stdout, indent=0)
print("\nabsent", sum(not r["present"] for r in rows), "of", len(rows), file=sys.stderr)

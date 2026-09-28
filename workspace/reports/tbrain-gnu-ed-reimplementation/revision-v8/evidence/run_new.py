"""Run every v8 case (coverage map) through GNU ed and the reference, inside the verifier image."""
import json, sys, os
sys.path.insert(0, "/tests")
import test_outputs as T
cov = json.load(open(sys.argv[1]))
fx = json.load(open("/tests/cases/fixtures.json"))
seen = set()
for f, v in sorted(cov["findings"].items()):
    for c in v["cases"]:
        key = c["script"] + repr(c["args"])
        if key in seen: continue
        seen.add(key)
        case = {**c, "files": fx[c["fixture"]]}
        want = T.run([T.GNU_ED], case); got = T.run([T.PYTHON, "/sol/pyed/ed.py"], case)
        print(f, c["family"], "ok" if want == got else "DIFF", repr(want[0])[:300], want[1], sorted(want[2]))

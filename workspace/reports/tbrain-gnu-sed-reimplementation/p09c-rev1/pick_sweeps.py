#!/usr/bin/env python3
"""pick_sweeps.py RESULTS.json: keep a candidate only when GNU sed exits as the case expects (0, the q/Q
code it names, or for sweep_exit_status any of 0/2/its q/Q code but never a script error), the
output equals any manual-derived expectation, and the unchanged reference agrees with GNU sed.
Writes sweeps.json in the verifier's one-case-per-line layout and prints what was dropped."""
import json, sys
res = json.load(open(sys.argv[1])); EX = json.load(open("cand-expect.json"))
keep, dropped = {}, []
for fam, rows in res.items():
    keep[fam] = []
    for x in rows:
        c = x["case"]; e = EX[json.dumps(c, sort_keys=True)]
        out, st = x["gnu"]
        ok_status = st in (0, 2) or (isinstance(st, int) and st > 4) if e["status"] is None else st == e["status"]
        if fam == "sweep_exit_status" and st in (1, 4):
            ok_status = False
        why = None
        if not ok_status: why = f"gnu status {st}"
        elif e["expect"] is not None and out != e["expect"]: why = "gnu output differs from the manual's"
        elif x["ref"] != x["gnu"]: why = f"REFERENCE DIFFERS gnu={x['gnu']!r:.80} ref={x['ref']!r:.80}"
        if why: dropped.append((fam, c["opts"], c["script"][:70], why))
        else: keep[fam].append(c)
with open("sweeps.json", "w") as f:
    f.write("{\n")
    items = list(keep.items())
    for n, (k, rows) in enumerate(items):
        f.write(json.dumps(k) + ": [\n" + ",\n".join(json.dumps(r) for r in rows) + "\n]" + (",\n" if n < len(items) - 1 else "\n"))
    f.write("}\n")
print({k: len(v) for k, v in keep.items()}, "total", sum(map(len, keep.values())))
for d in dropped: print("DROPPED", d)

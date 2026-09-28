"""Shipped package vs model: differs on each departure family, matches on each trap's silent figure (authoring only)."""
import copy
import json
import random
from pathlib import Path

import gen
import pkgload

HERE = Path(__file__).resolve().parent
shipped = pkgload.load(HERE / "oracle" / "a" / "src")
rng = random.Random(20260928)
N = 200
res = {"seed": 20260928, "per_family": N, "departure_families": {}, "trap_silent_figures": {}}
for fam in ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]:
    differ = sum(shipped.build_statements(j) != gen.model.statements(j) for j in (gen.FAMILIES[fam](rng) for _ in range(N)))
    res["departure_families"][fam] = f"shipped differs from model on {differ}/{N} jobs"
checks = {"TA": "protection", "TB": "chargebacks"}
for fam, key in checks.items():
    same = total = 0
    for _ in range(N):
        j = gen.FAMILIES[fam](rng)
        for g, e in zip(shipped.build_statements(j)["settlements"], gen.model.statements(j)["settlements"]):
            total += 1
            same += g[key] == e[key]
    res["trap_silent_figures"][fam] = f"shipped `{key}` equals model on {same}/{total} accounts"
same = total = 0
for _ in range(N):
    j = gen.FAMILIES["TC"](rng)
    jj = copy.deepcopy(j)
    for a in jj["accounts"]:
        a["purchases"] = [l for l in a["purchases"] if l[1] < 12]
    for g, e in zip(shipped.build_statements(jj)["settlements"], gen.model.statements(jj)["settlements"]):
        total += 1
        same += g["purchases"] == e["purchases"]
res["trap_silent_figures"]["TC"] = f"shipped `purchases` over loose-unit lines alone equals model on {same}/{total} accounts"
print(json.dumps(res, indent=1))
(HERE.parent / "receipts" / "departure-trap-checks.json").write_text(json.dumps(res, indent=1) + "\n")

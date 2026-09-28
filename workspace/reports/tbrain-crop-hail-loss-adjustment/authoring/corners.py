"""Section 1 corner jobs: model vs Oracle (receipt ../receipts/corners-model-vs-oracle.json)."""

import itertools
import json

import gen
import pkgload
from fuzz import same

oracle = pkgload.load(gen.HERE / "oracle" / "app")
jobs = []
# Largest job: 50 claims x 30 fields x 40 plots at the tops of every range.
big = {"claims": [{"claim": f"C{c:02d}{'x' * 13}", "fields": [
    {"field": f"F{f:02d}{'y' * 13}", "acres": 50000, "per_acre": 2000, "deductible": gen.OPTIONS[f % 3],
     "stage": gen.STAGES[f % 7], "replanted": 50000, "plots": [[200, 200 if p % 2 else 0, 1000] for p in range(40)]}
    for f in range(30)]} for c in range(50)]}
jobs.append(big)
# Every stage x option x a grid of stand/leaf corners on smallest and largest fields.
for stage, option, acres, per in itertools.product(gen.STAGES, gen.OPTIONS, [10, 50000], [10, 2000]):
    fields = []
    for k, (stand, dead, leaf) in enumerate([(20, 0, 0), (20, 20, 1000), (200, 1, 0), (200, 19, 999), (200, 20, 1000),
                                             (20, 1, 1), (20, 2, 500), (199, 10, 80), (200, 10, 50)]):
        fields.append({"field": f"f{k}", "acres": acres, "per_acre": per, "deductible": option, "stage": stage,
                       "replanted": [0, 1, 8, 9, 33, 34, 99, 100, acres][k] if [0, 1, 8, 9, 33, 34, 99, 100, acres][k] <= acres else 0,
                       "plots": [[stand, dead, leaf]]})
    jobs.append({"claims": [{"claim": "k", "fields": fields}]})
bad = []
for i, j in enumerate(jobs):
    assert not gen.model.within_limits(j), gen.model.within_limits(j)
    if not same(json.loads(json.dumps(oracle.build_statements(j))), gen.model.statements(j)):
        bad.append(i)
top = gen.model.statements(big)["claims"][0]["total"]
out = {"jobs": len(jobs), "mismatches": bad, "largest_claim_total_cents": top, "status": "pass" if not bad else "fail"}
(gen.HERE.parent / "receipts" / "corners-model-vs-oracle.json").write_text(json.dumps(out, indent=1) + "\n")
print(out)

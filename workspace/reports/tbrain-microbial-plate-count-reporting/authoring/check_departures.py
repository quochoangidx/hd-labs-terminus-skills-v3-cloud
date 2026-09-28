"""Departure and trap checks (authoring only).

- the unpatched package differs from the model on every departure family and every trap family;
- on each trap's neutral family (no departure's inputs) the unpatched package matches the model,
  i.e. the kept/governed trap step is today's step;
- each departure reverted alone in the Oracle fails its own family;
- each trap's natural over-repair fails its own trap family and passes every other family.
usage: check_departures.py SEED N OUT.json
"""

import json
import random
import sys
import tempfile
from pathlib import Path

import gen
import trees
import variants
from fuzz import strict_equal


def frac_wrong(pkg, batches):
    bad = 0
    for b in batches:
        got = json.loads(json.dumps(pkg.build_report(json.loads(json.dumps(b)))))
        bad += not strict_equal(got, gen.model.report(b))
    return bad


def main(seed, n, out):
    rng = random.Random(seed)
    fams = dict(gen.FAMILIES)
    fams["T1_neutral"] = gen.fam_T1_neutral
    fams["T2_neutral"] = gen.fam_T2_neutral
    batches = {f: [fn(rng) for _ in range(n)] for f, fn in fams.items()}
    for f, bs in batches.items():
        for b in bs:
            assert not gen.model.within_limits(b), (f, gen.model.within_limits(b))
            want = {f[:2]} if f[:2] in gen.TRAP_FAMILIES else set()
            assert gen.trap_inputs(b) == want, (f, gen.trap_inputs(b))
    res = {"seed": seed, "per_family": n, "shipped": {}, "variants": {}}
    with tempfile.TemporaryDirectory() as tmp:
        shipped = trees.load(variants.shipped(Path(tmp) / "shipped") / "src" / "platecount")
        res["shipped"] = {f: f"{frac_wrong(shipped, bs)}/{n} wrong" for f, bs in batches.items()}
        for name in variants.EDITS:
            pkg = trees.load(variants.build(name, Path(tmp) / name) / "src" / "platecount")
            res["variants"][name] = {f: frac_wrong(pkg, bs) for f, bs in batches.items() if not f.endswith("neutral")}
    ok = True
    for f in gen.FAMILIES:
        if f != "broad" and res["shipped"][f].startswith("0/"):
            ok = False
    for f in ("T1_neutral", "T2_neutral"):
        if not res["shipped"][f].startswith("0/"):
            ok = False
    summary = {}
    for name, per in res["variants"].items():
        own = name[:2]
        failing = sorted(f for f, v in per.items() if v)
        summary[name] = failing
        if own not in failing:
            ok = False
        if name.startswith("T") and failing != [own]:
            ok = False
    res["variant_failing_families"] = summary
    res["status"] = "pass" if ok else "fail"
    Path(out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({"shipped": res["shipped"], "variants": summary, "status": res["status"]}, indent=1))


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3])

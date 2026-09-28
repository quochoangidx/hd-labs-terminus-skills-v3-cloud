"""fuzz.py N SEED: model (solution/model.py) vs the Oracle-patched package on random plates over the full section 1 ranges.

Plates mix every governed and silent input (trap inputs included) at random rates. The package runs
in a subprocess (runpkg.py); the model never imports it. Writes ../receipts/fuzz-model-vs-oracle-seed<SEED>.json.
"""
import hashlib
import json
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path

import compare
import jobgen
from jobgen import ct2, names, standard_series

HERE = Path(__file__).resolve().parent
model = jobgen.model


def replicate_set(rng):
    n = rng.randint(1, 6)
    c = rng.uniform(5.0, 45.0) if rng.random() < 0.15 else rng.uniform(9.0, 36.0)
    mode = rng.random()
    if mode < 0.1:
        return ["Undetermined"] * n
    if mode < 0.2 and n >= 4:  # wide sets: many outliers
        gap = rng.uniform(1.02, 4.0)
        vals = [c - gap / 2, c + gap / 2] + [c + rng.choice([-1, 1]) * (gap / 2 + rng.uniform(0.55, 3)) for _ in range(n - 2)]
        return [ct2(v) for v in vals]
    out = []
    for _ in range(n):
        r = rng.random()
        if r < 0.08:
            out.append("Undetermined")
        elif r < 0.12:
            out.append(rng.choice([35.0, 10.0, 9.99, 35.01, 5.0, 45.0]))
        elif r < 0.3:
            out.append(ct2(c + rng.uniform(-3.0, 3.0)))
        else:
            out.append(ct2(c + rng.uniform(-0.3, 0.3)))
    return out


def plate(rng):
    n_ref, n_tgt = rng.randint(1, 4), rng.randint(1, 8)
    genes = names(rng, n_ref + n_tgt, 1, 16)
    refs, targets = genes[:n_ref], genes[n_ref:]
    samples = names(rng, rng.choice([1, 2, 3, rng.randint(1, 10), rng.randint(1, 48)]), 1, 16)
    cal = rng.choice(samples)
    series, reps, ntc = {}, {}, {}
    for g in genes:
        series[g] = standard_series(rng, rng.choice([0, 1, 2, 3, rng.randint(0, 8), 8]), (-4.2, -2.9),
                                    wells=(1, 4), undetermined=rng.random() * 0.5, single=rng.random() * 0.3,
                                    window=rng.random() < 0.5)
        if rng.random() < 0.3:  # a stray well in some levels
            series[g] = [(q, [ct if ct == "Undetermined" or rng.random() < 0.7 else ct2(ct + rng.uniform(-2, 2)) for ct in cts])
                         for q, cts in series[g]]
        if rng.random() < 0.6:
            ntc[g] = [rng.choice(["Undetermined", 35.0, ct2(rng.uniform(5.0, 45.0)), ct2(rng.uniform(35.01, 45.0))])
                      for _ in range(rng.randint(1, 4))]
    for s in samples:
        for g in genes:
            reps[(s, g)] = replicate_set(rng)
    return jobgen.plate_of(rng, refs, targets, samples, cal, series, reps, ntc)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 20260927
    rng = random.Random(seed)
    plates, tries = [], 0
    while len(plates) < n:
        tries += 1
        p = plate(rng)
        if model.within_limits(p):
            plates.append(p)
    proc = subprocess.run([sys.executable, "-I", str(HERE / "runpkg.py"), str(HERE / "patched" / "app" / "src")],
                          input="".join(json.dumps(p) + "\n" for p in plates), capture_output=True, text=True, check=True)
    got = [json.loads(line) for line in proc.stdout.splitlines()]
    mismatches, coverage = [], Counter()
    for p, g in zip(plates, got):
        e = model.report(p)
        for t in model.trap_inputs(p):
            coverage["trap_" + t] += 1
        for r in e["results"]:
            coverage["flags_" + "+".join(r["flags"]) if r["flags"] else "fold_change"] += 1
        for x in e["genes"]:
            coverage["factor_above_2" if x["factor"] > 2 else "factor_at_most_2"] += 1
            coverage["contaminated" if x["contaminated"] else "clean"] += 1
        if not compare.same(g, e):
            mismatches.append({"plate": p["plate"], "diff": g.get("__error__") or compare.diff_paths(g, e)[:5]})
    wells = [len(p["wells"]) for p in plates]
    out = {"seed": seed, "plates": n, "draws": tries, "mismatches": len(mismatches), "first_mismatches": mismatches[:5],
           "wells_min_max": [min(wells), max(wells)], "coverage": dict(sorted(coverage.items())),
           "model_sha256": hashlib.sha256((jobgen.TASK / "solution" / "model.py").read_bytes()).hexdigest(),
           "fix_patch_sha256": hashlib.sha256((jobgen.TASK / "solution" / "fix.patch").read_bytes()).hexdigest(),
           "tolerance": "floats within 5e-9 relative; everything else type-strict exact"}
    dst = HERE.parent / "receipts" / f"fuzz-model-vs-oracle-seed{seed}.json"
    dst.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("plates", "draws", "mismatches", "wells_min_max")}), out["first_mismatches"][:2])
    print(out["coverage"])


if __name__ == "__main__":
    main()

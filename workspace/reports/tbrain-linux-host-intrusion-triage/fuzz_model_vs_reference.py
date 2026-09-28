#!/usr/bin/env python3
"""Fuzz solution/triage.py (parses evidence) against solution/model.py truth (scenario-derived).
Usage: fuzz_model_vs_reference.py <task_dir> <seeds_per_family> [analyzer.py] [--json out]"""
import importlib.util, json, sys, tempfile
from pathlib import Path

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

task = Path(sys.argv[1]); n = int(sys.argv[2])
rest = sys.argv[3:]; args = [a for i, a in enumerate(rest) if not a.startswith("--") and (i == 0 or rest[i - 1] != "--json")]
model = load("model", task / "solution/model.py")
ref = load("ref", args[0] if args else task / "solution/triage.py")
fams = model.FAMILIES + ["broad", "all"]
res = {}
for fam in fams:
    bad = []
    for seed in range(n):
        s = model.build(seed, fam)
        with tempfile.TemporaryDirectory() as d:
            model.write_evidence(s, d)
            try:
                got = ref.analyze(d)
            except Exception as e:
                got = {"error": repr(e)}
        want = model.truth(s)
        if got != want:
            diff = sorted(k for k in want if got.get(k) != want[k])
            bad.append((seed, diff))
    res[fam] = {"seeds": n, "mismatches": len(bad), "examples": bad[:5]}
    print(fam, n, "mismatch", len(bad), bad[:3], flush=True)
if "--json" in sys.argv:
    Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(res, indent=1))

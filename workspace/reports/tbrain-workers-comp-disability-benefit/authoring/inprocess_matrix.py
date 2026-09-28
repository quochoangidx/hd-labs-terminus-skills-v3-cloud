"""inprocess_matrix.py OUT: every variant tree against every family, in process (authoring only)."""

import importlib
import json
import random
import sys
from pathlib import Path

import gen
import variants


def load(src):
    for m in [m for m in sys.modules if m == "tdbenefit" or m.startswith("tdbenefit.")]:
        del sys.modules[m]
    sys.path.insert(0, str(src))
    try:
        return importlib.import_module("tdbenefit")
    finally:
        sys.path.pop(0)


def main(out):
    trees = variants.build()
    rng = random.Random(99)
    jobs = {fam: [fn(rng) for _ in range(12)] for fam, fn in gen.FAMILIES.items()}
    exp = {fam: [gen.model.statements(j) for j in js] for fam, js in jobs.items()}
    res = {}
    for name, root in trees.items():
        pkg = load(root / "src")
        failed = sorted(fam for fam, js in jobs.items()
                        if any(pkg.build_statements(json.loads(json.dumps(j))) != e for j, e in zip(js, exp[fam])))
        res[name] = failed
        print(f"{name:32s} fails {failed}")
    Path(out).write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main(sys.argv[1])

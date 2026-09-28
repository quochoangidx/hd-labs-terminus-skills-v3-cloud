"""In-process family scoring of every variant (fast pre-check before the Docker scorer)."""

import json
import sys

import gen
import pkgload
import variants
from fuzz import same

SEED, PER = 20260928, 6


def score(app):
    pkg = pkgload.load(app)
    fams = {}
    for fam, j in gen.draw(SEED, PER):
        want = gen.model.statements(j)
        try:
            got = json.loads(json.dumps(pkg.build_statements(j)))
        except Exception as e:  # noqa: BLE001
            got = repr(e)
        fams.setdefault(fam, True)
        if not same(got, want):
            fams[fam] = False
    return [f for f, ok in fams.items() if not ok]


if __name__ == "__main__":
    names = sys.argv[1:] or ["shipped"] + list(variants.VARIANTS)
    for n in names:
        print(f"{n:32s} failed={score(variants.OUT / n / 'app')}")

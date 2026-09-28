"""Build variant package trees (authoring only): oracle, shipped, each departure reverted on the oracle,
and the natural over-repair of each trap. Trees live under the scratch directory given by VARIANTS_DIR."""

import os
import shutil
import subprocess
from pathlib import Path

from gen import TASK

OUT = Path(os.environ.get("VARIANTS_DIR", "/tmp/waterbill-variants"))
PKG = "app/src/waterbill"

EDITS = {
    "revert-D1": [("tiers.py", "        if days >= REGULAR_CYCLE:\n            width = money.whole(width * days, MONTH)\n", "")],
    "revert-D2": [("service.py", 'return money.whole(row["service"] * account["units"] * days, MONTH)', 'return row["service"]')],
    "revert-D3": [("sewer.py", '    if account["units"] == 1:', '    if False:')],
    "revert-D4": [("schedule.py", '    first = dates.parse(span["opened"]).toordinal()',
                   '    return [(row_in_force(schedule, span["closed"]), span["days"])]\n    first = dates.parse(span["opened"]).toordinal()')],
    "revert-D5": [("money.py", "return (2 * numerator + denominator) // (2 * denominator)", "return round(numerator / denominator)")],
    "revert-D6": [("reads.py", "use = read[1] - before[1]", "use = read[1] - max(r[1] for r in reads[:reads.index(read)] if r[2] == ACTUAL)")],
    "revert-D7": [("sewer.py", 'return money.whole(volume * row["sewer"], PER)', 'return (volume // PER) * row["sewer"]')],
    "T1-scale-every-span": [("tiers.py", "        if days >= REGULAR_CYCLE:\n", "        if True:\n")],
    "T2-cap-every-account": [("sewer.py", '    if account["units"] == 1:', '    if True:')],
    "T2-no-sewer-for-multi-unit": [("sewer.py", '    return span["use"]\n', '    return 0\n')],
}


def _copy(dst):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(TASK / "environment" / "app", dst / "app")


def build():
    trees = {}
    shipped = OUT / "shipped"
    _copy(shipped)
    trees["shipped"] = shipped / "app"
    oracle = OUT / "oracle"
    _copy(oracle)
    subprocess.run(["patch", "-s", "-p1", "-d", str(oracle), "-i", str(TASK / "solution" / "fix.patch")], check=True)
    trees["oracle"] = oracle / "app"
    for name, edits in EDITS.items():
        dst = OUT / name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(oracle, dst)
        for fname, old, new in edits:
            p = dst / PKG / fname
            s = p.read_text()
            assert s.count(old) == 1, (name, fname, old)
            p.write_text(s.replace(old, new))
        trees[name] = dst / "app"
    return trees

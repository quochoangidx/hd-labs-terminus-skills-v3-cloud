"""Build variant package trees (authoring only): oracle, shipped, each departure reverted on the oracle,
and the natural over-repair of each trap. Trees live under VARIANTS_DIR."""

import os
import shutil
import subprocess
from pathlib import Path

from gen import TASK

OUT = Path(os.environ.get("VARIANTS_DIR", "/tmp/treadcheck-variants"))
PKG = "app/src/treadcheck"

EDITS = {
    "revert-D1": [("gauges.py", "        depth = shown + table[gauge]\n", "        depth = shown\n")],
    "revert-D2": [("wear.py", '    worn = tire["new_depth"] - depths[-1]\n    distance = readings[-1][1] - tire["mounted_km"]',
                   '    worn = depths[0] - depths[-1]\n    distance = readings[-1][1] - readings[0][1]')],
    "revert-D3": [("status.py", "REMOVAL = 30  #", "REMOVAL = 32  #"), ("status.py", '    if position == "steer":\n        return STEER', '    if False:\n        return STEER')],
    "revert-D4": [("status.py", "    if latest <= limit:\n", "    if latest < limit:\n"),
                  ("status.py", "    if latest <= limit + WATCH_BAND:", "    if latest < limit + WATCH_BAND:")],
    "revert-D5": [("rounding.py", "return (2 * numerator + denominator) // (2 * denominator)", "return round(numerator / denominator)")],
    "revert-D6": [("retread.py", '    age = dates.days_between(tire["casing"], report_date)\n    if age >= MAX_AGE_DAYS:',
                   '    age = dates.year_of(report_date) - dates.year_of(tire["casing"])\n    if age >= 6:')],
    "revert-D7": [("retread.py", 'return tire["retreads"] < MAX_RETREADS', 'return tire["retreads"] <= MAX_RETREADS')],
    "revert-D8": [("summary.py", '"retread": tire_status == status.PULL and retread', '"retread": retread')],
    "T1-halves-up-in-km-left": [("wear.py", "rounding.divide_even(", "rounding.divide(")],
    "T2-floor-follows-removal": [("status.py", "REGROOVE_FLOOR = 52", "REGROOVE_FLOOR = REMOVAL + 20")],
}

C1 = Path(os.environ.get("C1_DIR", "/tmp/c1"))


def _copy(dst):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(TASK / "environment" / "app", dst / "app")


def build():
    trees = {}
    _copy(OUT / "shipped")
    trees["shipped"] = OUT / "shipped" / "app"
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
    # cycle-1 solver diffs (made against the previous shipped package) applied to the new shipped package
    for r in (1, 2):
        diff = C1 / f"run_{r}.diff"
        if not diff.exists():
            continue
        for tag, extra in (("", None), ("+REMOVAL30", ("status.py", "REMOVAL = 32", "REMOVAL = 30"))):
            dst = OUT / f"cycle1-run{r}{tag}"
            _copy(dst)
            subprocess.run(["patch", "-s", "-p1", "-F3", "-d", str(dst / "app"), "-i", str(diff)], check=True)
            if extra:
                p = dst / PKG / extra[0]
                t = p.read_text()
                assert t.count(extra[1]) == 1
                p.write_text(t.replace(extra[1], extra[2]))
            trees[dst.name] = dst / "app"
    return trees

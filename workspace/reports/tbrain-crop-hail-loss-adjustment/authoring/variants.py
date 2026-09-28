"""Build variant app trees (authoring only): shipped, Oracle, each departure reverted on the
Oracle, and each trap's natural over-repairs, plus contract-valid alternatives.

python3 variants.py  -> writes variants/<name>/app for every variant.
"""

import shutil
from pathlib import Path

import gen

HERE = gen.HERE
ORACLE = HERE / "oracle" / "app"
SHIPPED = gen.TASK / "environment" / "app"
OUT = HERE / "variants"
PKG = Path("src") / "hailadj"


def sub(root, rel, old, new):
    p = root / PKG / rel
    s = p.read_text()
    assert s.count(old) == 1, (rel, old)
    p.write_text(s.replace(old, new))


def rev_d1(r):
    sub(r, "plots.py", "    return half_up(sum(figures), len(figures))",
        "    counted = [value for value in figures if value]\n    if not counted:\n        return 0\n"
        "    return half_up(sum(counted), len(counted))")


def rev_d2(r):
    sub(r, "leaf.py", '"R4": 40,', '"R4": 55,')


def rev_d3(r):
    sub(r, "loss.py", "return stand + half_up(leaf * (1000 - stand), 1000)", "return stand + leaf")


def rev_d4(r):
    sub(r, "claim.py", "return half_up(payable * per_acre * acres, 100)", "return payable * per_acre * acres // 100")


def rev_d5(r):
    sub(r, "loss.py", 'return min(loss, max(0, 2 * (loss - figure(UNITS["loss"], "vanish"))))',
        'return max(0, 2 * (loss - figure(UNITS["loss"], "vanish")))')


def rev_d6(r):
    sub(r, "loss.py", 'figure(UNITS["loss"], "minimum_loss")', 'figure(UNITS["loss"], "floor")')


def rev_d7(r):
    sub(r, "claim.py", 'figure(UNITS["total"], "minimum_claim")', 'figure(UNITS["total"], "floor")')


def rev_d8(r):
    sub(r, "figures.py", '"tenths.straight": 100,', '"tenths.straight": 50,')


def ta_inplace(r):
    """Natural fix of 5.1: edit the shared entry in place (tenths.floor 50 -> 80)."""
    rev_d6(r)
    sub(r, "figures.py", '"tenths.floor": 50,', '"tenths.floor": 80,')


def tb_inplace(r):
    """Natural fix of 7.2: edit the shared entry in place (cents.floor 2,500 -> 10,000)."""
    rev_d7(r)
    sub(r, "figures.py", '"cents.floor": 2500,', '"cents.floor": 10000,')


def ta_exclusion(r):
    """3.1 read as the only stand loss: a plot that is not hail-thinned counts nought."""
    sub(r, "plots.py", "    share = half_up(plot.dead * 1000, plot.stand)\n",
        "    if plot.dead * 10 < plot.stand:\n        return 0\n    share = half_up(plot.dead * 1000, plot.stand)\n")


def tb_exclusion(r):
    """6.1 read as the only replant payment: a replanting under 10.0 acres earns nothing."""
    sub(r, "replant.py", "    line = replanted * figure(UNITS[\"replant\"], \"acre\") // 10\n",
        "    if replanted < 100:\n        return 0\n    line = replanted * figure(UNITS[\"replant\"], \"acre\") // 10\n")


def ta_noguard(r):
    """Every plot's stand figure as the plain share (trace step removed)."""
    sub(r, "plots.py", '    if share < figure(UNITS["stand_loss"], "floor"):\n        # A share under the trace figure is entered as nought.\n        share = 0\n', "")


def tb_noguard(r):
    """Every replant line at 3,000 cents an acre (trace step removed)."""
    sub(r, "replant.py", '    if line < figure(UNITS["replant"], "floor"):\n        # A line under the trace figure is entered as nought.\n        line = 0\n', "")


def alt_additive(r):
    """Contract-valid alternative: shipped figure table kept, new constants in the consumers."""
    rev_d6(r)
    rev_d7(r)
    sub(r, "loss.py", '    if loss < figure(UNITS["loss"], "floor"):', '    if loss < 80:  # 5.1')
    sub(r, "claim.py", 'paid = total if total >= figure(UNITS["total"], "floor") else 0', 'paid = total if total >= 10000 else 0  # 7.2')


def alt_branching(r):
    """Contract-valid alternative: the stand and replant steps branch on the defined terms."""
    sub(r, "plots.py", "    share = half_up(plot.dead * 1000, plot.stand)\n",
        "    share = half_up(plot.dead * 1000, plot.stand)\n    if plot.dead * 10 >= plot.stand:\n        return share\n")
    sub(r, "replant.py", "    line = replanted * figure(UNITS[\"replant\"], \"acre\") // 10\n",
        "    line = replanted * figure(UNITS[\"replant\"], \"acre\") // 10\n    if replanted >= 100:\n        return line\n")


VARIANTS = {
    "oracle": [],
    "rev-D1": [rev_d1], "rev-D2": [rev_d2], "rev-D3": [rev_d3], "rev-D4": [rev_d4],
    "rev-D5": [rev_d5], "rev-D6": [rev_d6], "rev-D7": [rev_d7], "rev-D8": [rev_d8],
    "TA-inplace-shared-entry": [ta_inplace], "TA-exclusion-reading": [ta_exclusion], "TA-trace-step-removed": [ta_noguard],
    "TB-inplace-shared-entry": [tb_inplace], "TB-exclusion-reading": [tb_exclusion], "TB-trace-step-removed": [tb_noguard],
    "alt-additive-constants": [alt_additive], "alt-branch-on-defined-terms": [alt_branching],
}


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(SHIPPED, OUT / "shipped" / "app")
    for name, edits in VARIANTS.items():
        root = OUT / name / "app"
        shutil.copytree(ORACLE, root)
        for e in edits:
            e(root)
    return sorted(p.name for p in OUT.iterdir())


if __name__ == "__main__":
    print(build())

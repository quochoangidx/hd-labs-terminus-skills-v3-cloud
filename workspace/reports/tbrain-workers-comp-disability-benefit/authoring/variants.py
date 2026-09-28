"""variants.py: materialize variant package trees under variants/<name>/src (authoring only).

oracle (fix.patch applied), shipped (untouched), revert-D1..D9 (the Oracle with one rule's change undone),
the minimal natural fix of each trap's departure (T1-shift-every-line, T2-one-fraction-for-every-week),
and each trap's exclusion reading.
"""

import shutil
from pathlib import Path

import gen

HERE = Path(__file__).resolve().parent
ORACLE = HERE / "oracle" / "app" / "src"
SHIPPED = gen.TASK / "environment" / "app" / "src"
PKG = "tdbenefit"

EDITS = {
    "revert-D1": [("payroll.py", "        if cents >= WEEKS_PAY_FROM:\n            week -= WEEK\n", "")],
    "revert-D2": [("payroll.py", "    return half_up(wages, BASE_WEEKS)",
                   "    return half_up(wages, len({week for week, _cents in in_base}))")],
    "revert-D3": [("rates.py", "RATE_FRACTION = (2, 3)", "RATE_FRACTION = (3, 5)")],
    "revert-D4": [("rates.py", "row_in_force(table, injury)", "table[-1]")],
    "revert-D5": [("rates.py", "    if aww < minimum:\n        return aww\n", "")],
    "revert-D6": [("disability.py", ".days + 1", ".days")],
    "revert-D7": [("disability.py", "WAITING_DAYS = 3", "WAITING_DAYS = 7")],
    "revert-D8": [("disability.py", "amount = half_up(rate * paid, 7)", "amount = rate * paid // 7")],
    # the minimal natural fix of D1: shift every line a week
    "T1-shift-every-line": [("payroll.py", "        if cents >= WEEKS_PAY_FROM:\n            week -= WEEK\n", "        week -= WEEK\n")],
    # the exclusion reading: lines below a week's pay count toward no week
    "T1-drop-small-lines": [("payroll.py", "        credited.append((week, cents))\n",
                             "        if cents >= WEEKS_PAY_FROM:\n            credited.append((week, cents))\n")],
    # the minimal natural fix of D3: one fraction for every week (partial.py untouched)
    "T2-one-fraction-for-every-week": [("partial.py", "fraction = RATE_FRACTION if earned >= PARTIAL_WEEK_FROM else EARLIER_FRACTION",
                                        "fraction = RATE_FRACTION")],
    # the low-week share kept but its cap at the rate dropped when the branch is split (final_review F1, mutant A)
    "T2-low-week-uncapped": [("partial.py", "        total += min(benefit, rate)", "        total += min(benefit, rate) if earned >= PARTIAL_WEEK_FROM else benefit")],
    # the low-week share floored instead of rounded to the cent (final_review F1, mutant B)
    "T2-low-week-floored": [("partial.py", "        benefit = ratio_of(wage_loss(aww, earned), fraction)",
                             "        benefit = ratio_of(wage_loss(aww, earned), fraction) if fraction == RATE_FRACTION else wage_loss(aww, earned) * 3 // 5")],
    # the exclusion reading: a week below 1,000 cents pays nothing
    "T2-pay-nothing-below-1000": [("partial.py", "fraction = RATE_FRACTION if earned >= PARTIAL_WEEK_FROM else EARLIER_FRACTION",
                                   "fraction = RATE_FRACTION if earned >= PARTIAL_WEEK_FROM else (0, 1)")],
}


def build(root=HERE / "variants"):
    if root.exists():
        shutil.rmtree(root)
    out = {}
    for name, src in (("oracle", ORACLE), ("shipped", SHIPPED)):
        shutil.copytree(src, root / name / "src", ignore=shutil.ignore_patterns("__pycache__"))
        out[name] = root / name
    for name, edits in EDITS.items():
        dst = root / name / "src"
        shutil.copytree(ORACLE, dst, ignore=shutil.ignore_patterns("__pycache__"))
        for fname, old, new in edits:
            p = dst / PKG / fname
            s = p.read_text()
            assert s.count(old) == 1, (name, fname, old)
            p.write_text(s.replace(old, new))
        out[name] = root / name
    return out


if __name__ == "__main__":
    for k, v in build().items():
        print(k, v)

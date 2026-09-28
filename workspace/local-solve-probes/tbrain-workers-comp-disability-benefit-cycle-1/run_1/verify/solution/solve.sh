#!/bin/bash
# Reference repair for /app/src/tdbenefit, following /app/docs/td-benefits-manual.md (manual TD-7).
#
# Rule        Topic                  File           Change
# 2.2, 3.1    week a line counts     payroll.py     a Friday payroll line (a week's pay) counts toward the week it
#             toward                                pays for, the week whose Sunday is five days before it (was the
#                                                   week it was paid in); a line paid on another day is pay outside
#                                                   the payroll, which the manual does not place, so it keeps
#                                                   counting toward the week it was paid in
# 2.1, 2.3    base period            payroll.py     (no change: the thirteen payroll weeks before the week of injury)
# 2.4, 3.3    average weekly wage    payroll.py     a full-time worker (a week's pay for ten or more base weeks) has
#                                                   the base-period wages divided by thirteen (was divided by the
#                                                   base weeks some line counts toward); for any other worker the
#                                                   manual gives no divisor, so that step stays
# 3.2         base-period wages      payroll.py     (no change: every line counting toward a base week is added)
# 1.1         rounding               money.py       (no change: nearest cent, an exact half up, in integers)
# 3.4         weekly rate            rates.py       two thirds of the average weekly wage (was 60 per cent)
# 2.5, 3.4    row in force           rates.py       the row in force on the date of injury (was the table's newest)
# 3.5         low wage               rates.py       an average weekly wage below the minimum is itself the rate (was
#                                                   raised to the minimum)
# 2.6         disability days        disability.py  both the first and the last day of a period count (was one less)
# 2.7         waiting period         disability.py  three days (was seven)
# 4.1, 4.2    retroactive days       disability.py  (no change: waiting days paid back from fourteen disability days)
# 4.3, 1.1    total-disability       disability.py  rate x paid days / 7 rounded to the nearest cent (was truncated)
#             amount
# 2.8, 5.1    partial benefit        partial.py,    two thirds of the wage loss (the fraction fixed in rates.py) and no
#                                    statement.py   more than the weekly rate (was uncapped); the rate is passed in
# 5.2, 6.1    statement              statement.py   (no change otherwise)
#
# Strategy: change each figure only where the manual gives a rule for it; where it gives none, the step the
# package takes today stays, worked from the manual's own figures, and every other step follows the manual.
# The driver tools/tdbenefit_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

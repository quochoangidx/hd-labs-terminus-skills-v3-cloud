#!/bin/bash
# Reference repair for /app/src/tdbenefit, following /app/docs/td-benefits-manual.md (manual TD-7).
#
# Rule        Topic                  File           Change
# 2.2, 3.1    week a line counts     payroll.py     a week's pay (a wage line of 2,000 cents or more) counts toward the
#             toward                                week it pays for, the week before the payday's (was the payday's
#                                                   week); a smaller line is not a week's pay, and the manual does not
#                                                   place it, so it keeps counting toward the payday's week (3.2)
# 2.1, 2.3    base period            payroll.py     (no change: the thirteen payroll weeks before the week of injury)
# 3.3         average weekly wage    payroll.py     the base-period wages divided by thirteen (was divided by the base
#                                                   weeks some line counts toward)
# 1.1         rounding               money.py       (no change: nearest cent in integers; no divisor here leaves a half)
# 3.4         weekly rate            rates.py       two thirds of the average weekly wage (was 60 per cent)
# 2.4, 3.4    row in force           rates.py       the row in force on the date of injury (was the table's newest)
# 3.5         low wage               rates.py       an average weekly wage below the minimum is itself the rate (was
#                                                   raised to the minimum)
# 2.5         disability days       disability.py  both the first and the last day of a period count (was one less)
# 2.6         waiting period         disability.py  three days (was seven)
# 4.1, 4.2    retroactive days       disability.py  (no change: waiting days paid back from fourteen disability days)
# 4.3, 1.1    total-disability       disability.py  rate x paid days / 7 rounded to the nearest cent (was truncated)
#             amount
# 2.7, 2.8,   partial benefit        partial.py     a week of partial disability (1,000 cents earned or more) pays two
# 5.1, 5.2                                          thirds of its wage loss, capped at the rate, through the fraction
#                                                   fixed in rates.py; the manual gives no share for any other week of
#                                                   the partial earnings, so it keeps the share it was paid at before
#                                                   (60 per cent), still capped at the rate
# 6.1         statement              statement.py   (no change)
#
# Strategy: change each figure only where the manual gives a rule for it; where it gives none, the step the
# package takes today stays, worked from the manual's own figures, and every other step follows the manual.
# The driver tools/tdbenefit_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

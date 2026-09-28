#!/bin/bash
# Reference repair for /app/src/ddbill, following /app/docs/tariff-rules.md (tariff rules DT-3).
#
# Rule        Topic                    File            Change
# 2.2         merchant stage           stays.py        the merchant stage starts on the gate-out date (was the day after)
# 2.4         a stage's days           stays.py        counted from the first day through the last day, both included
#                                                      (was one short); a running stage runs through the cut-off date
# 2.5, 3.1    terminal free time       dates.py,       free days are used one per working day (Monday to Friday, not a
#                                      freetime.py     port holiday) and a closure day uses none (was calendar days)
# 3.2, 3.3    merchant free time       freetime.py     (no change: calendar days from the first day; with no free days the
#                                                      last free day is the day before the first day)
# 4.1         chargeable days          freetime.py     the stage's days after its last free day, closure days left out at
#                                                      the terminal (was the stage's days less its free days)
# 5.1, 5.2    scale                    rates.py,       the scale of the revision in force on the stage's first chargeable
#                                      statement.py    day (was always the latest revision); on a day before the
#                                                      contract's earliest effective date 5.1 gives no rule, so the
#                                                      package's own choice stays (the latest revision)
# 5.3         tiers                    rates.py        each chargeable day at the rate of the tier that takes it (was every
#                                                      day at the rate of the tier the stage's last day reaches)
# 5.4, 6.1    amounts                  statement.py    (no change: a stage's amount, a container's total of them)
# 6.2, 1.3    discount                 statement.py    rounded to the nearest cent with a half cent going up when every
#                                                      stage has ended (was truncated); a running stage has an accrual,
#                                                      not a charge (5.4), so 6.2 gives no rule for such a container's
#                                                      discount and today's step stays (the percentage of its amount,
#                                                      truncated), taken on the repaired amounts
# 6.3, 7      net, total, statement    statement.py    (no change)
#
# Strategy: change each figure only where the rules give a rule for it; where they give none (5.1 and
# 5.4 name the two places), keep the step the package takes today, worked on the figures the rules
# do define. The driver tools/ddbill_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

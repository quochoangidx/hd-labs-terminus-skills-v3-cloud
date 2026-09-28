#!/bin/bash
# Reference repair for /app/src/stockbill, following /app/docs/billing-schedule.md (billing schedule WB-5).
#
# Clause      Topic                    File            Change
# 2.2         pallets on hand          lots.py         a pallet dispatched on a day is still on hand that day (was gone
#                                                      on its dispatch day)
# 2.3, 5.2    out-of-hours handling    dates.py        a public holiday is not a working day either (was weekends only)
# 2.4, 4.1    storage weeks            storage.py      seven-day weeks from each lot's receipt date, billed when they start
#                                                      in the period with pallets on hand (was calendar weeks from Monday)
# 3.1, 3.2    rate card in force       rates.py,       the rates of the revision in force on a storage week's first day or
#                                      storage.py,     a movement's date (was always the latest revision)
#                                      handling.py
# 4.2         storage tiers            storage.py      each billed week at the rate of the tier that takes its own number
#                                                      (was every week at the tier the lot's age at period end reaches)
# 4.3, 4.4    storage, minimum         statement.py    (no change: a lot with billed weeks pays at least the minimum)
# 4.5, 2.6    peak                     storage.py      the most pallets on hand on the first day of a billed week (was the
#                                                      most on any day of the period); a lot with no billed week has no
#                                                      figure to take the largest of, so 4.5 gives no rule (2.6) and
#                                                      today's step stays (the most on any day), on repaired on-hand counts
# 5.1         dispatch handling        handling.py     billed for every pallet dispatched (was one pallet per dispatch)
# 6.2, 1.3,   energy surcharge         statement.py    rounded to the nearest cent with a half cent going up on a storage
# 2.5, 2.6                                             charge (was truncated); a minimum fee is not a storage charge
#                                                      (2.5), so 6.2 gives no rule (2.6) for such a lot and today's step
#                                                      stays (the percentage of the billed storage, truncated)
# 6.3, 7      amount, total            statement.py    (no change)
#
# Strategy: change each figure only where the schedule gives a rule for it; where 2.6 says a clause
# gives none, keep the step the package takes today, worked on the figures the schedule does define.
# The driver tools/stockbill_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

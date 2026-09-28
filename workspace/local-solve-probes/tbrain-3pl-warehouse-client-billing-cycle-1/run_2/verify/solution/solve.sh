#!/bin/bash
# Reference repair for /app/src/stockbill, following /app/docs/billing-schedule.md (billing schedule WB-5).
#
# Clause      Topic                    File            Change
# 2.2         pallets on hand          lots.py         a pallet dispatched on a day is still on hand that day (was gone
#                                                      on its dispatch day)
# 2.3         closed and open lots     lots.py         (no change: closed when every pallet received has been dispatched)
# 2.4, 5.2    out-of-hours handling    dates.py        a public holiday is not a working day either (was weekends only)
# 3.1, 3.2    rate card in force       rates.py,       the rates of the revision in force on a storage week's first day or
#                                      storage.py,     a movement's date (was always the latest revision); on a day before
#                                      handling.py     the client's earliest effective date 3.1 gives no rule, so the
#                                                      package's own choice stays (the latest revision)
# 4.1, 4.2    storage weeks            storage.py      seven-day weeks from each lot's receipt date, billed when they start
#                                                      in the period (was calendar weeks starting on Mondays)
# 4.3         storage tiers            storage.py      each billed week at the rate of the tier that takes its own number
#                                                      (was every week at the tier the lot's age at period end reaches)
# 5.1         dispatch handling        handling.py     billed for every pallet dispatched (was one pallet per dispatch)
# 6.1         lot amounts              statement.py    (no change: storage plus handling)
# 6.2, 6.3,   discount                 statement.py    rounded to the nearest cent with a half cent going up for a closed
# 1.3                                                  lot (was truncated); an open lot's storage is an accrual, not a
#                                                      charge (6.2), so 6.3 gives no rule for its discount and today's
#                                                      step stays (the percentage of its amount, truncated), taken on
#                                                      the repaired amounts
# 6.4, 7      net, total, statement    statement.py    (no change)
#
# Strategy: change each figure only where the schedule gives a rule for it; where it gives none (3.1 and
# 6.2 name the two places), keep the step the package takes today, worked on the figures the schedule
# does define. The driver tools/stockbill_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

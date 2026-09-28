#!/bin/bash
# Reference repair for /app/src/stockbill, following /app/docs/billing-schedule.md (billing schedule WB-5).
#
# Clause      Topic                    File            Change
# 2.1, 2.2    pallets on hand          lots.py         a dispatch (an entry of one pallet or more) takes its pallets away
#                                                      from the day after its date (was from its date); the schedule says
#                                                      nothing of other entries, so they keep the package's timing (their
#                                                      own date)
# 2.3, 5.2    out-of-hours handling    dates.py        a public holiday is not a working day either (was weekends only)
# 2.4, 4.1    storage weeks            storage.py      seven-day weeks from each lot's receipt date, billed when they start
#                                                      in the period with pallets on hand (was calendar weeks from Monday)
# 3.1, 3.2    rate card in force       rates.py,       the rates of the revision in force on a storage week's first day or
#                                      storage.py,     a receipt's or entry's date (was always the latest revision)
#                                      handling.py
# 4.2         storage tiers            storage.py      each billed week at the rate of the tier that takes its own number
#                                                      (was every week at the tier the lot's age at period end reaches)
# 4.3, 4.4    storage, minimum         statement.py    (no change)
# 4.5         peak                     storage.py      the most pallets on hand on the first day of a billed week (was the
#                                                      most on any day); a lot with no billed week has nothing to take the
#                                                      largest of, so today's step stays (the most on any day, on the
#                                                      repaired on-hand counts)
# 5.1         receiving handling       handling.py     a receipt at the receiving rate (was the dispatch rate)
# 5.3         entries below one pallet handling.py     (no change: pallets times the dispatch or out-of-hours rate)
# 6.2, 1.3    energy surcharge         statement.py    rounded to the nearest cent, a half cent going up (was truncated)
# 6.3, 7      amount, total            statement.py    (no change)
#
# Strategy: change each figure only where the schedule gives a rule for it; where it gives none (entries
# of nought or below, a lot with no billed week), keep the step the package takes today, worked on the
# figures the schedule does define. The driver tools/stockbill_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

#!/bin/bash
# Reference repair for /app/src/treadcheck, following /app/docs/tread-standard.md (edition TS-6).
#
# Rule        Topic                  File           Change
# 1.1         rounding               rounding.py    nearest whole unit, an exact half to the larger number, in integers
#                                                   (was Python round(), which sends a half to the even number)
# 2.1, 3.1    reading depth          gauges.py      a measurement (the gauge showed 10 tenths or more) takes the gauge's
#                                                   offset (was the figure shown); the standard gives no depth for a
#                                                   reading on the wear bar, so it keeps the figure shown, as today
# 2.3, 4.2    tread worn             wear.py        a fresh tire is worn from its new depth over the distance from the
#                                                   odometer at mounting (was from its first reading); 4.2 speaks only
#                                                   of a fresh tire, so any other tire keeps today's first-reading basis
# 4.3         wear rate              wear.py        (no change beyond the rounding of 1.1)
# 2.4         removal depth          status.py      40 tenths at a steer position (was 32 at every position)
# 5.1         status                 status.py      pull at or below the removal depth, watch at or below it plus 16
#                                                   (were strict comparisons)
# 6.1         casing age             retread.py     days from the casing date to the report date, below 2,190 (was the
#                                                   difference of calendar years, below 6)
# 6.1         retread count          retread.py     fewer than 2 retreads (was 2 or fewer)
# 6.1         retread candidates     summary.py     only a tire that is to be pulled goes for retread (was any tire)
# 7.1         summary                summary.py     (no change: one entry per tire in job order)
#
# Strategy: change each figure only as far as a rule of the standard reaches; where no rule settles a
# figure, the step the package takes today stays, and every other step follows the standard.
# The driver tools/treadcheck_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

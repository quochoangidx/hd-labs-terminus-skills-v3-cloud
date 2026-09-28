#!/bin/bash
# Reference repair for /app/src/treadcheck, following /app/docs/tread-standard.md (edition TS-6).
#
# Rule        Topic                  File           Change
# 1.1         rounding               rounding.py    a rule's division rounds to the nearest unit, an exact half to the
#                                                   larger number (was Python round(), half to even); km_left, which no
#                                                   rule settles, keeps round() through divide_even
# 3.1         reading depth          gauges.py      the figure shown plus the gauge's offset (was the figure shown)
# 4.2         tread worn             wear.py        new depth less latest depth, over the distance from the odometer at
#                                                   mounting (was first reading to latest reading)
# 4.3         wear rate              wear.py        (no change beyond the rounding of 1.1)
# 2.2         removal depth          status.py      40 tenths at a steer position, 30 at drive and trailer (was 32 at
#                                                   every position); the regrooving check, which no rule settles, keeps
#                                                   today's floor of 32 + 20 as its own constant
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

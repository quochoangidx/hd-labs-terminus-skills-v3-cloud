#!/bin/bash
# Reference repair for /app/src/rentcharge, following /app/docs/rental-charges-manual.md (manual RC-3).
#
# Rule        Topic                 File             Change
# 2.2, 2.3    days charged          time_charge.py   a day rental: whole days of 1,440 minutes, one more only when more
#                                                    than 59 minutes are left over (was: every day begun); a rental under
#                                                    a day has no rule, so today's step stays (every day begun: one day)
# 3.2         mileage allowance     mileage.py       150 miles for each day charged (was 100)
# 2.4         miles driven          mileage.py       1,000,000 added when the odometer came back reading less (turnover)
# 2.5, 3.3    fuel charge           fuel.py          a refuelling rental: fuel rate per eighth short plus a 1,500-cent fee;
#                                                    a car back as full or fuller has no rule, so today's step stays
#                                                    (fuel rate times eighths out less eighths in: nought or a credit)
# 4.1         tax base              run.py           time and mileage charges only (was: fuel taxed too)
# 1.2         tax rounding          tax.py           nearest cent, an exact half cent going up (was: rounded down)
# 4.2, 4.3    total, file sums      run.py           (no change)
#
# Strategy: change each figure only where the manual gives a rule for it, and keep today's step where it gives
# none, fed by the figures the manual defines. The driver tools/rentcharge_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

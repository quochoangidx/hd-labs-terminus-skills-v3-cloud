#!/bin/bash
# Reference repair for /app/src/finebook, following /app/docs/overdue-fines-policy.md (policy LF-5).
#
# Rule   Topic        File        Change
# 2.1    due day      dates.py    a book 21 days after borrowing, a DVD 7 (was: 14 for every kind); a journal has
#                                 no loan period in the policy, so today's step stays (14)
# 2.2    late days    dates.py    a late loan counts the days after its due day up to its return day that are not
#                                 Sundays (was: every day); a loan that is not late has no late days in the
#                                 policy, so today's step stays (return day less due day)
# 3.1    fine         fines.py    a late loan's fine is capped at its replacement cost (was: no cap); a loan that
#                                 is not late has no fine in the policy, so today's step stays (its late days at
#                                 the daily fine)
# 3.2                             (no change)
#
# Strategy: change each figure only where the policy gives one, and keep today's step where it gives none, fed by
# the figures the policy defines. The driver tools/finebook_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

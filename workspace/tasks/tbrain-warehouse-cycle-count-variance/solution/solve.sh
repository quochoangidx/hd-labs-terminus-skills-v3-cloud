#!/bin/bash
# Reference repair for /app/src/cyclecount, following /app/docs/cycle-count-procedure.md (procedure CC-2).
#
# Rule        Topic               File           Change
# 2.1, 2.2    final count         variance.py    the recount when one was taken (was: the count, always)
# 2.3         graded tolerance    tolerance.py   A nought, B 2 per cent, C 5 per cent of the system quantity, a fraction
#                                                dropped (was: 5 per cent for every class, rounded); a class other than
#                                                A, B or C has no rule, so today's step stays (5 per cent, Python round)
# 3.1         status              report.py      outside tolerance with no recount is "recount" (was: always "adjust")
# 3.3         booked units        report.py      an adjusted line books its variance (was: count less system); a line
#                                                that is not adjusted has no rule, so today's step stays (count less
#                                                system, whatever the recount)
# 3.4         shrink              report.py      adjusted shortages only; a surplus does not reduce it (was: net of all
#                                                adjusted values)
# 3.2         value               report.py      (no change)
#
# Strategy: change each figure only where the procedure gives a rule for it, and keep today's step where it gives
# none, fed by the figures the procedure defines. The driver tools/cyclecount_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

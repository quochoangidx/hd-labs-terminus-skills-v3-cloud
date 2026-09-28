#!/bin/bash
# Reference repair for /app/src/cemsqr, following /app/docs/data-reduction-procedure.md (procedure DRP-4).
#
# Rule        Topic                    File            Change
# 2.1         operating quarter/hour   hours.py        (no change: a record of 1 MW or more; an hour holding one)
# 2.2, 3.1    hourly averages          hours.py        averages over the valid readings (OK records of operating
#                                                      quarters) only (was every record of the hour)
# 2.3         valid hour               hours.py        a valid reading for each operating quarter, or two or more
#                                                      in an hour holding a CAL record (was four OK records)
# 2.4, 3.2    corrected concentration  correction.py   a firing hour (oxygen average below 190) uses 209 (was 210);
#                                                      the procedure gives no correction for a valid hour that is
#                                                      not a firing hour, so it keeps today's expression (oxygen
#                                                      held at 190, 210), fed with the procedure's averages
# 3.3         mass rate                report.py       from the measured NOx average (was the corrected
#                                                      concentration); correction.mass_rate unchanged
# 2.5, 4.2,   lost hours               substitute.py   a lost hour (no valid reading) takes the average of the last
# 4.3                                                  valid hour before and the first after, one side alone, or
#                                                      nought (was the last valid hour's figures); an operating
#                                                      hour that is neither valid nor lost is not a lost hour and
#                                                      keeps today's step (the last valid hour's figures)
# 4.1         substitute kind          report.py       (no change: every operating hour that is not valid)
# 5.1         quarter mass             report.py       mass rate times the operating time (was a whole hour each)
# 2.6, 6.1    rolling average          rolling.py      the operating day and the 29 operating days before it (was
#                                                      30 calendar days), averaging the valid hours' concentrations
#                                                      (was the daily means of every operating hour)
# 6.2         exceedance day           rolling.py      above the limit (was at or above)
# 1.1         rounding                 rounding.py     (no change: exact arithmetic, nearest unit, half up)
# 7.1         report                   report.py       (no change)
#
# Strategy: change each figure only where the procedure gives a rule for it; where it gives none, the step the
# package takes today stays, worked from the procedure's own inputs, and every other step follows the procedure.
# The driver tools/cemsqr_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

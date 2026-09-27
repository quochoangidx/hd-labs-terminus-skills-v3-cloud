#!/bin/bash
# Reference repair for /app/src/noisedose, following /app/docs/noise-survey-manual.md (manual HC-4).
#
# Rule        Topic                 File          Change
# 2.3         counted reading       levels.py     a reading exactly at the 80.0 dBA threshold counts (was "above" only)
# 3.1         reference duration    levels.py     programme criterion 85 dBA and exchange rate 3 dB (were 90 and 5)
# 2.2, 2.4    sampled time          levels.py,    sampled time is the length of every reading (a run at 40.0 dBA or
#                                   runs.py       more), below-threshold readings included; a run logged at 0.0 is not
#                                                 a reading and stays out, as it did before
# 2.5, 3.3    shift dose            shift.py      a full-shift survey (sampled time at least three quarters of the
#                                                 shift) is projected to the worker's own shift when it sampled less
#                                                 than the shift (was 480 minutes) and keeps its measured dose
#                                                 otherwise; for any other survey the manual gives no rule, so today's
#                                                 step stays (nought with nothing sampled, else scaled to 480 minutes)
# 4.1         TWA                   twa.py        85 + 3 log2(D/100) (was 90 + 16.61 log10(D/100))
# 1.2         reported TWA          twa.py        rounded to the nearest tenth (was truncated)
# 5.1         ceiling flag          flags.py      (no change: a reading above 115.0 dBA)
# 5.2, 2.6    impulse flag          flags.py      a peak of 140.0 dBC counts (was "above" only)
# 5.3         status                twa.py        "action" from 82.0 dB, "over" above 85.0 dB (were 85 and 90 or more);
#                                   report.py     (no change: a flagged worker is "over" whatever the TWA)
# 6.1, 1.3    group dose            groups.py     mean of every member's shift dose, a quiet member's nought included;
#                                                 the group's TWA follows from that dose and its status from the TWA
#                                                 alone (was a mean of member TWAs over members that had one)
#
# Strategy: change each figure only where the manual gives a rule for it, and keep today's step where it
# gives none; every other step such a figure passes through still follows the manual. The driver
# tools/noisedose_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

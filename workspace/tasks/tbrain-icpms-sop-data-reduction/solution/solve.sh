#!/bin/bash
# Reference repair for /app/src/metalquant, following /app/docs/reduction-sop.md (SOP TM-07).
#
# SOP section               File        Change
# 2   calibration line      calib.py    least-squares line with its intercept fitted (was forced through the origin)
# 4   blank level           blanks.py   mean of the blank readings at or above the mdl, from every blank in the batch;
#                                       with no such result the SOP gives no mean, so today's first-blank reading
#                                       (or 0.0 with no blank) stays
# 5   amount                samples.py  (reading - blank level) * dilution (was reading * dilution - blank level)
# 5   flags                 samples.py  judged on the corrected reading, not the amount; J only below the loq
# 6   CCV pass              qc.py       recovery rounded to one decimal, 90.0 to 110.0 inclusive
# 6   bracketing            qc.py       with a CCV on both sides, both nearest CCVs must have passed; a run without
#                                       one on each side keeps today's check (nearest CCV before, else true)
# 7   spike recovery        qc.py       (spike amount - parent amount) / added * 100 when spike and parent are both
#                                       results; otherwise the SOP gives no rule and today's calculation
#                                       (divided by added * dilution) stays
# 3/7 results               report.py   passes the mdl to the blank level and whether spike and parent are results
#
# Strategy: fix each departure where the SOP speaks and keep today's calculation wherever it gives no rule.
# The driver tools/metalquant_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

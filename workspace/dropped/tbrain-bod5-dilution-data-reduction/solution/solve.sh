#!/bin/bash
# Reference repair for /app/src/bodcalc, following /app/docs/sop-wq14-bod5.md (SOP WQ-14).
#
# Rule        Topic                 File          Change
# 2.4         usable bottle         bottles.py    a usable bottle has depleted 2.50 mg/L or more (was 2.0)
# 2.3         spent bottle          bottles.py    a bottle is spent below a final DO of 1.20 mg/L (was 1.0)
# 2.5, 3.1,   seed factor           seed.py       mean seed rate of the reference controls: the usable seed controls,
# 3.2                                             or every control when none is usable (was total depletion over total
#                                                 seed of every control)
# 3.3, 4.1    bottle BOD            bottles.py    the seed correction comes off the depletion before dividing by the
#                                                 sample fraction (was taken off after)
# 5.1, 5.2    sample result         samples.py    (no change: mean of usable bottles; ">" from the bottle holding least)
# 5.3, 5.4    less-than result      samples.py    from the bottle holding the most sample, first listed on a tie (was
#                                                 the least)
# 6.1, 6.2    duplicate RPD         qc.py         |a - b| over the mean of the two measured BODs (was over the value of
#                                                 the sample duplicated); where either side has no measured BOD the SOP
#                                                 defines no RPD, so today's calculation stays, on the section 5 values
# 7.1         blank depletion       qc.py         the largest blank depletion (was the mean)
# 7.2         check value           qc.py         (no change: G is tested on the unrounded check value)
# 1.2         reported values       report.py     three significant figures (was one decimal place)
#
# Strategy: change each figure only where the SOP gives a rule for it, and keep today's calculation for a figure the
# SOP leaves undefined for a batch; every later step that uses such a figure still follows the SOP. The driver
# tools/bodcalc_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

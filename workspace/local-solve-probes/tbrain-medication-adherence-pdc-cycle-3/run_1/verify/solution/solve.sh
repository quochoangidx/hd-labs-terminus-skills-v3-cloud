#!/bin/bash
# Reference repair for /app/src/pdcmeasure, following /app/docs/adherence-measure-spec.md (specification AM-2).
#
# Rule        Topic                  File          Change
# 3.1, 3.2    start day              coverage.py   a fill starts on its fill date (was the day after)
# 3.2         carry-over             coverage.py   a fill whose date an earlier fill of the same drug covers starts the
#                                                  day after the last day those fills cover; fills of one date in file
#                                                  order; other drugs never move it (was: no fill ever moved)
# 2.2, 3.1    days a fill covers     coverage.py   (no change: a fill within the limit covers its days supply; the
#                                                  specification gives no length for a fill above the limit, so today's
#                                                  step stays, covering the supply limit of 100 days)
# 2.4         in the measure         measure.py    fills on two or more different fill dates and an index date no later
#                                                  than 2 October (was: any two fills, any index date)
# 2.5         treatment period       measure.py    a member in the measure is measured from the index date to 31 December
#                                                  (was: to the last covered day); for a member outside the measure the
#                                                  specification gives no period, so today's span stays
# 2.6, 4.1    period days            pdc.py        stay days leave the period days of a member in the measure as well as
#                                                  the covered days (were left in the period days)
# 1.2         reported percentages   rounding.py   nearest tenth, an exact half going up (was: rounded down)
# 4.2         adherent               pdc.py        in the measure and a reported PDC of 80.0 or more (was: above 80.0,
#                                                  whether in the measure or not)
# 2.7, 5.1    class rate             classes.py    a reportable class divides by its rate base, the members in the measure
#                                                  (was: every member with a fill); a class that is not reportable has no
#                                                  rate base in the specification, so today's divisor stays
#
# Strategy: change each figure only where the specification gives a rule for it, and keep today's step where it
# gives none, fed by the figures the specification defines; every other step such a figure passes through still
# follows the specification. The driver tools/pdc_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

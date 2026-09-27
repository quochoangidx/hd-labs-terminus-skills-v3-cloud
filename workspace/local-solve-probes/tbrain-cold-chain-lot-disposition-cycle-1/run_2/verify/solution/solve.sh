#!/bin/bash
# Reference repair for /app/src/coldchain, following /app/docs/qa-sop-lot-disposition.md (QA-SOP-311).
#
# Rule        Topic                    File              Change
# 1.2         reported hours           report.py         rounded to the nearest hundredth of an hour (was truncated)
# 2.1, 2.5    band ends                bands.py          the labelled range includes its upper limit; a band above the range
#                                                          holds temperatures above its lower end (was: from it); bands below
#                                                          the range unchanged
# 2.7         hold                     attribution.py    the last reading of an export holds nought (was the 60-minute hold cap);
#                                                          a reading opening a logged interval holds its length (no change);
#                                                          the SOP gives a reading that opens a logger gap no hold, so today's
#                                                          step stays: min(span, HOLD_CAP_MINUTES), the cap left at 60
# 2.4, 3.2    unlogged time            attribution.py    a logger gap is a spacing longer than 30 minutes (GAP_MINUTES was 60)
# 2.9, 4.1    carry across legs        disposition.py    a chained lot's band time is the total over its legs (was the worst
#                                                          leg); the SOP gives no band time for a lot that is not chained, so
#                                                          today's step stays there (the worst leg)
# 2.10, 4.2   prior time               disposition.py    the release certificate's prior minutes are charged against the band
# 5.1         mean kinetic temperature kinetics.py,      each reading weighted by its hold, each export on its own (no interval
#                                      disposition.py    across a handover) (was unweighted)
# 6.1         reject                   disposition.py    (no change: a frozen reading, or a remaining allowance below nought)
# 6.2, 1.2    quarantine               disposition.py    the unrounded MKT is compared with the upper limit (was the rounded one)
#
# Strategy: change each figure only where the SOP gives it a value, and keep today's step where the SOP
# names a figure but gives it none; every other step such a figure passes through still follows the
# SOP. The driver tools/coldchain_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

#!/bin/bash
# Reference repair for /app/src/coldchain, following /app/docs/qa-sop-lot-disposition.md (QA-SOP-311).
#
# Rule        Topic                    File              Change
# 1.2         reported hours           report.py         rounded to the nearest hundredth of an hour (was truncated)
# 2.1, 2.5    band ends                bands.py          the labelled range includes its upper limit; a band above the range
#                                                          holds temperatures above its lower end (was: from it); bands below
#                                                          the range unchanged
# 2.3, 2.7    last reading             attribution.py    the last reading of an export stands for nothing after it (was 60 min),
#                                                          for both its hold and its MKT weight
# 2.4, 2.7    hold of a gap opener     attribution.py,   band time charges a reading its hold: the logged interval it opens, and
#             3.1                      disposition.py    nothing for a reading that opens a logger gap (was the whole spacing);
#                                                          done on the band path only (logged_holds), because holds() is also
#                                                          the MKT weight
# 5.1         MKT weight               disposition.py    (no change: each reading weighs the minutes to the next reading of its
#                                                          export, logger gaps included, export by export)
# 2.4, 3.2    unlogged time            attribution.py    a logger gap is a spacing longer than 30 minutes (was 60)
# 4.1         carry across legs        disposition.py    a lot's band time is the total over its legs (was the worst leg)
# 2.6, 2.9    prior time               disposition.py    the certificate's excursion entries (15 minutes or more) are charged
#             4.2                                        against the band (was ignored); shorter entries are transients
# 6.1         reject                   disposition.py    (no change: a frozen reading, or a remaining allowance below nought)
# 6.2, 1.2    quarantine               disposition.py    the unrounded MKT is compared with the upper limit (was the rounded one)
#
# Strategy: each figure follows the SOP term that defines it. Band time and MKT read the same logger
# spacings through different terms (hold, weight), so the band rule is applied on the band path and
# the shared holds() keeps giving the MKT weight. The driver tools/coldchain_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

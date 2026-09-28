#!/bin/bash
# Reference repair of /app/src/sealsrc against /app/docs/source-inventory-manual.md (manual RPO-7).
#
# Rule  Topic                    File          Change
# 1.2   day count                dates.py      actual Gregorian days (was thirty-day months); the manual gives no
#                                              elapsed time for a certificate dated after the survey, so today's
#                                              stop at nought stays and that entry keeps its certificate figure
# 1.4   half-life in days        nuclides.py   a year of half-life is 365.25 days (was 365)
# 3.1   current activity         decay.py      A_ref * 2^(-t/T) (was exp(-t/T), the half-life used as a mean life)
# 3.2   daughter activity        decay.py      parent current activity times the branching fraction (was 1.0)
# 3.3/4 exemption                checks.py     total activity (parent plus daughter) at or below the exempt quantity
# 5.1   leak-testable            checks.py     current activity (was the certificate figure) against the class
#                                              threshold, 3.7e6 Bq beta-gamma or 3.7e5 Bq alpha
# 1.7/5.2 last leak test         checks.py     the latest-dated wipe that is a leak test (removable activity below
#                                              185 Bq); was the last wipe listed, whatever it read
# 7.1   decay-to-disposal        checks.py     short-lived and elapsed time at least ten half-lives (was activity at
#                                              or below a thousandth of the certificate figure)
# 6.1   held activity and count  locations.py  sums current activities (was the certificate figures) of the
#                                report.py     licensed material at the location; the licensing test stays on the
#                                              certificate figure (1.8, licensing follows the certificate), and
#                                              daughters stay out of the held activity
# 6.2   fraction and over limit  locations.py  (no change) held / limit, over when held is more than the limit
#
# Strategy: fix each departure where the manual decides and keep the package's present step wherever it gives
# no rule. The driver tools/sealsrc_run.py and the report layout are not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

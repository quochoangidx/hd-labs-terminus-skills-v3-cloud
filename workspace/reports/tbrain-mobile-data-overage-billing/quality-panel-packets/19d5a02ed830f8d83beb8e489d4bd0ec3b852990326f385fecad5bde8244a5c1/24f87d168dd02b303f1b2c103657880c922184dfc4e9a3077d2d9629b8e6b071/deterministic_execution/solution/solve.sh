#!/bin/bash
# Reference repair for /app/src/usagebill, following /app/docs/data-usage-tariff.md (tariff MD-2).
#
# Rule   Topic        File         Change
# 2.1    usage        usage.py     each session in whole megabytes, a part megabyte counting as a whole one
#                                  (was: the cycle's kilobytes added up, the part megabyte dropped)
# 2.2    allowance    usage.py     BASIC 2,048 MB, PLUS 10,240 MB (was: 5,120 MB for every plan); a FLEX line
#                                  has no allowance in the tariff, so today's step stays (5,120 MB)
# 3.1    charge       charges.py   a line over its allowance pays its rate for the first 1,024 MB of overage and
#                                  1 cent a megabyte after (was: the rate for every megabyte); a line not over
#                                  its allowance has no overage or charge in the tariff, so today's step stays
#                                  (usage less allowance, that many megabytes at the rate)
# 2.3, 3.2                     (no change)
#
# Strategy: change each figure only where the tariff gives one, and keep today's step where it gives none, fed by
# the figures the tariff defines. The driver tools/usagebill_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

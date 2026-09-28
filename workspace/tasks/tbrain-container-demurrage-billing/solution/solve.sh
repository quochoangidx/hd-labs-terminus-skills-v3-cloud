#!/bin/bash
# Reference repair for /app/src/demurrage, following /app/docs/demurrage-tariff.md (tariff DM-3).
#
# Rule   Topic               File         Change
# 2.1    dwell               dwell.py     the discharge day and the pickup day both counted (was: one day short)
# 2.2    free days           dwell.py     dry 5, reefer 3 (was: 5 for every type); a tank has no free days in the
#                                         tariff, so today's step stays (5)
# 3.1    demurrage charge    charges.py   a container on demurrage pays the rate for its first 4 days and twice
#                                         the rate after (was: the rate for every day); a container not on
#                                         demurrage has no days or charge in the tariff, so today's step stays
#                                         (dwell less free days, that many days at the rate)
# 2.3, 3.2                   (no change)
#
# Strategy: change each figure only where the tariff gives one, and keep today's step where it gives none, fed by
# the figures the tariff defines. The driver tools/demurrage_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

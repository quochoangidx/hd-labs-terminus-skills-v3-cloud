#!/bin/bash
# Reference repair for /app/src/folio, following /app/docs/folio-charges-rules.md (rules FC-3).
#
# Rule   Topic            File         Change
# 2.1    room charge      charges.py   every seventh night of a stay free (was: every night charged)
# 2.2    city tax         charges.py   a room at 5,000 cents a night or more: 250 cents a night for at most 14
#                                      nights (was: 200 a night, every night); a cheaper room has no city tax in
#                                      the rules, so today's step stays (nothing under 3,000, else 200 a night)
# 2.3    occupancy tax    charges.py   13.5 per cent, an exact half cent going up (was: 12 per cent, Python's round)
# 2.4    service fee      (no change)  the rules give no rate or rounding, so today's step stays: 3.5 per cent with
#                                      Python's round (a half cent to the even cent), on the rule 2.1 room charge;
#                                      money.to_cents() is therefore left as it is
# 2.5                     (no change)
#
# Strategy: change each figure only where the rules give one, and keep today's step where they give none, fed by
# the figures the rules define. The driver tools/folio_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

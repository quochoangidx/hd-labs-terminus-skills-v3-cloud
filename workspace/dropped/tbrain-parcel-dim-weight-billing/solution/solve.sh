#!/bin/bash
# Reference repair for /app/src/parcelbill, following /app/docs/parcel-billing-rules.md (rules PB-4).
#
# Rule   Topic                  File         Change
# 2.2    dimensional divisor    weight.py    139 for a box (was: 166 for every parcel); a parcel that is not a box
#                                            has no divisor in the rules, so today's step stays (166)
# 2.3    billable weight        weight.py    rounded up to the next whole pound (was: Python round)
# 3.2    residential surcharge  charges.py   530 for a ground parcel going to a home (was: 450); an express parcel
#                                            going to a home has no amount in the rules, so today's step stays (450)
# 3.3    fuel surcharge         charges.py   a ground parcel: 14.25 per cent of transport and residential
#                                            together, an exact half cent going up (was: of transport alone, the
#                                            fraction dropped); an express parcel has no rule, so today's step
#                                            stays (transport alone, the fraction dropped)
# 3.1, 3.4                      (no change)
#
# Strategy: change each figure only where the rules give one, and keep today's step where they give none, fed by
# the figures the rules define. The driver tools/parcelbill_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

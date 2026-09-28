#!/bin/bash
# Reference repair for /app/src/parkfee, following /app/docs/garage-tariff.md (tariff GT-2).
#
# Rule   Topic           File      Change
# 2.2    grace period    fees.py   a car or van staying 15 minutes or less has a parking fee of nothing (was:
#                                  charged hours); a motorcycle has no grace period in the tariff, so today's
#                                  step stays (charged hours at 150)
# 3.1    hourly rates    fees.py   a van pays 450 cents an hour (was: 300)
# 3.3    maximum         fees.py   a car's or van's fee is never more than 2,400 cents for each 24 hours begun
#                                  (was: no maximum); a motorcycle has no maximum in the tariff, so today's step
#                                  stays (charged hours at 150)
# (none) amount due      fees.py   the tariff gives no rule for it, so today's step stays: a validated ticket's
#                                  amount due is its fee less 200 cents, below nought where the fee is under 200
# 2.1                              (no change)
#
# Strategy: change each figure only where the tariff gives one, and keep today's step where it gives none, fed by
# the figures the tariff defines. The driver tools/parkfee_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

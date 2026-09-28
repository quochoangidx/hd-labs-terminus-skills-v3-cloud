#!/bin/bash
# Reference repair for /app/src/netbill, following /app/docs/net-metering-tariff.md (tariff NM-4).
#
# Rule   Topic            File         Change
# 2.2    energy charge    charges.py   a HOME net consumer pays 28 cents for its first 300 kWh and 34 after (was:
#                                      28 for every kWh); a meter that is not a net consumer has no energy charge
#                                      in the tariff, so today's step stays (its net at the tariff's rate)
# 3.1    service charge   charges.py   HOME 950 and SHOP 1,450 from 200 kWh imported (was: 950 from 50 kWh); a FARM
#                                      meter, or one that imported under 200 kWh, has no service charge in the
#                                      tariff, so today's step stays (nothing under 50 kWh imported, else 950)
# 2.1, 3.2                             (no change)
#
# Strategy: change each figure only where the tariff gives one, and keep today's step where it gives none, fed by
# the figures the tariff defines. The driver tools/netbill_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

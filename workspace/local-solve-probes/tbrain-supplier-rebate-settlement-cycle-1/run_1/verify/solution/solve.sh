#!/bin/bash
# Reference repair of /app/src/rebate against Schedule R (edition R-4).
#
# | Rule          | File                  | Change                                                                 |
# |---------------|-----------------------|------------------------------------------------------------------------|
# | 2.2, 3.1, 3.2 | rebate/ledger.py      | a carton shipment (12 units or more) counts from the fourth day after its invoice; other lines keep the date the export gives them |
# | 3.3           | rebate/returns.py     | returns carry a handling charge of 40 cents a unit (own constant; HANDLING_PER_UNIT stays 25 for chargeback.py) |
# | 2.6, 3.5      | rebate/tiers.py       | a tier is reached at or above its threshold                            |
# | 3.4, 3.5      | rebate/statement.py   | the tier is picked on net purchases, not purchases                     |
# | 1.1, 3.6      | rebate/tiers.py       | the volume rebate is rounded to the cent, half up, instead of truncated |
# | 4.1           | rebate/growth.py      | the growth bonus is taken on the increase over last year, not on all net purchases |
# | 6.2           | rebate/settle.py      | the minimum settlement is 25,000 cents (own constant; MINIMUM_CREDIT stays 5,000 for protection.py) |
# | 5.1, 5.2      | protection.py, chargeback.py | (no change)                                                     |
# | 1.2           | rebate/dates.py       | (no change)                                                            |
#
# Strategy: each rule is applied to the inputs its defined terms reach. A purchase line of
# fewer than 12 units, a price notice that is not a price drop and a sale below cost that is
# not a contract sale are reached by no rule, so they keep the step today's code takes,
# with the package's own constants at today's values.
set -euo pipefail
cd /app
patch -p1 < /solution/fix.patch

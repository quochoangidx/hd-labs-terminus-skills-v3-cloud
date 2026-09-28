#!/bin/bash
# Reference repair of /app/src/commission against the Field Sales Compensation Plan (issue 6).
#
# | Rule          | File                       | Change                                                                  |
# |---------------|----------------------------|-------------------------------------------------------------------------|
# | 2.2, 3.2      | commission/bookings.py     | bookings add the rep's split share of each order, not the whole value    |
# | 4.1           | commission/commission.py   | three marginal bands: up to quota, quota to twice quota, above that      |
# | 1.1, 4.2      | commission/commission.py   | each band's commission rounded to the cent, half up, instead of truncated |
# | 2.3, 2.5, 5.1 | commission/clawback.py, figures.py | a reversal (50,000 cents or more) is clawed back up to an age of 120 days through a new reversal_days figure; window_days stays 90 for other credit notes |
# | 2.4, 6.1      | commission/bonus.py        | a new-logo order (a first order of 250,000 cents or more) earns its bonus whatever the rep's share; other first orders keep today's floor |
# | 7.3           | commission/payout.py       | the owed balance is recovered only from the part of the total above the draw |
# | 7.4           | commission/figures.py      | the minimum payment reads a new payment_cents figure of 25,000; small_cents stays 10,000 for the bonus floor |
# | 5.2, 6.2, 7.1, 7.2 | clawback.py, bonus.py, statement.py, payout.py | (no change)                                       |
# | 1.2, 3.1      | commission/dates.py        | (no change)                                                             |
#
# Strategy: each rule is applied to the inputs its defined terms reach. A credit note that is
# not a reversal and a first order that is not a new-logo order are priced by no rule, so they
# keep the step today's code takes for them, with the package's own figures at today's values.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

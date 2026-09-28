#!/bin/bash
# Reference repair for /app/src/costshare, following /app/docs/cost-sharing.md.
#
# Note section            File            Change
# 1.3 half to even        money.py        share(): nearest cent, halves to even, for a rate from 0 to 10000;
#                                         any other rate keeps today's half-up expression (the note is silent)
# 2.2 other kinds         adjudicator.py  unchanged: any kind but preventive/office still takes the facility path
# 3   preventive          adjudicator.py  preventive lines return all-zero parts and record nothing
# 4.1 office copay        adjudicator.py  copay part is the allowed amount when 0 < allowed < copay; otherwise
#                                         the copay, including for allowed amounts of zero or less
# 4.2 office lines        adjudicator.py  no coinsurance on office lines
# 5.2 what is left        adjudicator.py  deductible_left() takes the family remainder when the family deductible
#                                         is above zero; no clamp (a negative remainder stands)
# 5.3 coinsurance base    adjudicator.py  coinsurance on allowed minus the pre-cut deductible part
# 6.1 rooms               adjudicator.py  one room per maximum above zero, member and family independently
# 6.2 cut order           adjudicator.py  excess off coinsurance, then copay, then deductible; parts at or below
#                                         zero give nothing
# 7.1 deductible totals   adjudicator.py  the post-cut deductible part is what gets recorded
# 7.2 out-of-pocket       ledger.py       family total takes the whole cost share when the family maximum is above
#                                         zero; without one it keeps today's deductible + coinsurance sum
#
# Strategy: fix each departure where the note speaks, and leave every expression the note does not reach as it
# ships. The patch below holds one hunk per file; see the table for which lines answer which section.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

#!/bin/bash
# Reference repair for /app/src/cellbank, following /app/docs/cell-bank-sop.md (SOP CB-3).
#
# Rule  File        Change
# 2.3   growth.py   a viable count is cells x viability / 100, only for a valid count (70.0 or more)
# 2.4   growth.py   the seed is counted at the viability of its source suspension (the source
#       lineage.py  culture's harvest or the thaw), passed in from the lineage walk
# 3.1   growth.py   doublings = log2(viable harvest / viable seed) (was total harvested / seeded);
#                   where either count is not valid, 3.1 has no rule, so today's total-count
#                   log2(harvested / seeded) stays
# 3.2   growth.py   (no change) doublings below nought are kept as they are
# 4.1   lineage.py  passage and PDL come from the culture's own source suspension, not from a
# 4.3               running figure per line in log order
# 4.2   lineage.py  a thawed bank vial takes the passage and PDL of the harvest it was frozen
#                   from (was the line's seed); no thaw adds a passage (was + 1); a supplier
#                   vial takes seed_passage and seed_pdl
# 5.1   lineage.py  age = highest PDL along the lineage; a thawed vial carries its harvest's age
# 5.2   lineage.py  flags judged on age: LIMIT above max_pdl, NEAR above max_pdl - 3 (was PDL,
#                   at or above, with a 5-doubling band)
# 6.1   banks.py    vials left = vials frozen less vials thawed from each freeze (was frozen only)
# 6.2   banks.py    bank PDL = highest PDL of the freezes with vials still in stock (was the latest
#                   freeze) for a bank in use; a bank not in use has no rule and the latest
#                   freeze's PDL stays
# 7     report.py   (no change)
#
# Strategy: repair each rule where the SOP sets a value, and keep today's calculation for a
# figure the SOP has no rule for. The driver tools/cellbank_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

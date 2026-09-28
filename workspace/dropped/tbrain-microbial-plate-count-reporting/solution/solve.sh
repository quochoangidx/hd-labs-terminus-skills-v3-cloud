#!/bin/bash
# Reference repair for /app/src/platecount, following /app/docs/apc-sop.md (SOP MIC-14).
#
# Rule       Topic                   File          Change
# 2.4, 2.5   countable range         plates.py     countable from 20 to 300 colonies, crowded above 300 (were 25 and 250)
# 2.5        too numerous to count   plates.py     a plate marked too numerous to count is crowded (was taken as no colonies)
# 2.2        plated amount           plates.py     volume plated times the dilution (was the dilution alone, as if 1.0 mL)
# 2.8        counted plates          plates.py     in_count: every plate that is not crowded, sparse and empty plates included
#                                                  (was 250 or fewer colonies, a too-numerous mark counted as none)
# 2.7, 4.1   count                   results.py    colonies on the counted plates of the counted dilutions over the sum of their
#                                                  plated amounts: the first dilution with a countable plate, and the dilution
#                                                  one step on (a tenth of it) when it was plated and holds one (was the first
#                                                  such dilution alone)
# 4.4        greater-than result     results.py    any sample with a crowded plate and no countable plate: 300 over the plated
#                                                  amount of a plate of the last dilution holding a crowded plate (was only a
#                                                  wholly crowded sample, at its first dilution)
# 2.6, 4.2   estimated count         results.py    a sparse sample (neither a countable nor a crowded plate) is estimated from
#                                                  the plates of its first dilution holding a colony (was every uncrowded plate
#                                                  of every dilution pooled)
# 4.3        less-than result        results.py    a sparse sample with no colony: one over the plated amount of a plate of its
#                                                  first dilution (was its last dilution)
# 1.2        reported result         report.py     two significant figures with an exact half going up (was half to even)
# 1.2, 5.1   written form, kinds     report.py     (no change: d.dEk with its < or > sign, kinds count/estimate/below/above)
# 1.1        unit                    report.py     (no change: CFU/g or CFU/mL)
#
# Strategy: change each figure only where the SOP gives a rule for it, and follow each defined term to
# its edge: a count takes every counted plate (2.8), not only the countable ones, and pools only the
# dilution a tenth of the first counted one (2.7). The driver tools/platecount_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

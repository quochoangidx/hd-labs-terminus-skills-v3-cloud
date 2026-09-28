#!/bin/bash
# Reference repair of /app/src/qpcrrel against SOP QP-7 (/app/docs/relative-expression-sop.md).
#
# Rule | File                      | Change
# -----|---------------------------|-------------------------------------------------------------
# 1.1  | plate.py                  | (no change) Cts read as floats, Undetermined as None
# 1.2  | (all)                     | (no change) nothing is rounded
# 2.2  | replicates.py reportable  | a reportable replicate runs from 10.00 up to and including 35.00
# 2.3  | replicates.py detected    | (no change) not detected = no reportable replicate
# 2.4  | curve.py curve_points     | Undetermined standards play no part; a level needs two determined wells
# 2.5  | curve.py amplification_.. | a standard curve needs three or more curve points
# 2.6  | ntc.py contaminated       | only an NTC Ct at or below the 35.00 cut-off contaminates
# 3.1  | curve.py amplification_.. | a standard curve's factor 10^(-1/s) is not capped at 2
# 4.1  | replicates.py kept        | every replicate more than 0.50 from the median is an outlier
# 4.2  | replicates.py kept        | mean of the replicates that are not outliers
# 4.3  | replicates.py mean_ct     | no mean Ct (None) when not detected; nothing substituted
# 5.1  | expression.py fold_change | each gene raised to its own amplification factor
# 5.2  | expression.py fold_change | normalisation factor = geometric mean of reference quantities
# 5.3  | expression.py fold_change | (no change) target quantity over the normalisation factor
# 5.4  | expression.py result      | any flag leaves the result without a fold change
# 6.x  | report.py, expression.py  | (no change) entry order, result order, flag order
#
# Strategy: change only what the SOP governs. Where the SOP gives no rule for a
# value, the step the code takes today stays, fed with the values the SOP does
# define: a gene with fewer than three curve points has no standard curve, so its
# factor is still today's (2.0 below two points, the two-point line capped at 2.0);
# and when every reportable replicate of a sample is an outlier, 4.2 has no mean,
# so the replicates are all kept, as today. Everything downstream follows the SOP.
set -euo pipefail
cd /app
patch -p1 --no-backup-if-mismatch < "$(dirname "$0")/fix.patch"

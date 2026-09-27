#!/bin/bash
# Reference repair of /app/src/qpcrrel against SOP QP-7 (/app/docs/relative-expression-sop.md).
#
# Rule | File                      | Change
# -----|---------------------------|-------------------------------------------------------------
# 1.1  | plate.py                  | (no change) Cts read as floats, Undetermined as None
# 1.2  | (all)                     | (no change) nothing is rounded
# 2.2  | replicates.py reportable  | new: a reportable replicate is a called Ct from 10.00 up to 35.00;
#      |                           | the floor stays out of plate.called, which the NTC test shares
# 2.3  | replicates.py detected    | not detected = no reportable replicate
# 2.4  | curve.py curve_points     | Undetermined standards play no part; a level needs two determined
#      |                           | wells; its Ct stays the plain mean of all of them (mean_ct unchanged)
# 2.5  | curve.py amplification_.. | (no change) a line through two or more curve points
# 2.6  | ntc.py, plate.called      | (no change) an NTC Ct at or below 35.00 contaminates, early ones too
# 3.1  | curve.py amplification_.. | the factor 10^(-1/s) is not capped at 2; 2 below two curve points
# 4.1  | replicates.py without_o.. | new: replicates more than 0.50 from the lower median are outliers
# 4.2  | replicates.py sample_ct   | mean of the reportable replicates that are not outliers
# 4.3  | replicates.py sample_ct   | no mean Ct (None) when not detected; nothing substituted
# 5.1  | expression.py fold_change | each gene raised to its own amplification factor
# 5.2  | expression.py fold_change | normalisation factor = geometric mean of reference quantities
# 5.3  | expression.py fold_change | (no change) target quantity over the normalisation factor
# 5.4  | expression.py result      | any flag leaves the result without a fold change
# 6.x  | report.py, expression.py  | (no change) entry order, result order, flag order
#
# Strategy: change only what the SOP governs, rule by rule. The replicate rules
# (2.2 window, 4.1 outliers) belong to a sample's replicates only: the curve-point
# mean (2.4) and the NTC test (2.6) share helpers with them and must keep their
# own, already correct, behaviour.
set -euo pipefail
cd /app
patch -p1 --no-backup-if-mismatch < "$(dirname "$0")/fix.patch"

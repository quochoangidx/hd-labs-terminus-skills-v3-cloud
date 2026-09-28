#!/bin/bash
# Reference repair of /app/src/hailadj against the Crop-Hail Loss Adjustment Procedure (edition 7).
#
# | Rule          | File                  | Change                                                                 |
# |---------------|-----------------------|------------------------------------------------------------------------|
# | 3.2, 3.3      | hailadj/plots.py      | stand loss and defoliation are averaged over all of a field's plots, not only the plots with a figure above nought |
# | 4.1, 4.3      | hailadj/leaf.py       | the R4 row of the leaf-loss chart is 40 per cent                        |
# | 4.2           | hailadj/loss.py       | leaf loss is taken as a share of what the stand loss leaves, not added whole |
# | 5.1           | figures.py, loss.py   | the minimum loss reads a new tenths.minimum_loss figure of 8.0 per cent; tenths.floor stays 5.0 for the plot figure |
# | 5.2           | hailadj/figures.py    | the straight deductible (tenths.straight) is 10.0 per cent             |
# | 5.2           | hailadj/loss.py       | the vanishing deductible never pays more than the loss                 |
# | 1.1, 5.3      | hailadj/claim.py      | the indemnity is rounded to the cent, half up, instead of cut off       |
# | 7.2           | figures.py, claim.py  | the minimum claim reads a new cents.minimum_claim figure of 10,000 cents; cents.floor stays 2,500 for the replant line |
# | 3.1, 6.1      | plots.py, replant.py  | (no change)                                                            |
# | 1.2-1.6       | hailadj/sheet.py      | (no change)                                                            |
#
# Strategy: each rule is applied to the inputs its defined terms reach. A sample plot that
# is not hail-thinned and a replanting of less than 10.0 acres are reached by no rule that
# says what their figure is, so they keep the step today's code takes, with the package's
# own figures at today's values.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

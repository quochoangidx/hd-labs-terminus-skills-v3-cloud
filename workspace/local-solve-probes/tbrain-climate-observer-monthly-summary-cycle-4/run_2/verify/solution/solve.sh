#!/bin/bash
# Reference repair for /app/src/coopsum, following /app/docs/observer-handbook.md (network handbook CN-7 part 3).
#
# Rule        Topic                      File               Change
# 2.2, 3.1    maximum's day              crediting.py       a maximum read at a morning observation (hour 0-11) goes to the
#                                                           day before its form day, `next` to the month's last day, a form
#                                                           day 1 maximum out of the month (was every maximum on its form day)
# 3.2         minimum's day              crediting.py       (no change: every minimum on its form day)
# 2.1, 2.4,   precipitation's day        crediting.py       a day's precipitation entered at a morning observation goes to the
# 3.3                                                       day before its form day (was always its form day); an accumulated
#                                                           amount (1.3, the first catch after unread days) is not the catch
#                                                           of one observation day (2.1, 2.4), so 3.3 does not reach it and
#                                                           it stays on the day the package credits it to today (its own
#                                                           form day); 5.1/5.2 total it
# 1.2         trace                      entries.py         a trace counts nought (was one hundredth)
# 1.4, 4.1    means, rounding            temperature.py     (no change: exact half-up in whole tenths)
# 2.7-2.9,    mean temperature           temperature.py     a well-observed month (gap count five or fewer): the average of
# 4.3, 6                                                    its standard means, its mean maximum and mean minimum (was the
#                                                           mean of its days' mean temperatures); any other month has no
#                                                           standard means, so it keeps the package's figure, the mean of
#                                                           its days' means to tenths
# 4.2, 5.4    tied extremes              temperature.py,    the latest of the tied days (was the first)
#                                        precipitation.py
# 4.4         degree days                temperature.py     each day's mean rounded to the whole degree before the 65 F base
#                                                           (was the unrounded mean, the month's total rounded)
# 4.5         threshold days             temperature.py     90.0 or above, 32.0 or below, 0.0 or below include the value itself
#                                                           (were strict)
# 5.1-5.3     totals, precipitation days precipitation.py   0.10 and 1.00 inch or more include the value itself (were strict)
# 2.6, 6      lacking days, layout       summary.py         (no change beyond passing the month's length to the mean)
#
# Strategy: change each figure only where the handbook gives a rule for it; where no rule reaches a reading
# or a month, keep the step the package takes today, worked on the values the handbook defines. The driver
# tools/coopsum_run.py is not touched.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

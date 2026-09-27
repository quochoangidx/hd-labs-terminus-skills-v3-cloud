#!/bin/bash
# Reference repair for /app/mlnet, following /app/manual/npm4-local-magnitude.md (NPM-4).
#
# NPM-4 rule                  File            Change
# 2.2 magnification 2080      amplitude.py    Wood-Anderson magnification 2080 (was Richter's nominal 2800)
# 2.2 half of peak-to-peak    amplitude.py    record amplitude is half the picker's peak-to-peak value
# 3.1 hypocentral distance    distance.py     sqrt(epi_km^2 + depth_km^2) (was the epicentral distance); it feeds
#                                             the correction, distance_km and the contributor test
# 3.3 linear in distance      attenuation.py  between two listed distances, linear in distance (was log distance)
# 3.2 beyond the table        attenuation.py  (no change) outside 10-600 km NPM-4 gives no correction, so the
#                                             shipped end-segment log-distance calculation stays, fed with the
#                                             hypocentral distance
# 4.1/4.2 correction added    station.py      the station correction is added (was subtracted)
# 2.3/4.3 station mean        station.py      mean of the channel magnitudes of the readings, an amplitude at
#                                             least three times its channel's noise (was the largest amplitude)
# 1.2/4.3 a station's readings bulletin.py     a station's readings are those of all its recordings in the event
#                                             (two sensors of one site): one station magnitude, reported on each
#                                             of its recordings, and one vote in the median and the count of
#                                             three (was one magnitude per recording, each counted)
# 5.2 median                  network.py      median of the contributors, mean of the middle two when even
#                                             (was the mean)
# 5.3 fewer than three        network.py      fewer than three contributors gives no network magnitude (null)
# 5.1 contributes / 6 report  network.py,     (no change) already the table's 10-600 km, both ends included;
#                             bulletin.py     report keys and order (one object per recording) already as section 6
# driver                      tools/          (no change) tools/ml_bulletin.py is not touched
#
# Strategy: repair each rule where NPM-4 speaks, on the whole range section 1 allows, and keep today's
# calculation for the one value it gives no rule for (the correction off the table), with every other step
# around that value still following NPM-4. No other exclusion, clamp or guard is added.
set -euo pipefail
cd /
patch -p1 --no-backup-if-mismatch < /solution/fix.patch

#!/bin/bash
# Reference schedules for the four weeks.
#
# They are the best schedules found by a ruin-and-recreate search with
# simulated annealing (solution/search/lns.py) and an iterated local search
# (solution/search/ils.py), over several seeds and restarts. Each target is
# 6 percent above them. solution/search/one-session/ holds the schedules
# from one fresh session per week (lns.py 70 min, then ils.py 30 min, one
# core), which also meet every target. The searches are not run here.
#
# week      reference   one session   target
# week-36      33983       33983       36021
# week-37      47936       50087       50812
# week-38      77699       81637       82360
# week-39     112876      118759      119648
set -euo pipefail
mkdir -p /app/schedules
cp /solution/schedules/*.json /app/schedules/
for w in week-36 week-37 week-38 week-39; do
    python3 /app/tools/check_schedule.py "/app/weeks/$w.json" "/app/schedules/$w.json"
done

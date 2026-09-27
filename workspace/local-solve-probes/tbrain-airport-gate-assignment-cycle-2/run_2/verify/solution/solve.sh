#!/bin/bash
# Reference stand plans for the four days.
#
# They come from simulated annealing over the stand rules in
# /app/docs/stand-rules.md with incremental cost updates. Moves: move a turn to
# another stand it fits, sending the turns it collides with there back to its old
# stand; and exchange everything two stands hold over a time window that grows
# until no turn crosses its edges. Runs started from the shipped planner and later
# from the cheapest plan so far, pooled with the best plans from trial runs, with
# the temperature falling from 30000-60000 to 10-30 over 20-60 minutes, several
# seeds per day, until restarts stopped improving. Each target is the cost of the
# cheapest plan seen.
set -euo pipefail
mkdir -p /app/plans
cp /solution/plans/*.json /app/plans/
for d in day-1 day-2 day-3 day-4; do
    python3 /app/tools/check_plan.py "/app/days/$d.json" "/app/plans/$d.json"
done

#!/bin/bash
# Reference stand plans for the four days.
#
# They come from simulated annealing over the stand rules in
# /app/docs/stand-rules.md, started from the shipped planner's plan, with four
# moves: move one turn to another stand it fits and is free on; swap the stands
# of two turns; put a turn on a stand and re-place the turns it collides with on
# their cheapest free stands; and exchange everything two stands hold inside a
# time window. Several seeds per day, restarted from the cheapest plan in
# further rounds, then iterated shorter anneals at varied starting temperatures
# and single anneals of two and four hours from the best plan. Each target is the cost of
# the cheapest plan seen.
set -euo pipefail
mkdir -p /app/plans
cp /solution/plans/*.json /app/plans/
for d in day-1 day-2 day-3 day-4; do
    python3 /app/tools/check_plan.py "/app/days/$d.json" "/app/plans/$d.json"
done

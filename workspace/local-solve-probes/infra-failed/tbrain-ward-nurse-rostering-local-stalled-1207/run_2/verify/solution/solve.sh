#!/bin/bash
# Reference rosters for the four wards.
#
# They come from simulated annealing over the rules in /app/docs/roster-rules.md,
# started from the shipped planner's roster. The search lets hard rules break at
# a large price per breach and keeps the cheapest roster with none. Moves: set
# one nurse's code on one day; swap two nurses' codes on one day; swap a block of
# two to seven days between two nurses; rotate a block of one nurse's row by a
# day. Several seeds per ward, then repeated shorter anneals restarted from the
# best roster at varied starting temperatures, and single runs of one to four hours.
# Each target is the penalty of the cheapest roster seen.
set -euo pipefail
mkdir -p /app/rosters
cp /solution/rosters/*.json /app/rosters/
for w in ash birch cedar dale; do
    python3 /app/tools/check_roster.py "/app/wards/$w.json" "/app/rosters/$w.json"
done

#!/bin/bash
# Reference stand plans for the four days, saved from runs of
# /solution/search.py (the search itself; it is not rerun here).
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
#
# day      checker output         target
# day-1    valid, cost 7241380    7241380
# day-2    valid, cost 9017700    9017700
# day-3    valid, cost 10098740   10098740
# day-4    valid, cost 15505590   15505590
#
# The script checks each plan with /app/tools/check_plan.py and stops with an
# error unless the checker reports it valid at a cost no higher than the day's
# target in /app/days/targets.json.
set -euo pipefail
mkdir -p /app/plans
cp /solution/plans/*.json /app/plans/
for d in day-1 day-2 day-3 day-4; do
    out="$(python3 /app/tools/check_plan.py "/app/days/$d.json" "/app/plans/$d.json")"
    echo "$d: $out"
    cost="${out#valid, cost }"
    target="$(python3 -c 'import json, sys; print(json.load(open("/app/days/targets.json"))[sys.argv[1]])' "$d")"
    if [ "$cost" = "$out" ] || [ "$cost" -gt "$target" ]; then
        echo "$d: plan is not valid within its target ($target)" >&2
        exit 1
    fi
done

#!/bin/bash
# Reference rosters for the four wards.
#
# They come from simulated annealing over the rules in /app/docs/roster-rules.md,
# started from the shipped planner's roster. The search lets hard rules break at
# a large price per breach and keeps the cheapest roster with none. Moves: set
# one nurse's code on one day; swap two nurses' codes on one day; swap a block of
# two to seven days between two nurses; rotate a block of one nurse's row by a
# day. Several seeds per ward, then repeated shorter anneals restarted from the
# best roster at varied starting temperatures, and single runs of one to four hours;
# the best rosters from trial runs were pooled in and the searches restarted from them.
# Each target is the penalty of the cheapest roster seen.
#
# ward     checker output         target
# ash      valid, penalty 440     440
# birch    valid, penalty 1070    1070
# cedar    valid, penalty 820     820
# dale     valid, penalty 1650    1650
#
# The script checks each roster with /app/tools/check_roster.py and stops with an
# error unless the checker reports it valid at a penalty no higher than the
# ward's target in /app/wards/targets.json.
set -euo pipefail
mkdir -p /app/rosters
cp /solution/rosters/*.json /app/rosters/
for w in ash birch cedar dale; do
    out="$(python3 /app/tools/check_roster.py "/app/wards/$w.json" "/app/rosters/$w.json")"
    echo "$w: $out"
    penalty="${out#valid, penalty }"
    target="$(python3 -c 'import json, sys; print(json.load(open("/app/wards/targets.json"))[sys.argv[1]])' "$w")"
    if [ "$penalty" = "$out" ] || [ "$penalty" -gt "$target" ]; then
        echo "$w: roster is not valid within its target ($target)" >&2
        exit 1
    fi
done

#!/bin/bash
# Reference layouts for the four editions, saved from runs of
# /solution/search.py (the search itself; it is not rerun here).
#
# They come from a large-neighbourhood search over the rules in
# /app/docs/makeup-rules.md, started from the shipped planner's layout. Each step
# clears one to four pages (random pages, one spread, or pages of one section),
# takes the cleared ads plus a sample of left-out ads in a randomized order, and
# puts each at its cheapest spot on the cleared pages, at the lowest flat stretch
# of the columns' filled heights (an ad must rest on the foot or on ads across
# its whole width, so a page's ads always fill each column from the foot up).
# Steps are accepted by simulated annealing. Several seeds per edition, then
# repeated shorter searches restarted from the best layout at varied starting
# temperatures, and single runs of two and four hours. Each target is the cost of the
# cheapest layout seen.
#
# edition  checker output        target
# mon      valid, cost 4635       4635
# wed      valid, cost 6701       6701
# fri      valid, cost 7500       7500
# sat      valid, cost 10601      10601
#
# The script checks each layout with /app/tools/check_layout.py and stops with an
# error unless the checker reports it valid at a cost no higher than the edition's
# target in /app/editions/targets.json.
set -euo pipefail
mkdir -p /app/layouts
cp /solution/layouts/*.json /app/layouts/
for e in mon wed fri sat; do
    out="$(python3 /app/tools/check_layout.py "/app/editions/$e.json" "/app/layouts/$e.json")"
    echo "$e: $out"
    cost="${out#valid, cost }"
    target="$(python3 -c 'import json, sys; print(json.load(open("/app/editions/targets.json"))[sys.argv[1]])' "$e")"
    if [ "$cost" = "$out" ] || [ "$cost" -gt "$target" ]; then
        echo "$e: layout is not valid within its target ($target)" >&2
        exit 1
    fi
done

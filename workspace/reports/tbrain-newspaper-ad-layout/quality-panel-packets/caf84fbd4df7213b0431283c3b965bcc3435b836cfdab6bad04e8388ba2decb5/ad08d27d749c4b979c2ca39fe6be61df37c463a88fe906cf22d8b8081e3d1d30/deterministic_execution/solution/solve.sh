#!/bin/bash
# Reference layouts for the four editions.
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
set -euo pipefail
mkdir -p /app/layouts
cp /solution/layouts/*.json /app/layouts/
for e in mon wed fri sat; do
    python3 /app/tools/check_layout.py "/app/editions/$e.json" "/app/layouts/$e.json"
done

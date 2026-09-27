#!/bin/bash
# Reference plans for the four mornings.
#
# They were produced by searching the rules in /app/docs/dispatch-rules.md: a
# guided local search start, then a slack-induced string-removal search (remove
# strings of consecutive customers from routes near a random customer, reinsert
# them at their cheapest feasible positions with occasional skipped positions,
# move each route to the cheapest vehicle kind that can run it, swap kinds between
# routes, simulated-annealing acceptance), run from many seeds on eight cores for
# a few hours in all, keeping the cheapest plan. Each target is that plan's cost.
#
# morning        plan cost = target
# harbour-lanes     77867
# old-town         147362
# riverside        201921
# north-ring       288705
set -euo pipefail
mkdir -p /app/plans
cp /solution/plans/*.json /app/plans/
for m in harbour-lanes old-town riverside north-ring; do
    python3 /app/tools/check_plan.py "/app/orders/$m.json" "/app/plans/$m.json"
done

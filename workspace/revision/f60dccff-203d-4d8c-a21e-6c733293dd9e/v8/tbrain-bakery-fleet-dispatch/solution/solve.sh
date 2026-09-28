#!/bin/bash
# Reference plans for the four mornings.
#
# solution/search/sisr.py is the search that produced them: a slack-induced
# string-removal search over the rules in /app/docs/dispatch-rules.md (remove
# strings of consecutive customers from routes near a random customer, reinsert
# them at their cheapest feasible positions with occasional skipped positions,
# move each route to the cheapest vehicle kind that can run it, swap kinds
# between routes, simulated-annealing acceptance). It was run in rounds of
# several seeds per morning, each round starting from the previous round's
# cheapest plan, for a few hours on eight cores in all:
#
#   python3 search/sisr.py ORDERS.json OUT.json SECONDS SEED [START_PLAN.json]
#
# Each target is the cost of the cheapest plan kept. Re-running the search takes
# hours, so this script installs the kept plans and checks each one.
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

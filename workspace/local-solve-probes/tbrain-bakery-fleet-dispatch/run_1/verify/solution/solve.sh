#!/bin/bash
# Reference plans for the four mornings.
#
# solution/search/sisr.py is the search that produced them: a slack-induced
# string-removal search over the rules in /app/docs/dispatch-rules.md (remove
# strings of consecutive customers from routes near a random customer, reinsert
# them at their cheapest feasible positions with occasional skipped positions,
# move each route to the cheapest vehicle kind that can run it, swap kinds
# between routes, simulated-annealing acceptance):
#
#   python3 search/sisr.py ORDERS.json OUT.json SECONDS SEED [START_PLAN.json]
#
# Each target is the dearest of three independent cold-start runs of that
# search (seeds 2, 3 and 4, 2400 seconds each on one core, no start plan), so
# every one of those runs reached it. Two cores run the four mornings in about
# 80 minutes. The kept plans below come from longer runs and are cheaper than
# the targets; this script installs them and checks each one.
#
# morning        plan cost   target
# harbour-lanes     77867     80734
# old-town         147362    148979
# riverside        201921    210436
# north-ring       288705    302006
set -euo pipefail
mkdir -p /app/plans
cp /solution/plans/*.json /app/plans/
for m in harbour-lanes old-town riverside north-ring; do
    python3 /app/tools/check_plan.py "/app/orders/$m.json" "/app/plans/$m.json"
done

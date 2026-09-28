#!/bin/bash
# Reference plans for the four mornings.
#
# They were produced by a vehicle-routing search over the rules in
# /app/docs/dispatch-rules.md: guided local search from a parallel cheapest
# insertion start, then an adaptive large-neighbourhood search (random, related,
# worst and whole-route removal, regret-2 reinsertion, a move of each route to
# the cheapest vehicle kind that can still run it, 2-opt on improvements) run
# from several seeds, keeping the cheapest plan. The targets are these costs plus
# half a percent.
#
# morning        plan cost   target
# harbour-lanes     78040     78431
# old-town         149036    149782
# riverside        205446    206474
# north-ring       297450    298938
set -euo pipefail
mkdir -p /app/plans
cp /solution/plans/*.json /app/plans/
for m in harbour-lanes old-town riverside north-ring; do
    python3 /app/tools/check_plan.py "/app/orders/$m.json" "/app/plans/$m.json"
done

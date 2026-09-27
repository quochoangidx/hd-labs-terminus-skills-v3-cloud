"""Write tbrain-bottling-line-lot-sizing/solution/solve.sh from the current targets."""
import json, os
T = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tasks", "tbrain-bottling-line-lot-sizing")
t = json.load(open(os.path.join(T, "tests", "targets.json")))
rows = "".join(f"# {s:<8} valid, cost {t[s]:<10} {t[s]}\n" for s in ["dorset", "kent", "fife", "tyne"])
body = f'''#!/bin/bash
# Reference production plans for the four sites, saved from runs of
# /solution/search.py (the search itself; it is not rerun here).
#
# search.py anneals the batches of each product on each line and day, keeping
# every line-day within capacity: it shifts batches to another day or line,
# merges two runs of a product to save a changeover, adds or removes batches, and
# moves a whole run to another day. Runs started from the shipped planner's plan
# and later from the cheapest plan so far, several seeds per site at starting
# temperatures near the size of a changeover cost, until restarts stopped
# improving. Each target is the cost of the cheapest plan seen.
#
# site     checker output        target
{rows}#
# The script checks each plan with /app/tools/check_plan.py and stops with an
# error unless the checker reports it valid at a cost no higher than the site's
# target in /app/sites/targets.json.
set -euo pipefail
mkdir -p /app/plans
cp /solution/plans/*.json /app/plans/
for s in dorset kent fife tyne; do
    out="$(python3 /app/tools/check_plan.py "/app/sites/$s.json" "/app/plans/$s.json")"
    echo "$s: $out"
    cost="${{out#valid, cost }}"
    target="$(python3 -c 'import json, sys; print(json.load(open("/app/sites/targets.json"))[sys.argv[1]])' "$s")"
    if [ "$cost" = "$out" ] || [ "$cost" -gt "$target" ]; then
        echo "$s: plan is not valid within its target ($target)" >&2
        exit 1
    fi
done
'''
p = os.path.join(T, "solution", "solve.sh")
open(p, "w").write(body); os.chmod(p, 0o755)
print("wrote solve.sh", t)

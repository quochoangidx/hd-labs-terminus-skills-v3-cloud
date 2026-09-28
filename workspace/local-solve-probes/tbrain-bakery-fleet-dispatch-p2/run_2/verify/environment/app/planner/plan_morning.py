"""Current dispatch planner: nearest-next greedy, vans first.

Usage: python3 planner/plan_morning.py orders/<morning>.json plans/<morning>.json

Builds one route at a time. A route leaves when the bakery opens and keeps
driving to the nearest customer it can still reach inside that customer's window
with room on board; when nothing fits, it goes home and the next vehicle starts.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from check_plan import distance, evaluate  # noqa: E402

ORDER = ("van", "truck", "bike")


def plan(orders):
    depot = orders["depot"]
    left = {c["id"]: c for c in orders["customers"]}
    fleet = sorted(orders["fleet"], key=lambda f: ORDER.index(f["type"]) if f["type"] in ORDER else 99)
    routes = []
    for kind in fleet:
        for _ in range(kind["count"]):
            if not left:
                break
            clock, here, crates, driven, stops = depot["open"], depot, 0, 0, []
            while True:
                best = None
                for c in left.values():
                    leg = distance(here, c)
                    start = max(clock + leg * kind["pace"], c["ready"])
                    if start > c["due"] or crates + c["demand"] > kind["capacity"]:
                        continue
                    back = start + c["service"] + distance(c, depot) * kind["pace"]
                    if back > depot["close"] or back - depot["open"] > kind["shift"]:
                        continue
                    total = driven + leg + distance(c, depot)
                    if kind["range"] is not None and total > kind["range"]:
                        continue
                    if best is None or leg < best[0]:
                        best = (leg, c, start)
                if best is None:
                    break
                leg, c, start = best
                stops.append(c["id"])
                clock, here, crates, driven = start + c["service"], c, crates + c["demand"], driven + leg
                del left[c["id"]]
            if stops:
                routes.append({"type": kind["type"], "depart": depot["open"], "stops": stops})
    return {"routes": routes}


def main(argv):
    with open(argv[1]) as fh:
        orders = json.load(fh)
    result = plan(orders)
    with open(argv[2], "w") as fh:
        json.dump(result, fh, indent=1)
    try:
        print("cost", evaluate(orders, result))
    except ValueError as exc:
        print("INFEASIBLE:", exc)


if __name__ == "__main__":
    main(sys.argv)

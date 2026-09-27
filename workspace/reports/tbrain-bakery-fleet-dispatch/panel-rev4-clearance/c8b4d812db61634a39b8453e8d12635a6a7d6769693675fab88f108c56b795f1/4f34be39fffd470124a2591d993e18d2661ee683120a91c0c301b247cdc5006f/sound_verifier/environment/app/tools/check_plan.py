"""Check a delivery plan against docs/dispatch-rules.md and print its cost.

Usage: python3 tools/check_plan.py orders/<morning>.json plans/<morning>.json
"""

import json
import math
import sys


class PlanError(ValueError):
    pass


ROUTE_KEYS = {"type", "depart", "stops"}


def _no_repeats(pairs):
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise PlanError(f"a key appears twice in one object: {sorted(k for k in set(keys) if keys.count(k) > 1)}")
    return dict(pairs)


def _not_json(name):
    raise PlanError(f"{name} is not a JSON value")


def load_plan(path):
    """Read a plan file as strict JSON: no repeated keys, no NaN or Infinity."""
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh, object_pairs_hook=_no_repeats, parse_constant=_not_json)
    except PlanError:
        raise
    except (ValueError, RecursionError) as exc:
        raise PlanError(f"not a readable JSON plan: {exc}") from None


def distance(a, b):
    sq = (a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2
    d = math.isqrt(sq)
    return d if d * d == sq else d + 1


def evaluate(orders, plan):
    depot = orders["depot"]
    customers = {c["id"]: c for c in orders["customers"]}
    fleet = {f["type"]: f for f in orders["fleet"]}
    used = {t: 0 for t in fleet}
    served = set()
    total = 0
    if not isinstance(plan, dict) or not isinstance(plan.get("routes"), list):
        raise PlanError("a plan is a JSON object with a routes list")
    if set(plan) != {"routes"}:
        raise PlanError(f"a plan has only a routes key, not {sorted(set(plan) - {'routes'})}")
    for number, route in enumerate(plan["routes"], start=1):
        where = f"route {number}"
        if not isinstance(route, dict):
            raise PlanError(f"{where}: not a JSON object")
        if set(route) != ROUTE_KEYS:
            raise PlanError(f"{where}: a route has exactly the keys type, depart and stops")
        kind = fleet.get(route.get("type")) if isinstance(route.get("type"), str) else None
        if kind is None:
            raise PlanError(f"{where}: unknown vehicle type {route.get('type')!r}")
        stops = route.get("stops")
        if not isinstance(stops, list) or not stops:
            raise PlanError(f"{where}: no stops")
        depart = route.get("depart")
        if not isinstance(depart, int) or isinstance(depart, bool) or depart < depot["open"]:
            raise PlanError(f"{where}: departure must be a whole second, not before opening")
        used[route["type"]] += 1
        clock, here, crates, driven = depart, depot, 0, 0
        for cid in stops:
            if not isinstance(cid, int) or isinstance(cid, bool) or cid not in customers:
                raise PlanError(f"{where}: unknown customer {cid!r}")
            if cid in served:
                raise PlanError(f"{where}: customer {cid} delivered twice")
            served.add(cid)
            customer = customers[cid]
            leg = distance(here, customer)
            driven += leg
            start = max(clock + leg * kind["pace"], customer["ready"])
            if start > customer["due"]:
                raise PlanError(f"{where}: customer {cid} reached at {start}, after its window closes at {customer['due']}")
            clock = start + customer["service"]
            crates += customer["demand"]
            here = customer
        leg = distance(here, depot)
        driven += leg
        back = clock + leg * kind["pace"]
        if back > depot["close"]:
            raise PlanError(f"{where}: back at {back}, after the bakery closes")
        if back - depart > kind["shift"]:
            raise PlanError(f"{where}: out for {back - depart} s, longer than the {kind['shift']} s shift")
        if crates > kind["capacity"]:
            raise PlanError(f"{where}: {crates} crates on a vehicle that carries {kind['capacity']}")
        if kind["range"] is not None and driven > kind["range"]:
            raise PlanError(f"{where}: drives {driven} units, beyond its range of {kind['range']}")
        total += kind["fixed"] + kind["per_unit"] * driven
    for name, count in used.items():
        if count > fleet[name]["count"]:
            raise PlanError(f"{count} routes use a {name}; only {fleet[name]['count']} are available")
    missing = sorted(set(customers) - served)
    if missing:
        raise PlanError(f"{len(missing)} customers get no delivery, first {missing[:5]}")
    return total


def main(argv):
    if len(argv) != 3:
        sys.exit(__doc__)
    with open(argv[1]) as fh:
        orders = json.load(fh)
    try:
        cost = evaluate(orders, load_plan(argv[2]))
    except PlanError as exc:
        print(f"INFEASIBLE: {exc}")
        return 1
    print(f"feasible, cost {cost}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

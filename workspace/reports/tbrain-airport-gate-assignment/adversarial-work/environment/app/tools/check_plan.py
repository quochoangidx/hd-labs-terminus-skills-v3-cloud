"""Check a gate plan against the stand rules and print its cost.

Usage: python3 check_plan.py DAY.json PLAN.json
"""

import json
import sys


class PlanError(Exception):
    pass


def evaluate(day, plan):
    """Return the integer cost of the plan, or raise PlanError."""
    if not isinstance(plan, dict) or not isinstance(plan.get("stands"), dict):
        raise PlanError('the plan must be an object with a "stands" object')
    stands = {s["id"]: s for s in day["stands"]}
    turns = {t["id"]: t for t in day["turns"]}
    where = {}
    for sid, lst in plan["stands"].items():
        if sid not in stands:
            raise PlanError(f"unknown stand {sid!r}")
        if not isinstance(lst, list):
            raise PlanError(f"stand {sid}: expected a list of turn ids")
        for tid in lst:
            if not isinstance(tid, str) or tid not in turns:
                raise PlanError(f"stand {sid}: unknown turn {tid!r}")
            if tid in where:
                raise PlanError(f"turn {tid} is placed twice")
            where[tid] = sid
    missing = [t for t in turns if t not in where]
    if missing:
        raise PlanError(f"turn {missing[0]} is not placed ({len(missing)} missing)")

    buffer = day["buffer_minutes"]
    for sid, lst in plan["stands"].items():
        s = stands[sid]
        for tid in lst:
            t = turns[tid]
            if t["size"] > s["size"]:
                raise PlanError(f"turn {tid} (size {t['size']}) does not fit stand {sid} (size {s['size']})")
            if t["international"] and not s["international"]:
                raise PlanError(f"international turn {tid} on stand {sid}, which has no passport control")
        occ = sorted((turns[tid]["arrive"], turns[tid]["depart"], tid) for tid in lst)
        for (a1, d1, t1), (a2, d2, t2) in zip(occ, occ[1:]):
            if d1 + buffer > a2:
                raise PlanError(f"stand {sid}: turn {t2} arrives at {a2}, before {t1} leaves at {d1} plus the {buffer}-minute buffer")

    for a, b in day["wingtip_pairs"]:
        big_a = [turns[t] for t in plan["stands"].get(a, []) if turns[t]["size"] == 3]
        big_b = [turns[t] for t in plan["stands"].get(b, []) if turns[t]["size"] == 3]
        for x in big_a:
            for y in big_b:
                if x["arrive"] < y["depart"] and y["arrive"] < x["depart"]:
                    raise PlanError(f"widebody turns {x['id']} on {a} and {y['id']} on {b} are on the ground together")

    walk = day["walk_metres"]
    idx = {s["id"]: i for i, s in enumerate(day["stands"])}
    cost = 0
    for tid, sid in where.items():
        s = stands[sid]
        if s["remote"]:
            t = turns[tid]
            cost += day["bus_cost_per_passenger"] * (t["pax_in"] + t["pax_out"])
    for tr in day["transfers"]:
        a, b = where[tr["from"]], where[tr["to"]]
        cost += tr["passengers"] * walk[idx[a]][idx[b]]
    return cost


def main(argv):
    if len(argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    with open(argv[1]) as fh:
        day = json.load(fh)
    with open(argv[2]) as fh:
        plan = json.load(fh)
    try:
        cost = evaluate(day, plan)
    except PlanError as exc:
        print(f"invalid: {exc}")
        return 1
    print(f"valid, cost {cost}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

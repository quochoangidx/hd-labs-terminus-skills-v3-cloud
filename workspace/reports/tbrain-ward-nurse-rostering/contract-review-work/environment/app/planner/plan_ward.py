"""Roster planner used by the ward office.

Fills the roster one day at a time, nights first, then earlies, then lates.
For each shift it takes nurses who may legally work it, fewest hours so far
first, until the shift has a senior nurse, its registered nurses and its
minimum head count. It does not look at requests, weekends or contracts.

Usage: python3 plan_ward.py WARD.json ROSTER.json
"""

import json
import sys


def may_work(ward, row, d, s):
    rules = ward["rules"]
    if row[d] != ".":
        return False
    if d > 0 and (row[d - 1] + s) in ("NE", "NL", "LE"):
        return False
    if d > 0 and row[d - 1] == "N" and s != "N":
        return False
    for back in range(2, rules["rest_days_after_nights"] + 1):
        k = d - back
        if k >= 0 and row[k] == "N" and all(row[j] == "." for j in range(k + 1, d)):
            return False
    run = 0
    for k in range(d - 1, -1, -1):
        if row[k] == ".":
            break
        run += 1
    return run + 1 <= rules["max_consecutive_days"]


def plan(ward):
    days = ward["days"]
    hours = ward["shift_hours"]
    rows = {n["id"]: ["."] * days for n in ward["nurses"]}
    worked = {n["id"]: 0 for n in ward["nurses"]}
    nights = {n["id"]: 0 for n in ward["nurses"]}
    for d in range(days):
        # a nurse on nights yesterday either stays on nights or rests
        for s in "NEL":
            need = ward["cover"][s]
            on = []

            def pick(pred, count):
                cands = [n for n in ward["nurses"]
                         if d not in n["leave"] and pred(n) and may_work(ward, rows[n["id"]], d, s)
                         and not (s == "N" and nights[n["id"]] >= n["max_nights"])]
                cands.sort(key=lambda n: (worked[n["id"]] - n["max_hours"], n["id"]))
                for n in cands[:max(0, count)]:
                    rows[n["id"]][d] = s
                    worked[n["id"]] += hours[s]
                    nights[n["id"]] += s == "N"
                    on.append(n)

            pick(lambda n: n["grade"] == "senior", 1)
            pick(lambda n: n["grade"] in ("RN", "senior"), need["registered"] - sum(n["grade"] != "HCA" for n in on))
            pick(lambda n: True, need["minimum"] - len(on))
            if len(on) < need["minimum"] or not any(n["grade"] == "senior" for n in on) \
                    or sum(n["grade"] != "HCA" for n in on) < need["registered"]:
                raise SystemExit(f"cannot cover day {d} shift {s}")
    return {"roster": {nid: "".join(r) for nid, r in rows.items()}}


def main(argv):
    with open(argv[1]) as fh:
        ward = json.load(fh)
    with open(argv[2], "w") as fh:
        json.dump(plan(ward), fh, indent=1)


if __name__ == "__main__":
    main(sys.argv)

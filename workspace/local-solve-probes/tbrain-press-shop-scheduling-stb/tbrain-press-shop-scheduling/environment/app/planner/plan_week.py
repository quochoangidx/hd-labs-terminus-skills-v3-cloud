"""Current press planner: earliest due date first, each job to the press that finishes it soonest.

Usage: python3 planner/plan_week.py weeks/<week>.json schedules/<week>.json
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from check_schedule import clear_of, evaluate, minutes  # noqa: E402


def plan(week):
    presses = week["presses"]
    state = {p["id"]: (0, p["initial_family"]) for p in presses}
    lists = {p["id"]: [] for p in presses}
    for job in sorted(week["jobs"], key=lambda j: (j["due"], j["id"])):
        best = None
        for p in presses:
            if job["tonnage"] > p["tonnage"]:
                continue
            clock, family = state[p["id"]]
            change = week["setup_minutes"][family][job["family"]]
            change_start = clear_of(clock, change, p["maintenance"])
            run = minutes(job, p)
            start = clear_of(max(change_start + change, job["release"]), run, p["maintenance"])
            if best is None or start + run < best[0]:
                best = (start + run, p["id"])
        end, pid = best
        lists[pid].append(job["id"])
        state[pid] = (end, job["family"])
    return {"presses": lists}


def main(argv):
    with open(argv[1]) as fh:
        week = json.load(fh)
    schedule = plan(week)
    with open(argv[2], "w") as fh:
        json.dump(schedule, fh, indent=1)
    print("cost", evaluate(week, schedule))


if __name__ == "__main__":
    main(sys.argv)

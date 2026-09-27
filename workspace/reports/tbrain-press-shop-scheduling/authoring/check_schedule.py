"""Check a press schedule against docs/press-rules.md and print its cost.

Usage: python3 tools/check_schedule.py weeks/<week>.json schedules/<week>.json
"""

import json
import sys


class ScheduleError(ValueError):
    pass


def minutes(job, press):
    return -(-job["strokes"] // press["strokes_per_minute"])


def clear_of(start, length, windows):
    """Earliest time at or after start at which [t, t + length) meets no maintenance window."""
    moved = True
    while moved:
        moved = False
        for a, b in windows:
            if start < b and a < start + length:
                start = b
                moved = True
    return start


def evaluate(week, schedule):
    presses = {p["id"]: p for p in week["presses"]}
    jobs = {j["id"]: j for j in week["jobs"]}
    setup = week["setup_minutes"]
    if not isinstance(schedule, dict) or not isinstance(schedule.get("presses"), dict):
        raise ScheduleError("a schedule is a JSON object with a presses object")
    seen = set()
    setup_total = 0
    penalty = 0
    for pid, sequence in schedule["presses"].items():
        press = presses.get(pid)
        if press is None:
            raise ScheduleError(f"unknown press {pid!r}")
        if not isinstance(sequence, list):
            raise ScheduleError(f"{pid}: the job list is not a list")
        clock = 0
        family = press["initial_family"]
        for jid in sequence:
            if not isinstance(jid, str) or jid not in jobs:
                raise ScheduleError(f"{pid}: unknown job {jid!r}")
            if jid in seen:
                raise ScheduleError(f"{pid}: job {jid} scheduled twice")
            seen.add(jid)
            job = jobs[jid]
            if job["tonnage"] > press["tonnage"]:
                raise ScheduleError(f"{pid}: job {jid} needs {job['tonnage']} t, the press has {press['tonnage']} t")
            change = setup[family][job["family"]]
            change_start = clear_of(clock, change, press["maintenance"])
            run = minutes(job, press)
            start = clear_of(max(change_start + change, job["release"]), run, press["maintenance"])
            end = start + run
            setup_total += change
            penalty += job["weight"] * max(0, end - job["due"])
            clock = end
            family = job["family"]
    missing = sorted(set(jobs) - seen)
    if missing:
        raise ScheduleError(f"{len(missing)} jobs are not scheduled, first {missing[:5]}")
    return week["setup_cost_per_minute"] * setup_total + penalty


def main(argv):
    if len(argv) != 3:
        sys.exit(__doc__)
    with open(argv[1]) as fh:
        week = json.load(fh)
    with open(argv[2]) as fh:
        schedule = json.load(fh)
    try:
        cost = evaluate(week, schedule)
    except ScheduleError as exc:
        print(f"INFEASIBLE: {exc}")
        return 1
    print(f"feasible, cost {cost}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

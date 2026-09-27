"""Stand planner used by the apron office.

Takes the turns in order of arrival and puts each on the first stand in the
day's stand list that it fits and that is free for it; remote stands come last
in the list, so a turn is bussed only when no contact stand is free.

Usage: python3 plan_day.py DAY.json PLAN.json
"""

import json
import sys


def free(day, stand, turn, placed):
    buffer = day["buffer_minutes"]
    for other in placed[stand["id"]]:
        if not (other["depart"] + buffer <= turn["arrive"] or turn["depart"] + buffer <= other["arrive"]):
            return False
    if turn["size"] == 3:
        for a, b in day["wingtip_pairs"]:
            if stand["id"] in (a, b):
                nb = b if stand["id"] == a else a
                for other in placed[nb]:
                    if other["size"] == 3 and other["arrive"] < turn["depart"] and turn["arrive"] < other["depart"]:
                        return False
    return True


def plan(day):
    placed = {s["id"]: [] for s in day["stands"]}
    for turn in sorted(day["turns"], key=lambda t: (t["arrive"], t["id"])):
        for stand in day["stands"]:
            if turn["size"] > stand["size"]:
                continue
            if turn["international"] and not stand["international"]:
                continue
            if free(day, stand, turn, placed):
                placed[stand["id"]].append(turn)
                break
        else:
            raise SystemExit(f"no stand for turn {turn['id']}")
    return {"stands": {sid: [t["id"] for t in lst] for sid, lst in placed.items()}}


def main(argv):
    with open(argv[1]) as fh:
        day = json.load(fh)
    result = plan(day)
    with open(argv[2], "w") as fh:
        json.dump(result, fh, indent=1)


if __name__ == "__main__":
    main(sys.argv)

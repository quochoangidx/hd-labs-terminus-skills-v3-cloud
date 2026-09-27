"""Check a ward roster against the rostering rules and print its penalty.

Usage: python3 check_roster.py WARD.json ROSTER.json
"""

import json
import os
import sys

sys.set_int_max_str_digits(4300)

SHIFTS = "ELN"


class RosterError(Exception):
    pass


MAX_BYTES = 2_000_000
MAX_DEPTH = 64
MAX_DIGITS = 4300


def _no_constant(name):
    raise RosterError(f"{name} is not JSON")


def _digits(text):
    if sum(c.isdigit() for c in text) > MAX_DIGITS:
        raise RosterError(f"a number is written with more than {MAX_DIGITS} digits")
    return text


def _int(text):
    return int(_digits(text))


def _float(text):
    return float(_digits(text))


def _no_repeats(pairs):
    names = set()
    for name, _ in pairs:
        if name in names:
            raise RosterError(f"the name {name!r} appears twice in one object")
        names.add(name)
    return dict(pairs)


def _check_depth(value):
    stack = [(value, 1)]
    while stack:
        v, depth = stack.pop()
        if isinstance(v, (dict, list)):
            if depth > MAX_DEPTH:
                raise RosterError(f"the file nests values more than {MAX_DEPTH} levels deep")
            stack.extend((x, depth + 1) for x in (v.values() if isinstance(v, dict) else v))


def load_roster(path):
    """Read a roster file: standard JSON of at most MAX_BYTES bytes."""
    if os.path.getsize(path) > MAX_BYTES:
        raise RosterError(f"the file is larger than {MAX_BYTES} bytes")
    with open(path, "rb") as fh:
        data = fh.read()
    try:
        value = json.loads(data.decode("utf-8"), parse_constant=_no_constant, object_pairs_hook=_no_repeats,
                           parse_int=_int, parse_float=_float)
    except (UnicodeDecodeError, ValueError) as exc:
        raise RosterError(f"the file is not valid JSON: {exc}")
    except RecursionError:
        raise RosterError(f"the file nests values more than {MAX_DEPTH} levels deep")
    _check_depth(value)
    return value


def evaluate(ward, roster):
    """Return the integer penalty of the roster, or raise RosterError."""
    if not isinstance(roster, dict) or not isinstance(roster.get("roster"), dict):
        raise RosterError('the roster must be an object with a "roster" object')
    days = ward["days"]
    nurses = {n["id"]: n for n in ward["nurses"]}
    rows = roster["roster"]
    for nid in rows:
        if nid not in nurses:
            raise RosterError(f"unknown nurse {nid!r}")
    for nid in nurses:
        row = rows.get(nid)
        if not isinstance(row, str) or len(row) != days:
            raise RosterError(f"nurse {nid}: expected a string of {days} characters")
        bad = [c for c in row if c not in "ELN."]
        if bad:
            raise RosterError(f"nurse {nid}: unknown shift code {bad[0]!r}")

    hours = ward["shift_hours"]
    w = ward["weights"]
    rules = ward["rules"]
    penalty = 0

    # cover, day by day and shift by shift
    for d in range(days):
        for s in SHIFTS:
            on = [nurses[nid] for nid in nurses if rows[nid][d] == s]
            need = ward["cover"][s]
            rn = sum(1 for n in on if n["grade"] in ("RN", "senior"))
            senior = sum(1 for n in on if n["grade"] == "senior")
            if len(on) < need["minimum"]:
                raise RosterError(f"day {d} shift {s}: {len(on)} on duty, minimum {need['minimum']}")
            if rn < need["registered"]:
                raise RosterError(f"day {d} shift {s}: {rn} registered nurses, need {need['registered']}")
            if senior < 1:
                raise RosterError(f"day {d} shift {s}: no senior nurse on duty")
            if len(on) < need["preferred"]:
                penalty += w["short_of_preferred"] * (need["preferred"] - len(on))

    for nid, n in nurses.items():
        row = rows[nid]
        for d in n["leave"]:
            if row[d] != ".":
                raise RosterError(f"nurse {nid} is on leave on day {d}")
        for d in range(days - 1):
            pair = row[d] + row[d + 1]
            if pair in ("NE", "NL", "LE"):
                raise RosterError(f"nurse {nid}: {row[d]} on day {d} is followed by {row[d + 1]}, too little rest")
        run = 0
        for d in range(days):
            run = run + 1 if row[d] != "." else 0
            if run > rules["max_consecutive_days"]:
                raise RosterError(f"nurse {nid}: more than {rules['max_consecutive_days']} days in a row ending day {d}")
        for d in range(days - 1):
            if row[d] == "N" and row[d + 1] != "N":
                for k in range(d + 1, min(days, d + 1 + rules["rest_days_after_nights"])):
                    if row[k] != ".":
                        raise RosterError(f"nurse {nid}: works day {k}, too soon after the nights ending day {d}")

        worked = sum(hours[c] for c in row if c != ".")
        if worked < n["min_hours"]:
            penalty += w["hour_under"] * (n["min_hours"] - worked)
        if worked > n["max_hours"]:
            penalty += w["hour_over"] * (worked - n["max_hours"])
        nights = row.count("N")
        if nights > n["max_nights"]:
            penalty += w["night_over"] * (nights - n["max_nights"])
        weekends = 0
        for sat in range(5, days, 7):
            a = row[sat] != "."
            b = sat + 1 < days and row[sat + 1] != "."
            if a or b:
                weekends += 1
            if sat + 1 < days and a != b:
                penalty += w["split_weekend"]
        if weekends > rules["max_weekends"]:
            penalty += w["weekend_over"] * (weekends - rules["max_weekends"])
        for d in range(1, days - 1):
            if row[d] != "." and row[d - 1] == "." and row[d + 1] == ".":
                penalty += w["lone_day"]
        for req in n["requests"]:
            d, want = req["day"], req["off"]
            if want == "day" and row[d] != ".":
                penalty += w["request"]
            elif want in SHIFTS and row[d] == want:
                penalty += w["request"]
    return penalty


def main(argv):
    if len(argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    with open(argv[1]) as fh:
        ward = json.load(fh)
    try:
        roster = load_roster(argv[2])
        penalty = evaluate(ward, roster)
    except RosterError as exc:
        print(f"invalid: {exc}")
        return 1
    print(f"valid, penalty {penalty}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

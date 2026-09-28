"""Independent expectation model for the Fleet Tire Tread Standard TS-6 (tread-standard.md).

Written from the standard alone; it never imports the treadcheck package. Every figure is worked in
integers. Two figures the standard does not settle mirror the shipped package, each marked "Shipped step":
  * the depth of a reading that is not a measurement (the gauge showed under 10 tenths, 2.1/3.1), which
    today's code takes as the figure shown;
  * the tread worn and distance of a tire that is not fresh (2.3/4.2), which today's code takes from the
    first reading to the latest.
"""

from datetime import date

MEASUREMENT = 10  # 2.1
FRESH_MARGIN = 10  # 2.3
REMOVAL = {"steer": 40, "drive": 32, "trailer": 32}  # 2.4
WATCH_BAND = 16  # 5.1
PER_KM = 10000  # 4.3
MAX_AGE_DAYS = 2190  # 6.1
MAX_RETREADS = 2  # 6.1 (fewer than)


def half_up(num, den):
    """num/den rounded to the nearest integer, an exact half to the larger number (1.1); den > 0."""
    return (2 * num + den) // (2 * den)


def _d(text):
    return date.fromisoformat(text)


def depth(reading, offsets):
    shown, gauge = reading[2], reading[3]
    if shown >= MEASUREMENT:
        return shown + offsets[gauge]  # 3.1
    # Shipped step: a reading that is not a measurement has no rule; today's code takes what it showed.
    return shown


def entry(job, tire, offsets):
    readings = tire["readings"]  # 1.5: in date order
    first, last = readings[0], readings[-1]
    latest = depth(last, offsets)  # 4.1
    first_depth = depth(first, offsets)
    if tire["new_depth"] - first_depth <= FRESH_MARGIN:  # 2.3 fresh
        worn = tire["new_depth"] - latest  # 4.2
        distance = last[1] - tire["mounted_km"]
    else:
        # Shipped step: 4.2 speaks only of a fresh tire; today's code measures from the first reading.
        worn = first_depth - latest
        distance = last[1] - first[1]
    limit = REMOVAL[tire["position"]]
    if latest <= limit:
        status = "pull"
    elif latest <= limit + WATCH_BAND:
        status = "watch"
    else:
        status = "in service"
    age = (_d(job["report_date"]) - _d(tire["casing"])).days
    return {
        "tire": tire["tire"],
        "position": tire["position"],
        "latest": latest,
        "worn": worn,
        "distance": distance,
        "rate": half_up(worn * PER_KM, distance),  # 4.3, 1.1
        "status": status,
        "retread": status == "pull" and age < MAX_AGE_DAYS and tire["retreads"] < MAX_RETREADS,  # 6.1
    }


def summary(job):
    offsets = {g["gauge"]: g["offset"] for g in job["gauges"]}
    return {"tires": [entry(job, t, offsets) for t in job["tires"]]}


def within_limits(job):
    """Violations of section 1 (empty when the job keeps within the limits)."""
    bad = []

    def ok_date(t):
        try:
            return type(t) is str and len(t) == 10 and 2015 <= _d(t).year <= 2034
        except ValueError:
            return False

    rep = job["report_date"]
    if not ok_date(rep):
        return ["report date"]
    gs = job["gauges"]
    if not 1 <= len(gs) <= 20:
        bad.append("gauges")
    ids = [g["gauge"] for g in gs]
    if len(set(ids)) != len(ids):
        bad.append("duplicate gauge")
    for g in gs:
        if type(g["gauge"]) is not str or not 1 <= len(g["gauge"]) <= 12:
            bad.append("gauge number")
        if type(g["offset"]) is not int or not -9 <= g["offset"] <= 9:
            bad.append("offset")
    ts = job["tires"]
    if not 1 <= len(ts) <= 300:
        bad.append("tires")
    names = [t["tire"] for t in ts]
    if len(set(names)) != len(names):
        bad.append("duplicate tire")
    for t in ts:
        if type(t["tire"]) is not str or not 1 <= len(t["tire"]) <= 16:
            bad.append("tire number")
        if t["position"] not in REMOVAL:
            bad.append("position")
        if type(t["new_depth"]) is not int or not 60 <= t["new_depth"] <= 320:
            bad.append("new depth")
        if not ok_date(t["casing"]) or _d(t["casing"]) > _d(rep):
            bad.append("casing")
        if type(t["retreads"]) is not int or not 0 <= t["retreads"] <= 4:
            bad.append("retreads")
        if type(t["mounted_km"]) is not int or not 0 <= t["mounted_km"] <= 5_000_000:
            bad.append("mounted")
        rs = t["readings"]
        if not 2 <= len(rs) <= 30:
            bad.append("readings")
            continue
        if rs[0][2] < 20:
            bad.append("first reading")
        offs = {g["gauge"]: g["offset"] for g in gs}
        if rs[0][3] in offs and rs[0][2] + offs[rs[0][3]] > t["new_depth"]:
            bad.append("first reading above new")
        prev_d, prev_km = None, t["mounted_km"]
        for r in rs:
            if not ok_date(r[0]) or _d(r[0]) > _d(rep):
                bad.append("reading date")
                continue
            if type(r[1]) is not int or not 0 <= r[1] <= 5_000_000 or r[1] <= prev_km:
                bad.append("odometer")
            if type(r[2]) is not int or not 0 <= r[2] <= 320:
                bad.append("shown")
            if r[3] not in ids:
                bad.append("reading gauge")
            if prev_d is not None and _d(r[0]) <= prev_d:
                bad.append("reading order")
            prev_d, prev_km = _d(r[0]), r[1]
    return bad


if __name__ == "__main__":
    import json
    import sys
    json.dump(summary(json.load(open(sys.argv[1], encoding="utf-8"))), sys.stdout)
    sys.stdout.write("\n")

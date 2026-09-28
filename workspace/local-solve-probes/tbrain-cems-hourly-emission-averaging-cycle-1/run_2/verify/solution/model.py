"""Independent expectation model for DRP-4 (never imports cemsqr).

report(job) returns the report the procedure gives. Where the procedure gives no rule for a figure,
the model mirrors the step the shipped package takes ("Shipped step" comments), fed with the
procedure's own inputs. within_limits(job) lists every section 1 limit a job breaks (empty = inside).
"""

import datetime
from fractions import Fraction

CODES = ("OK", "CAL", "MNT", "OOC")


def rnd(x):
    """DRP-4 1.1: nearest whole unit, an exact half up (exact arithmetic)."""
    x = Fraction(x)
    q, r = divmod(x.numerator, x.denominator)
    return q + (1 if 2 * r >= x.denominator else 0)


def _hours(readings):
    out = {}
    order = []
    for rec in readings:
        key = rec[0][:13]  # 1.5: HH:00 to the next hour
        if key not in out:
            out[key] = []
            order.append(key)
        out[key].append(rec)
    return [(k, out[k]) for k in order]


def report(job):
    ref = job["unit"]["ref_o2"]
    limit = job["unit"]["limit"]
    hours = []
    for key, recs in _hours(job["readings"]):
        op = [r for r in recs if r[1] >= 1]  # 2.1
        if not op:
            continue
        good = [r for r in op if r[5] == "OK"]  # 2.2
        has_cal = any(r[5] == "CAL" for r in recs)
        valid = len(good) == len(op) or (has_cal and len(good) >= 2)  # 2.3
        h = {"hour": key, "day": key[:10], "time": Fraction(len(op), 4), "valid": valid,
             "lost": not good}  # 2.5
        if valid:
            n = len(good)
            nox = Fraction(sum(r[2] for r in good), n)  # 3.1
            o2 = Fraction(sum(r[3] for r in good), n)
            flow = Fraction(sum(r[4] for r in good), n)
            if o2 < 190:  # 2.4 firing hour; 3.2 with the 2.7 firing ratio
                h["conc"] = rnd(nox * (209 - ref) / (209 - o2))
            else:
                # Shipped step: correction.corrected() for a valid hour that is not a firing hour
                # (3.2 speaks only of firing hours): oxygen held at 190, ambient 210.
                h["conc"] = rnd(nox * (210 - ref) / (210 - min(o2, 190)))
            h["rate"] = rnd(Fraction(1194, 10**10) * nox * flow)  # 3.3, tenths of lb/h
        hours.append(h)

    valid_idx = [i for i, h in enumerate(hours) if h["valid"]]
    carried = (0, 0)
    for i, h in enumerate(hours):
        if h["valid"]:
            carried = (h["conc"], h["rate"])
            continue
        if h["lost"]:  # 4.2, 4.3
            before = [j for j in valid_idx if j < i]
            after = [j for j in valid_idx if j > i]
            if before and after:
                b, a = hours[before[-1]], hours[after[0]]
                h["conc"] = rnd(Fraction(b["conc"] + a["conc"], 2))
                h["rate"] = rnd(Fraction(b["rate"] + a["rate"], 2))
            elif before or after:
                s = hours[before[-1]] if before else hours[after[0]]
                h["conc"], h["rate"] = s["conc"], s["rate"]
            else:
                h["conc"], h["rate"] = 0, 0
        else:
            # Shipped step: substitute.fill() for an operating hour that is neither valid nor lost
            # (4.2 and 4.3 speak only of lost hours): the last valid hour's figures, nought before any.
            h["conc"], h["rate"] = carried

    # 5.1: rate (tenths lb/h) x time -> lb/10; tons x100 = lb/20
    tons = rnd(sum((h["rate"] * h["time"] for h in hours), Fraction(0)) / 200)

    days = []
    for h in hours:
        if not days or days[-1]["day"] != h["day"]:
            days.append({"day": h["day"], "hours": []})
        days[-1]["hours"].append(h)
    out_days = []
    for k, d in enumerate(days):
        rolling = None
        if k >= 29:  # 6.1
            vals = [h["conc"] for e in days[k - 29:k + 1] for h in e["hours"] if h["valid"]]
            if vals:
                rolling = rnd(Fraction(sum(vals), len(vals)))
        out_days.append({"day": d["day"], "rolling": rolling,
                         "exceed": rolling is not None and rolling > limit})  # 6.2

    return {
        "hours": [{"hour": h["hour"], "kind": "valid" if h["valid"] else "substitute",
                   "nox": h["conc"], "lb": h["rate"]} for h in hours],
        "days": out_days,
        "operating_hours": len(hours),
        "valid_hours": len(valid_idx),
        "nox_tons": tons,
    }


def within_limits(job):
    """Every section 1 limit the job breaks; empty when the job is inside them."""
    bad = []
    u = job.get("unit", {})
    if not (isinstance(u.get("ref_o2"), int) and 0 <= u["ref_o2"] <= 150):
        bad.append("ref_o2")
    if not (isinstance(u.get("limit"), int) and 1 <= u["limit"] <= 20000):
        bad.append("limit")
    recs = job.get("readings", [])
    if not 1 <= len(recs) <= 11520:
        bad.append("records")
    prev = None
    for r in recs:
        t = datetime.datetime.strptime(r[0], "%Y-%m-%d %H:%M")
        if t.minute not in (0, 15, 30, 45) or not 2020 <= t.year <= 2039:
            bad.append("start " + r[0])
        if prev is not None and t - prev != datetime.timedelta(minutes=15):
            bad.append("order " + r[0])
        prev = t
        for v, lo, hi in ((r[1], 0, 1500), (r[2], 0, 20000), (r[3], 0, 205), (r[4], 0, 90000000)):
            if not (type(v) is int and lo <= v <= hi):
                bad.append("figure " + r[0])
        if r[5] not in CODES:
            bad.append("code " + r[0])
        if r[5] == "CAL" and r[1] < 1:
            bad.append("CAL off " + r[0])
    hours = {}
    for r in recs:
        hours.setdefault(r[0][:13], set()).add(r[5])
    for key, codes in hours.items():
        if "CAL" in codes and codes & {"MNT", "OOC"}:
            bad.append("CAL with MNT/OOC " + key)
    return bad

"""Independent expectation model for the monthly station summary.

Derived from /app/docs/observer-handbook.md (network handbook CN-7 part 3) alone; it does not import
the coopsum package. Where the handbook's rules do not reach a reading or a figure, the model mirrors the
step the shipped package takes today and says so in a "Shipped step" comment (instruction: whatever no
rule reaches keeps what the package does with it today).

    python3 model.py FORM.json      prints the summary the handbook gives for the form
"""

import json
import re
import sys
from datetime import date

TEMP_RE = re.compile(r"^-?\d{1,3}\.\d$")
AMOUNT_RE = re.compile(r"^\d{1,2}\.\d{2}$")


# -- 1. units, entries and rounding ------------------------------------------------------------------

def temp_tenths(text):
    """1.1: a temperature entry in whole tenths of a degree, None for M."""
    if text == "M":
        return None
    assert TEMP_RE.match(text), text
    negative = text.startswith("-")
    whole, frac = text.lstrip("-").split(".")
    value = int(whole) * 10 + int(frac)
    return -value if negative else value


def amount_hundredths(text):
    """1.2: an amount in whole hundredths; a trace counts nought. None for M and A (no amount)."""
    if text in ("M", "A"):
        return None
    if text == "T":
        return 0
    assert AMOUNT_RE.match(text), text
    whole, frac = text.split(".")
    return int(whole) * 100 + int(frac)


def nearest(num, den):
    """1.4: num/den to the nearest whole unit, an exact half to the higher value (den > 0)."""
    q, r = divmod(num, den)
    return q + 1 if 2 * r >= den else q


def days_in(month):
    year, mon = int(month[:4]), int(month[5:7])
    nxt = date(year + (mon == 12), mon % 12 + 1, 1)
    return (nxt - date(year, mon, 1)).days


# -- 2./3. crediting --------------------------------------------------------------------------------

def is_morning(hour):
    """2.2: a morning observation is taken at an hour from 0 through 11."""
    return 0 <= hour <= 11


def credited(station, n):
    """Section 3: the maxima, minima and precipitation credited to each day 1..n of the month."""
    morning = is_morning(station["hour"])
    entries = station["days"] + [station["next"]]  # form days 1..n, then n + 1 for `next`
    highs, lows, rain = {}, {}, {}
    unread = False
    for form_day, entry in enumerate(entries, start=1):
        high = temp_tenths(entry["max"])
        if high is not None:
            highs[form_day - 1 if morning else form_day] = high  # 3.1
        low = temp_tenths(entry["min"])
        if low is not None:
            lows[form_day] = low  # 3.2
        text = entry["precip"]
        if text == "A":
            unread = True  # 1.3: the gauge was not read at this observation
            continue
        amount = amount_hundredths(text)
        if amount is None:
            continue
        if unread:
            # 1.3 / 2.4: an accumulated amount holds two or more observation days, so it is not a day's
            # precipitation and 3.3 does not reach it; 3.4 still credits it to one day, and 5.1 totals it.
            # Shipped step: the package credits every amount to its own form day.
            day = form_day
        else:
            day = form_day - 1 if morning else form_day  # 3.3
        unread = False
        rain[day] = rain.get(day, 0) + amount  # 5.1
    keep = range(1, n + 1)  # 3.4
    return ({d: v for d, v in highs.items() if d in keep},
            {d: v for d, v in lows.items() if d in keep},
            {d: v for d, v in rain.items() if d in keep})


# -- 4. temperature -----------------------------------------------------------------------------------

def last_extreme(values, better):
    """4.2 / 5.4: the value and the latest day that reaches it, or (None, None)."""
    best_day = None
    for day in sorted(values):
        if best_day is None or not better(values[best_day], values[day]):
            best_day = day
    return (None, None) if best_day is None else (values[best_day], best_day)


def station_summary(station, month):
    n = days_in(month)
    highs, lows, rain = credited(station, n)
    lacking_max = n - len(highs)
    lacking_min = n - len(lows)
    complete = lacking_max <= 5 and lacking_min <= 5  # 2.7

    mean_max = nearest(sum(highs.values()), len(highs)) if highs else None  # 4.1
    mean_min = nearest(sum(lows.values()), len(lows)) if lows else None
    paired = [d for d in range(1, n + 1) if d in highs and d in lows]  # 2.5: days with a mean temperature
    if complete:
        mean = nearest(mean_max + mean_min, 2)  # 2.8 standard means, 4.3
    elif paired:
        # 2.8: a month that is not complete has no standard means, so 4.3 does not reach it; section 6
        # gives `mean` as a temperature to tenths, null only with no day's mean temperature.
        # Shipped step: the package gives the mean of the days' mean temperatures, to tenths (1.4).
        mean = nearest(sum(highs[d] + lows[d] for d in paired), 2 * len(paired))
    else:
        mean = None  # Shipped step: no day with a mean temperature gives no figure.

    high, high_day = last_extreme(highs, lambda best, v: v < best)
    low, low_day = last_extreme(lows, lambda best, v: v > best)

    heating = cooling = 0
    for d in paired:  # 4.4
        rounded = nearest(highs[d] + lows[d], 20)  # the day's mean, in whole degrees
        heating += max(0, 65 - rounded)
        cooling += max(0, rounded - 65)

    total = sum(rain.values())  # 5.2
    wet = {d: v for d, v in rain.items() if v >= 1}  # 5.3
    top, top_day = last_extreme(wet, lambda best, v: v < best)  # 5.4

    def label(d):
        return None if d is None else f"{month}-{d:02d}"

    def deg(v):
        return None if v is None else v / 10

    return {
        "id": station["id"],
        "complete": complete,
        "lacking_max": lacking_max,
        "lacking_min": lacking_min,
        "mean_max": deg(mean_max),
        "mean_min": deg(mean_min),
        "mean": deg(mean),
        "highest": deg(high),
        "highest_day": label(high_day),
        "lowest": deg(low),
        "lowest_day": label(low_day),
        "heating_dd": heating,
        "cooling_dd": cooling,
        "days_max_90": sum(1 for v in highs.values() if v >= 900),  # 4.5
        "days_max_32": sum(1 for v in highs.values() if v <= 320),
        "days_min_32": sum(1 for v in lows.values() if v <= 320),
        "days_min_0": sum(1 for v in lows.values() if v <= 0),
        "precip": total / 100,
        "precip_days": len(wet),
        "precip_days_10": sum(1 for v in wet.values() if v >= 10),
        "precip_days_100": sum(1 for v in wet.values() if v >= 100),
        "greatest": None if top is None else top / 100,
        "greatest_day": label(top_day),
    }


def summarize(form):
    return {"network": form["network"], "month": form["month"],
            "stations": [station_summary(s, form["month"]) for s in form["stations"]]}


# -- limits (1.5) and trap-input predicates -----------------------------------------------------------

def within_limits(form):
    """Assert that a form keeps within handbook 1.5; returns True."""
    month = form["month"]
    assert re.match(r"^\d{4}-\d{2}$", month) and "1950-01" <= month <= "2099-12", month
    n = days_in(month)
    stations = form["stations"]
    assert 1 <= len(stations) <= 40
    assert len({s["id"] for s in stations}) == len(stations)
    for s in stations:
        assert isinstance(s["hour"], int) and 0 <= s["hour"] <= 23
        assert len(s["days"]) == n
        entries = s["days"] + [s["next"]]
        run = 0
        for k, e in enumerate(entries):
            for key in ("max", "min"):
                v = temp_tenths(e[key])
                assert v is None or -600 <= v <= 1300
            p = e["precip"]
            if p == "A":
                run += 1
                assert run <= 6 and k < len(entries) - 1
                continue
            if run:
                assert p != "M"
            run = 0
            a = amount_hundredths(p)
            assert a is None or 0 <= a <= 2000
    return True


def accumulated_positions(station):
    """Form days (1..n+1) whose entry is an accumulated amount (1.3)."""
    out, unread = [], False
    for k, e in enumerate(station["days"] + [station["next"]], start=1):
        if e["precip"] == "A":
            unread = True
            continue
        if unread and e["precip"] != "M":
            out.append(k)
        unread = False
    return out


def carries_accumulated_at_morning(form):
    """Trap T1 input: an accumulated amount entered at a morning observation."""
    return any(is_morning(s["hour"]) and accumulated_positions(s) for s in form["stations"])


def carries_incomplete_month(form):
    """Trap T2 input: a station whose month is not complete for temperature."""
    return any(not station_summary(s, form["month"])["complete"] for s in form["stations"])


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as handle:
        job = json.load(handle)
    within_limits(job)
    json.dump(summarize(job), sys.stdout)
    sys.stdout.write("\n")

"""The audit report of one log."""

from .cycle import CYCLE_DAYS, CYCLE_MINUTES, RECAP_DAYS, history
from .limits import DRIVING_LIMIT, WINDOW_MINUTES, violations
from .shifts import shifts
from .stretches import DAY, day_totals, is_driving, is_on_duty, stretches


def hours(minutes):
    return round(minutes / 60, 1)


def minutes_between(items, counts, start, end):
    total = 0
    for s in items:
        if counts(s):
            total += max(0, min(s.end, end) - max(s.start, start))
    return total


def time_left(log, items, ndays):
    end = log["end"]
    start = max(s for s, _ in shifts(items) if s < end)
    driven = minutes_between(items, is_driving, start, end)
    used = minutes_between(items, is_on_duty, start, end)
    hist = history(log, items, ndays)
    last = RECAP_DAYS + ndays - 1
    cycle = sum(hist[max(0, last - (CYCLE_DAYS - 1)):last + 1])
    return {
        "driving": hours(DRIVING_LIMIT - driven),
        "window": hours(WINDOW_MINUTES - used),
        "cycle": hours(CYCLE_MINUTES - cycle),
    }


def audit_log(log):
    items = stretches(log)
    ndays = (log["end"] - 1) // DAY + 1
    driving = day_totals(items, ndays, is_driving)
    on_duty = day_totals(items, ndays, is_on_duty)
    per_day = violations(log, items, ndays)
    days = [
        {"day": d + 1, "driving": driving[d], "on_duty": on_duty[d], "violations": per_day[d]}
        for d in range(ndays)
    ]
    return {"driver": log["driver"], "days": days, "left": time_left(log, items, ndays)}

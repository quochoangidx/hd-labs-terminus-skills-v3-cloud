"""Violation minutes of every driving limit, day by day."""

from bisect import bisect_right

from .cycle import CYCLE_MINUTES, earlier_days, history
from .shifts import breaks, shifts
from .stretches import DAY, is_driving, is_on_duty

DRIVING_LIMIT = 11 * 60
WINDOW_MINUTES = 14 * 60
BREAK_AFTER = 8 * 60
RULES = ("3.1", "3.2", "3.3", "3.4")


def violations(log, items, ndays):
    per_day = [dict.fromkeys(RULES, 0) for _ in range(ndays)]
    shift_starts = [s for s, _ in shifts(items)]
    hist = history(log, items, ndays)
    break_points = sorted(set(shift_starts) | {b[1] for b in breaks(items)})

    shift_no = -1
    shift_driven = shift_on = 0
    since_break = 0
    next_point = 0
    today, today_on = -1, 0
    for s in items:
        driving, on_duty = is_driving(s), is_on_duty(s)
        if not (driving or on_duty):
            continue
        for t in range(s.start, s.end):
            day = t // DAY
            if day != today:
                today, today_on = day, 0
            current = bisect_right(shift_starts, t) - 1
            if current != shift_no:
                shift_no, shift_driven, shift_on = current, 0, 0
            while next_point < len(break_points) and break_points[next_point] <= t:
                since_break = 0
                next_point += 1
            if driving:
                start = shift_starts[shift_no]
                where = per_day[start // DAY]
                if shift_driven >= DRIVING_LIMIT:
                    where["3.1"] += 1
                if shift_on >= WINDOW_MINUTES:
                    where["3.2"] += 1
                if since_break >= BREAK_AFTER:
                    where["3.3"] += 1
                if earlier_days(hist, day) + today_on >= CYCLE_MINUTES:
                    where["3.4"] += 1
                shift_driven += 1
                since_break += 1
            if on_duty:
                shift_on += 1
                today_on += 1
    return per_day

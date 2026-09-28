"""Duty-status stretches of a log and how each one counts."""

DAY = 1440
REST_STATUSES = ("off", "sleeper")


class Stretch:
    """One log entry in force from ``start`` up to, not including, ``end``."""

    __slots__ = ("status", "start", "end", "miles")

    def __init__(self, status, start, end, miles):
        self.status = status
        self.start = start
        self.end = end
        self.miles = miles

    @property
    def minutes(self):
        return self.end - self.start


def stretches(log):
    events = log["events"]
    out = []
    for i, event in enumerate(events):
        end = events[i + 1]["at"] if i + 1 < len(events) else log["end"]
        out.append(Stretch(event["status"], event["at"], end, event["miles"]))
    return out


def is_rest(stretch):
    return stretch.status in REST_STATUSES


def is_on_duty(stretch):
    return not is_rest(stretch)


def is_driving(stretch):
    return stretch.status == "driving"


def rest_periods(items):
    """Unbroken runs of rest as (start, end) pairs in log order."""
    periods = []
    for s in items:
        if not is_rest(s):
            continue
        if periods and periods[-1][1] == s.start:
            periods[-1] = (periods[-1][0], s.end)
        else:
            periods.append((s.start, s.end))
    return periods


def day_totals(items, ndays, counts):
    """Minutes of the stretches ``counts`` accepts on each day, split at midnight."""
    totals = [0] * ndays
    for s in items:
        if not counts(s):
            continue
        t = s.start
        while t < s.end:
            day = t // DAY
            upto = min(s.end, (day + 1) * DAY)
            totals[day] += upto - t
            t = upto
    return totals

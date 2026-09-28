"""Temperature figures of the monthly summary, worked in tenths of a degree."""

from .entries import half_up

BASE = 65  # the degree-day base, in whole degrees


def lacking(credited, days):
    """How many of the month's days have no reading of this kind credited."""
    return days - len(credited)


def complete(maxima, minima, days):
    """Whether the month is complete for temperature."""
    return lacking(maxima, days) <= 5 and lacking(minima, days) <= 5


def mean_of(by_day):
    """The mean of the credited readings in tenths, or None when there are none."""
    if not by_day:
        return None
    return half_up(sum(by_day.values()), len(by_day))


def monthly_mean(maxima, minima, days):
    """The month's mean temperature in tenths.

    For a well-observed month (2.8) this is the average of the month's two standard means (2.9), to
    tenths, as 4.3 requires. No rule of the handbook gives the mean temperature of a month that is
    not well-observed, so such a month keeps the package's own figure, the mean of its days' mean
    temperatures; it is None only when no day has a mean temperature (2.5).
    """
    both = [day for day in sorted(maxima) if day in minima]
    if not both:
        return None
    if complete(maxima, minima, days):
        return half_up(mean_of(maxima) + mean_of(minima), 2)
    return half_up(sum(maxima[day] + minima[day] for day in both), 2 * len(both))


def extreme(by_day, highest):
    """The day holding the highest (or lowest) credited reading, or None when there is none."""
    chosen = None
    for day in sorted(by_day):
        value = by_day[day]
        if chosen is None:
            chosen = day
        elif highest and value >= by_day[chosen]:
            chosen = day  # a reading matched later belongs to the latest of those days (4.2)
        elif not highest and value <= by_day[chosen]:
            chosen = day
    return chosen


def degree_days(maxima, minima):
    """The month's heating and cooling degree days: the totals of its days' own degree days, each
    worked from that day's mean temperature rounded to the whole degree (4.4)."""
    heating = cooling = 0
    for day in sorted(maxima):
        if day not in minima:
            continue
        whole = half_up(maxima[day] + minima[day], 20)  # the day's mean temperature, whole degrees
        heating += max(0, BASE - whole)
        cooling += max(0, whole - BASE)
    return heating, cooling


def threshold_days(maxima, minima):
    """Days with a maximum of 90.0 or above, a maximum of 32.0 or below, a minimum of 32.0 or below
    and a minimum of 0.0 or below."""
    hot = sum(1 for value in maxima.values() if value >= 900)
    cold_max = sum(1 for value in maxima.values() if value <= 320)
    freezing = sum(1 for value in minima.values() if value <= 320)
    zero = sum(1 for value in minima.values() if value <= 0)
    return hot, cold_max, freezing, zero

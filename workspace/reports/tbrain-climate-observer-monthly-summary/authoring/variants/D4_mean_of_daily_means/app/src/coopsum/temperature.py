"""Temperature figures of the monthly summary, worked in tenths of a degree."""

from .entries import half_up

BASE = 65  # the degree-day base, whole degrees F


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
    """The month's mean temperature in tenths: for a complete month the average of its standard means
    (its mean maximum and mean minimum); otherwise, as before, the mean of its days' mean temperatures."""
    both = [day for day in sorted(maxima) if day in minima]
    if not both:
        return None
    return half_up(sum(maxima[day] + minima[day] for day in both), 2 * len(both))


def extreme(by_day, highest):
    """The day holding the highest (or lowest) credited reading, or None when there is none."""
    chosen = None
    for day in sorted(by_day):
        value = by_day[day]
        if chosen is None:
            chosen = day
        elif highest and value >= by_day[chosen]:
            chosen = day
        elif not highest and value <= by_day[chosen]:
            chosen = day
    return chosen


def degree_days(maxima, minima):
    """The month's heating and cooling degree days."""
    heating = cooling = 0
    for day in sorted(maxima):
        if day not in minima:
            continue
        rounded = half_up(maxima[day] + minima[day], 20)
        heating += max(0, BASE - rounded)
        cooling += max(0, rounded - BASE)
    return heating, cooling


def threshold_days(maxima, minima):
    """Days with a maximum of 90.0 or above, a maximum of 32.0 or below, a minimum of 32.0 or below
    and a minimum of 0.0 or below."""
    hot = sum(1 for value in maxima.values() if value >= 900)
    cold_max = sum(1 for value in maxima.values() if value <= 320)
    freezing = sum(1 for value in minima.values() if value <= 320)
    zero = sum(1 for value in minima.values() if value <= 0)
    return hot, cold_max, freezing, zero

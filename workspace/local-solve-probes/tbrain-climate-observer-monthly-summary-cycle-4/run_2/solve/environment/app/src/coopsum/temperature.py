"""Temperature figures of the monthly summary, worked in tenths of a degree."""

from .entries import half_up

BASE = 65  # the degree-day base, in whole degrees
HOT = 900  # 90.0 F in tenths
FREEZING = 320  # 32.0 F in tenths
ZERO = 0  # 0.0 F in tenths
GAP_LIMIT = 5  # the largest gap count of a well-observed month (2.8)


def lacking(credited, days):
    """How many of the month's days have no reading of this kind credited."""
    return days - len(credited)


def gap_count(maxima, minima, days):
    """The month's gap count (2.7): the larger of its days lacking a maximum and lacking a minimum."""
    return max(lacking(maxima, days), lacking(minima, days))


def complete(maxima, minima, days):
    """Whether the month is well observed (2.8): a gap count of five or fewer."""
    return gap_count(maxima, minima, days) <= GAP_LIMIT


def mean_of(by_day):
    """The mean of the credited readings in tenths, or None when there are none."""
    if not by_day:
        return None
    return half_up(sum(by_day.values()), len(by_day))


def day_means_mean(maxima, minima):
    """The mean of the month's days' mean temperatures, in tenths, or None when no day has one.

    No rule of the handbook gives a mean temperature to a month that is not well observed, which has no
    standard means (2.9), so such a month keeps the figure the package has always worked out.
    """
    both = [day for day in sorted(maxima) if day in minima]
    if not both:
        return None
    return half_up(sum(maxima[day] + minima[day] for day in both), 2 * len(both))


def monthly_mean(maxima, minima, days):
    """The month's mean temperature in tenths (4.3): the average of its two standard means (2.9), to
    tenths, for a well-observed month."""
    if complete(maxima, minima, days):
        mean_max, mean_min = mean_of(maxima), mean_of(minima)
        if mean_max is not None and mean_min is not None:
            return half_up(mean_max + mean_min, 2)
    return day_means_mean(maxima, minima)


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
    """The month's heating and cooling degree days (4.4), the totals of its days' own, each worked from
    the day's mean temperature rounded to the whole degree."""
    heating = cooling = 0
    for day in sorted(maxima):
        if day not in minima:
            continue
        whole = half_up(maxima[day] + minima[day], 20)  # the day's mean to the whole degree
        heating += max(0, BASE - whole)
        cooling += max(0, whole - BASE)
    return heating, cooling


def threshold_days(maxima, minima):
    """Days with a maximum of 90.0 or above, a maximum of 32.0 or below, a minimum of 32.0 or below
    and a minimum of 0.0 or below."""
    hot = sum(1 for value in maxima.values() if value >= HOT)
    cold_max = sum(1 for value in maxima.values() if value <= FREEZING)
    freezing = sum(1 for value in minima.values() if value <= FREEZING)
    zero = sum(1 for value in minima.values() if value <= ZERO)
    return hot, cold_max, freezing, zero

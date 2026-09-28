"""Temperature figures of the monthly summary, worked in tenths of a degree."""

from .entries import half_up

BASE = 65  # the degree-day base in whole degrees Fahrenheit
TENTHS_PER_DEGREE = 10
HOT = 900  # 90.0 F in tenths
FREEZING = 320  # 32.0 F in tenths


def lacking(credited, days):
    """How many of the month's days have no reading of this kind credited (2.6)."""
    return days - len(credited)


def complete(maxima, minima, days):
    """Whether the month is complete for temperature (2.7)."""
    return lacking(maxima, days) <= 5 and lacking(minima, days) <= 5


def mean_of(by_day):
    """The mean of the credited readings in tenths, or None when there are none (4.1)."""
    if not by_day:
        return None
    return half_up(sum(by_day.values()), len(by_day))


def days_with_mean(maxima, minima):
    """The month's days that have a mean temperature (2.5), in date order."""
    return [day for day in sorted(maxima) if day in minima]


def monthly_mean(maxima, minima, days):
    """The month's mean temperature in tenths.

    For a month complete for temperature this is the average of its two standard means (4.3). For a
    month that has no standard means no rule of the handbook applies, so the figure the package has
    always worked out is kept: the average of its days' mean temperatures."""
    both = days_with_mean(maxima, minima)
    if not both:
        return None
    if complete(maxima, minima, days):
        return half_up(mean_of(maxima) + mean_of(minima), 2)
    return half_up(sum(maxima[day] + minima[day] for day in both), 2 * len(both))


def extreme(by_day, highest):
    """The day holding the highest (or lowest) credited reading, or None when there is none. When the
    reading is credited to more than one day, the latest of those days is given (4.2)."""
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


def rounded_mean(maxima, minima, day):
    """The day's mean temperature rounded to the whole degree (4.4)."""
    return half_up(maxima[day] + minima[day], 2 * TENTHS_PER_DEGREE)


def degree_days(maxima, minima):
    """The month's heating and cooling degree days, the totals of its days' own (4.4)."""
    heating = cooling = 0
    for day in days_with_mean(maxima, minima):
        mean = rounded_mean(maxima, minima, day)
        heating += max(0, BASE - mean)
        cooling += max(0, mean - BASE)
    return heating, cooling


def threshold_days(maxima, minima):
    """Days with a maximum of 90.0 or above, a maximum of 32.0 or below, a minimum of 32.0 or below
    and a minimum of 0.0 or below (4.5)."""
    hot = sum(1 for value in maxima.values() if value >= HOT)
    cold_max = sum(1 for value in maxima.values() if value <= FREEZING)
    freezing = sum(1 for value in minima.values() if value <= FREEZING)
    zero = sum(1 for value in minima.values() if value <= 0)
    return hot, cold_max, freezing, zero

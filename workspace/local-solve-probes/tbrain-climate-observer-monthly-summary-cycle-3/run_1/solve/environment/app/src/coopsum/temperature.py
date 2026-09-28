"""Temperature figures of the monthly summary, worked in tenths of a degree."""

from .entries import half_up

BASE = 65  # the degree-day base, in whole degrees
GAP_LIMIT = 5  # a well-observed month's gap count is five or fewer (2.8)


def lacking(credited, days):
    """How many of the month's days have no reading of this kind credited."""
    return days - len(credited)


def gap_count(maxima, minima, days):
    """The month's gap count (2.7): the larger of its numbers of days lacking a maximum and a
    minimum."""
    return max(lacking(maxima, days), lacking(minima, days))


def complete(maxima, minima, days):
    """Whether the month is well observed (2.8)."""
    return gap_count(maxima, minima, days) <= GAP_LIMIT


def mean_of(by_day):
    """The mean of the credited readings in tenths, or None when there are none."""
    if not by_day:
        return None
    return half_up(sum(by_day.values()), len(by_day))


def days_with_mean(maxima, minima):
    """The month's days that have a mean temperature (2.5), in date order."""
    return [day for day in sorted(maxima) if day in minima]


def monthly_mean(maxima, minima, days):
    """The month's mean temperature in tenths (4.3): for a well-observed month the average of its two
    standard means, to tenths. For a month that is not well observed no rule of the handbook applies,
    and the package's own figure, the mean of its days' mean temperatures, is kept. None when no day
    of the month has a mean temperature."""
    both = days_with_mean(maxima, minima)
    if not both:
        return None
    if complete(maxima, minima, days):
        mean_max, mean_min = mean_of(maxima), mean_of(minima)
        if mean_max is not None and mean_min is not None:
            return half_up(mean_max + mean_min, 2)
    return half_up(sum(maxima[day] + minima[day] for day in both), 2 * len(both))


def extreme(by_day, highest):
    """The day holding the highest (or lowest) credited reading, or None when there is none."""
    chosen = None
    for day in sorted(by_day):
        value = by_day[day]
        if chosen is None:
            chosen = day
        elif highest and value >= by_day[chosen]:
            chosen = day  # a reading matched later is given on the latest of those days (4.2)
        elif not highest and value <= by_day[chosen]:
            chosen = day
    return chosen


def degree_days(maxima, minima):
    """The month's heating and cooling degree days."""
    heating = cooling = 0
    for day in days_with_mean(maxima, minima):
        # the day's mean temperature, in twentieths of a degree, rounded to the whole degree (4.4)
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

"""Daily mean values."""

from gaugeflow.pieces import span_totals
from gaugeflow.record import discharge_series

DAY = 86_400


def daily_mean(series, day, gap):
    """The time-weighted mean value of a series over day ``day``."""
    start, end = DAY * day, DAY * (day + 1)
    covered, integral = span_totals(series, start, end, gap)
    if covered > 0:
        return integral / covered
    # No covered time: the note does not describe this case; keep prior result.
    values = [v for t, v in series if start <= t < end]
    if not values:
        return None
    return sum(values) / len(values)


def daily_values(record, table, curve, first_day, last_day, gap):
    """Daily mean discharge for each day from ``first_day`` to ``last_day``."""
    series = discharge_series(record, table, curve)
    return [daily_mean(series, day, gap) for day in range(first_day, last_day + 1)]

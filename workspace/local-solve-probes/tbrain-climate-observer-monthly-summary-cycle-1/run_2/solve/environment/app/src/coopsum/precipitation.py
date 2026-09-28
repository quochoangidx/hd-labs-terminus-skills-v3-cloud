"""Precipitation figures of the monthly summary, worked in hundredths of an inch."""

MEASURABLE = 1  # 0.01 inch
TENTH = 10  # 0.10 inch
INCH = 100  # 1.00 inch


def precipitation_days(totals):
    """The month's days whose credited precipitation is measurable, in date order."""
    return [day for day in sorted(totals) if totals[day] >= MEASURABLE]


def month_total(totals):
    """The month's precipitation in hundredths."""
    return sum(totals.values())


def heavy_days(totals):
    """How many days had 0.10 inch or more, and 1.00 inch or more."""
    wet = precipitation_days(totals)
    return (sum(1 for day in wet if totals[day] >= TENTH),
            sum(1 for day in wet if totals[day] >= INCH))


def greatest_day(totals):
    """The day of the month's greatest precipitation, or None for a month without a precipitation day."""
    chosen = None
    for day in precipitation_days(totals):
        if chosen is None or totals[day] >= totals[chosen]:  # the latest of matching days (5.4)
            chosen = day
    return chosen

"""The monthly summary of a network form, laid out as handbook CN-7 part 3 section 6 gives it."""

from . import precipitation, temperature
from .crediting import credit_precipitation, credit_temperatures
from .entries import day_label, month_length


def degrees(value):
    """A figure in tenths of a degree as the JSON number of the summary."""
    return None if value is None else value / 10


def inches(value):
    """A figure in hundredths of an inch as the JSON number of the summary."""
    return None if value is None else value / 100


def station_summary(station, month):
    days = month_length(month)
    maxima, minima = credit_temperatures(station, days)
    totals = credit_precipitation(station, days)

    well_observed = temperature.complete(maxima, minima, days)
    mean_max = temperature.mean_of(maxima)
    mean_min = temperature.mean_of(minima)
    if well_observed and mean_max is not None and mean_min is not None:
        # 4.3: a well-observed month has standard means (2.9), and its mean temperature is their
        # average, to tenths.
        mean = temperature.standard_mean(mean_max, mean_min)
    else:
        mean = temperature.monthly_mean(maxima, minima)

    high_day = temperature.extreme(maxima, highest=True)
    low_day = temperature.extreme(minima, highest=False)
    heating, cooling = temperature.degree_days(maxima, minima)
    hot, cold_max, freezing, zero = temperature.threshold_days(maxima, minima)
    wet = precipitation.precipitation_days(totals)
    tenth_days, inch_days = precipitation.heavy_days(totals)
    top_day = precipitation.greatest_day(totals)

    return {
        "id": station["id"],
        "complete": well_observed,
        "lacking_max": temperature.lacking(maxima, days),
        "lacking_min": temperature.lacking(minima, days),
        "mean_max": degrees(mean_max),
        "mean_min": degrees(mean_min),
        "mean": degrees(mean),
        "highest": None if high_day is None else degrees(maxima[high_day]),
        "highest_day": None if high_day is None else day_label(month, high_day),
        "lowest": None if low_day is None else degrees(minima[low_day]),
        "lowest_day": None if low_day is None else day_label(month, low_day),
        "heating_dd": heating,
        "cooling_dd": cooling,
        "days_max_90": hot,
        "days_max_32": cold_max,
        "days_min_32": freezing,
        "days_min_0": zero,
        "precip": inches(precipitation.month_total(totals)),
        "precip_days": len(wet),
        "precip_days_10": tenth_days,
        "precip_days_100": inch_days,
        "greatest": None if top_day is None else inches(totals[top_day]),
        "greatest_day": None if top_day is None else day_label(month, top_day),
    }


def summarize(form):
    """The month's summary for every station on the form, in the form's order."""
    month = form["month"]
    return {
        "network": form["network"],
        "month": month,
        "stations": [station_summary(station, month) for station in form["stations"]],
    }

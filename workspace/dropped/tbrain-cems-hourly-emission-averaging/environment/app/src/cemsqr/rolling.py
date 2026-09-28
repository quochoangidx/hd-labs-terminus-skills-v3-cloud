"""Rolling averages and exceedance days."""

from .rounding import half_up, mean
from .timebase import day_number

WINDOW = 30


def operating_days(hours):
    """The operating days in date order, each with its operating hours."""
    days = []
    for hour in hours:
        if not hour["operating"]:
            continue
        if not days or days[-1]["day"] != hour["day"]:
            days.append({"day": hour["day"], "hours": []})
        days[-1]["hours"].append(hour)
    return days


def rolling_days(days, limit):
    """Each operating day's rolling average and exceedance flag."""
    if not days:
        return []
    first = day_number(days[0]["day"])
    daily = [mean(hour["conc"] for hour in day["hours"]) for day in days]
    out = []
    for k, day in enumerate(days):
        today = day_number(day["day"])
        rolling = None
        if today - first >= WINDOW - 1:
            window = [daily[j] for j in range(k + 1)
                      if today - day_number(days[j]["day"]) < WINDOW]
            rolling = half_up(mean(window))
        out.append({"day": day["day"], "rolling": rolling,
                    "exceed": rolling is not None and rolling >= limit})
    return out

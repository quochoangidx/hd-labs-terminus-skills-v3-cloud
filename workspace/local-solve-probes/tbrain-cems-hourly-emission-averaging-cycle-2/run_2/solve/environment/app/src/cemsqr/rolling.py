"""Rolling averages and exceedance days."""

from .rounding import half_up, mean

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
    out = []
    for index, day in enumerate(days):
        rolling = None
        if index >= WINDOW - 1:
            window = [hour["conc"]
                      for earlier in days[index - WINDOW + 1:index + 1]
                      for hour in earlier["hours"] if hour["valid"]]
            if window:
                rolling = half_up(mean(window))
        out.append({"day": day["day"], "rolling": rolling,
                    "exceed": rolling is not None and rolling > limit})
    return out

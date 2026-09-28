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
    if not days:
        return []
    out = []
    for k, day in enumerate(days):
        rolling = None
        if k >= WINDOW - 1:  # DRP-4 6.1: twenty-nine operating days before it
            window = [hour["conc"] for d in days[k - WINDOW + 1:k + 1]
                      for hour in d["hours"] if hour["valid"]]
            if window:
                rolling = half_up(mean(window))
        out.append({"day": day["day"], "rolling": rolling,
                    "exceed": rolling is not None and rolling > limit})
    return out

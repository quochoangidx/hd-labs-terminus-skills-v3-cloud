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
    # Rule 6.1: the window is thirty operating days, and the average is over the
    # reported concentrations of the valid hours they hold.
    valid_concs = [[hour["conc"] for hour in day["hours"] if hour["valid"]]
                   for day in days]
    out = []
    for k, day in enumerate(days):
        rolling = None
        if k >= WINDOW - 1:
            window = [conc for j in range(k - WINDOW + 1, k + 1)
                      for conc in valid_concs[j]]
            if window:
                rolling = half_up(mean(window))
        out.append({"day": day["day"], "rolling": rolling,
                    "exceed": rolling is not None and rolling > limit})
    return out

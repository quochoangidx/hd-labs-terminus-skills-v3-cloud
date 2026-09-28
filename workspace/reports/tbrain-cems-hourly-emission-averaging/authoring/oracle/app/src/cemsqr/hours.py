"""Group the export into clock hours and work out each hour's averages.

A record is [start, load, nox, o2, flow, code].
"""

from .rounding import mean
from .timebase import day_of, hour_of

LOAD, NOX, O2, FLOW, CODE = 1, 2, 3, 4, 5


def group_hours(records):
    """The export's clock hours in time order, each with its records."""
    hours = []
    for record in records:
        key = hour_of(record[0])
        if not hours or hours[-1]["hour"] != key:
            hours.append({"hour": key, "day": day_of(key), "records": []})
        hours[-1]["records"].append(record)
    return hours


def operating_quarters(hour):
    return sum(1 for record in hour["records"] if record[LOAD] >= 1)


def valid_readings(hour):
    """DRP-4 2.2: the OK records of operating quarters."""
    return [record for record in hour["records"] if record[LOAD] >= 1 and record[CODE] == "OK"]


def is_valid(hour):
    """DRP-4 2.3: every operating quarter valid, or two valid readings in an hour with a CAL record."""
    good = len(valid_readings(hour))
    if good == hour["quarters"]:
        return True
    return good >= 2 and any(record[CODE] == "CAL" for record in hour["records"])


def classify(hour):
    """Set the hour's operating quarters, whether it is valid, and its averages."""
    hour["quarters"] = operating_quarters(hour)
    hour["operating"] = hour["quarters"] > 0
    hour["valid"] = hour["operating"] and is_valid(hour)
    hour["lost"] = hour["operating"] and not valid_readings(hour)
    if hour["valid"]:
        records = valid_readings(hour)
        hour["nox"] = mean(record[NOX] for record in records)
        hour["o2"] = mean(record[O2] for record in records)
        hour["flow"] = mean(record[FLOW] for record in records)
    return hour

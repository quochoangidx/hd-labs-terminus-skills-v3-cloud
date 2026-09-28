"""Group the export into clock hours and work out each hour's averages.

A record is [start, load, nox, o2, flow, code].
"""

from .correction import FIRING_O2_LIMIT
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


def is_operating_quarter(record):
    """Rule 2.1: a record whose load is 1 MW or more."""
    return record[LOAD] >= 1


def operating_quarters(hour):
    return sum(1 for record in hour["records"] if is_operating_quarter(record))


def valid_readings(hour):
    """Rule 2.2: the records of operating quarters whose status code is OK."""
    return [record for record in hour["records"]
            if is_operating_quarter(record) and record[CODE] == "OK"]


def is_valid(hour, readings):
    """Rule 2.3: a valid reading for every operating quarter, or a CAL hour with two."""
    if len(readings) == hour["quarters"]:
        return True
    if any(record[CODE] == "CAL" for record in hour["records"]):
        return len(readings) >= 2
    return False


def classify(hour):
    """Set the hour's operating quarters, whether it is valid, and its averages."""
    hour["quarters"] = operating_quarters(hour)
    hour["operating"] = hour["quarters"] > 0
    readings = valid_readings(hour)
    hour["valid"] = hour["operating"] and is_valid(hour, readings)
    hour["lost"] = hour["operating"] and not readings
    hour["firing"] = False
    if hour["valid"]:
        hour["nox"] = mean(record[NOX] for record in readings)
        hour["o2"] = mean(record[O2] for record in readings)
        hour["flow"] = mean(record[FLOW] for record in readings)
        hour["firing"] = hour["o2"] < FIRING_O2_LIMIT
    return hour

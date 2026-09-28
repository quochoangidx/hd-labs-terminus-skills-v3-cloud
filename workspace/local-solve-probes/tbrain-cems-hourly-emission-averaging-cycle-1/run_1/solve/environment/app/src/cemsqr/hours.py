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


def operating_records(hour):
    """The hour's operating quarters (rule 2.1): a load of 1 MW or more."""
    return [record for record in hour["records"] if record[LOAD] >= 1]


def valid_readings(hour):
    """The hour's valid readings (rule 2.2): operating quarters coded OK."""
    return [record for record in operating_records(hour) if record[CODE] == "OK"]


def operating_quarters(hour):
    return len(operating_records(hour))


def is_valid(hour):
    """Rule 2.3: a valid reading for every operating quarter, or a CAL hour
    with two valid readings or more."""
    operating = operating_records(hour)
    if not operating:
        return False
    valid = [record for record in operating if record[CODE] == "OK"]
    if len(valid) == len(operating):
        return True
    if any(record[CODE] == "CAL" for record in hour["records"]):
        return len(valid) >= 2
    return False


def classify(hour):
    """Set the hour's operating quarters, whether it is valid, and its averages."""
    hour["quarters"] = operating_quarters(hour)
    hour["operating"] = hour["quarters"] > 0
    hour["valid"] = hour["operating"] and is_valid(hour)
    # Rule 2.5: a lost hour is an operating hour in which no reading is valid.
    hour["lost"] = hour["operating"] and not valid_readings(hour)
    if hour["valid"]:
        # Rule 3.1: the averages are over the hour's valid readings.
        readings = valid_readings(hour)
        hour["nox"] = mean(record[NOX] for record in readings)
        hour["o2"] = mean(record[O2] for record in readings)
        hour["flow"] = mean(record[FLOW] for record in readings)
    return hour

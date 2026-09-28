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
    """The hour's operating quarters: records with a load of 1 MW or more."""
    return [record for record in hour["records"] if record[LOAD] >= 1]


def operating_quarters(hour):
    return len(operating_records(hour))


def valid_readings(hour):
    """The hour's valid readings: operating quarters whose code is OK."""
    return [record for record in operating_records(hour) if record[CODE] == "OK"]


def is_valid(hour):
    """A valid hour (rule 2.3)."""
    operating = operating_records(hour)
    if not operating:
        return False
    readings = valid_readings(hour)
    if len(readings) == len(operating):
        return True
    if any(record[CODE] == "CAL" for record in hour["records"]):
        return len(readings) >= 2
    return False


def classify(hour):
    """Set the hour's operating quarters, whether it is valid, and its averages."""
    hour["quarters"] = operating_quarters(hour)
    hour["operating"] = hour["quarters"] > 0
    readings = valid_readings(hour)
    hour["lost"] = hour["operating"] and not readings
    hour["valid"] = hour["operating"] and is_valid(hour)
    if hour["valid"]:
        hour["nox"] = mean(record[NOX] for record in readings)
        hour["o2"] = mean(record[O2] for record in readings)
        hour["flow"] = mean(record[FLOW] for record in readings)
    return hour

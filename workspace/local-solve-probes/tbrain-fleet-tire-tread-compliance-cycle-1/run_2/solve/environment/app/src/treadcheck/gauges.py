"""Tread gauges and the depths their readings give."""

MEASUREMENT_SHOWN = 10  # tenths: a reading showing this much is a measurement


def offsets(job):
    """Gauge number -> calibration offset in tenths."""
    table = {}
    for gauge in job["gauges"]:
        table[gauge["gauge"]] = gauge["offset"]
    return table


def is_measurement(shown):
    """True when a reading showing this figure is a measurement (2.1)."""
    return shown >= MEASUREMENT_SHOWN


def reading_depth(shown, gauge, table):
    """The depth in tenths one reading gives.

    A measurement's measured depth is what the gauge showed plus the gauge's
    calibration offset (3.1).  No rule settles a depth for a reading that is
    not a measurement, so such a reading gives the figure shown.
    """
    if is_measurement(shown):
        return shown + table[gauge]
    return shown


def reading_depths(tire, table):
    """The depth in tenths each of a tire's readings gives, in reading order."""
    depths = []
    for _date, _odometer, shown, gauge in tire["readings"]:
        depths.append(reading_depth(shown, gauge, table))
    return depths

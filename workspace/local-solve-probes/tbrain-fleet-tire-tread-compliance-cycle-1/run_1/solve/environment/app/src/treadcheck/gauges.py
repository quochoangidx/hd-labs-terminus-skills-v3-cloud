"""Tread gauges and the depths their readings give."""

MEASUREMENT_SHOWN = 10  # tenths; a reading showing this much is a measurement


def offsets(job):
    """Gauge number -> calibration offset in tenths."""
    table = {}
    for gauge in job["gauges"]:
        table[gauge["gauge"]] = gauge["offset"]
    return table


def is_measurement(shown):
    """True when a reading showing this figure is a measurement (2.1)."""
    return shown >= MEASUREMENT_SHOWN


def reading_depths(tire, table):
    """The depth in tenths each of a tire's readings gives, in reading order.

    A measurement's measured depth is what the gauge showed plus that gauge's
    calibration offset (3.1). The standard settles no measured depth for a
    reading that is not a measurement, so such a reading keeps the figure the
    gauge showed.
    """
    depths = []
    for _date, _odometer, shown, gauge in tire["readings"]:
        depth = shown
        if is_measurement(shown):
            depth = shown + table[gauge]
        depths.append(depth)
    return depths

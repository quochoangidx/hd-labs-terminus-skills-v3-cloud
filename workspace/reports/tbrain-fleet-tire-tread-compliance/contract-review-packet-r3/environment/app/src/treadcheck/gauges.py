"""Tread gauges and the depths their readings give."""


def offsets(job):
    """Gauge number -> calibration offset in tenths."""
    table = {}
    for gauge in job["gauges"]:
        table[gauge["gauge"]] = gauge["offset"]
    return table


def reading_depths(tire, table):
    """The depth in tenths each of a tire's readings gives, in reading order."""
    depths = []
    for _date, _odometer, shown, _gauge in tire["readings"]:
        depth = shown
        depths.append(depth)
    return depths

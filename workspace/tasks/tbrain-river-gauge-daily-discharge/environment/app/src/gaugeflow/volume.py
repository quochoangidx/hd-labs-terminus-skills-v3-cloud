"""Flow volume over a span."""

from gaugeflow.pieces import span_totals


def volume(series, start, end, gap):
    """Volume passed between ``start`` and ``end``."""
    if end < start:
        return -volume(series, end, start, gap)
    _covered, integral = span_totals(series, start, end, gap)
    return integral

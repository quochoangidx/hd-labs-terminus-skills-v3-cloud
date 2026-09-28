"""Flow volume over a span."""

from gaugeflow.pieces import span_totals


def volume(series, start, end, gap):
    """Volume passed between ``start`` and ``end``."""
    if not end > start:
        return 0.0
    _covered, integral = span_totals(series, start, end, gap)
    return integral

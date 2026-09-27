"""Joining consecutive points of a series into pieces, and totals over a span."""


def joined_pieces(series, gap):
    """``(t0, v0, t1, v1)`` for each pair of consecutive points that are joined."""
    for (t0, v0), (t1, v1) in zip(series, series[1:]):
        if t1 - t0 < gap:
            yield t0, v0, t1, v1


def span_totals(series, start, end, gap):
    """Covered time and integral of the joined pieces inside ``[start, end)``."""
    covered = 0.0
    integral = 0.0
    for t0, v0, t1, v1 in joined_pieces(series, gap):
        lo = max(t0, start)
        hi = min(t1, end)
        if hi <= lo:
            continue
        covered += hi - lo
        integral += (hi - lo) * (v0 + v1) / 2
    return covered, integral

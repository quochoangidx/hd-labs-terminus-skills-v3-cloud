"""Expected gaugeflow results, worked out from /app/docs/record-processing.md.

This module never imports, loads or runs the package under repair. Integrals
are exact (fractions) and converted to float at the end. Where the note is
silent, the expectation mirrors the shipped expression and names it; it never
answers with a reading of its own.
"""

from __future__ import annotations

from fractions import Fraction

DAY = 86_400


class Raised(Exception):
    """The shipped code raises here; carries the exception's kind."""

    def __init__(self, kind: str) -> None:
        super().__init__(kind)
        self.kind = kind


def shift_at(table, t):
    if not table:
        # Silent (2.3 names a first and a last entry). Shipped: falls through to 0.0.
        return 0.0
    if t <= table[0][0]:
        return table[0][1]  # 2.3
    if t >= table[-1][0]:
        return table[-1][1]  # 2.3
    for (t0, s0), (t1, s1) in zip(table, table[1:]):
        if t == t0:
            return s0  # 2.2, an entry's own time
        if t0 < t < t1:
            return s0 + (s1 - s0) * (t - t0) / (t1 - t0)  # 2.2
    raise AssertionError("unreachable for a strictly increasing table")


def rate(segments, stage):
    if not segments:
        # Silent (3.2 names a first segment). Shipped: self.segments[0] raises.
        raise Raised("IndexError")
    if stage < segments[0][0]:
        return 0.0  # 3.2
    lower, coefficient, offset, exponent = segments[0]
    for seg in segments:
        if seg[0] <= stage:
            lower, coefficient, offset, exponent = seg  # 3.2, greatest lower stage at or below
    depth = stage - offset
    if depth > 0:
        return coefficient * depth ** exponent  # 3.3
    if exponent > 0:
        return 0.0  # 3.3
    # Silent: exponent of zero or less at or below the offset. Shipped:
    # depth < 0 -> 0.0, otherwise coefficient * depth ** exponent.
    if depth < 0:
        return 0.0
    try:
        return coefficient * depth ** exponent
    except ZeroDivisionError:
        raise Raised("ZeroDivisionError") from None


def discharge_series(record, table, segments):
    return [(t, rate(segments, stage + shift_at(table, t))) for t, stage in record]  # 2.4, 4


def joined_pieces(series, gap):
    out = []
    for (t0, v0), (t1, v1) in zip(series, series[1:]):
        if 0 < t1 - t0 <= gap:  # 5.1-5.2
            out.append((t0, v0, t1, v1))
    return out


def _span_exact(series, start, end, gap):
    covered = Fraction(0)
    integral = Fraction(0)
    for t0, v0, t1, v1 in joined_pieces(series, gap):
        lo, hi = max(t0, start), min(t1, end)
        if hi <= lo:
            continue
        a, b = Fraction(v0), Fraction(v1)
        slope = (b - a) / (t1 - t0)
        at_lo = a + slope * (lo - t0)
        at_hi = a + slope * (hi - t0)
        covered += hi - lo
        integral += (at_lo + at_hi) * (hi - lo) / 2  # 5.3, area under the line
    return covered, integral


def span_totals(series, start, end, gap):
    covered, integral = _span_exact(series, start, end, gap)
    return float(covered), float(integral)


def daily_mean(series, day, gap):
    start, end = DAY * day, DAY * (day + 1)
    covered, integral = _span_exact(series, start, end, gap)
    if covered > 0:
        return float(integral / covered)  # 6
    # Silent: no covered time, so no time-weighted mean. Shipped daily_mean:
    # None without points in the day, else the plain mean of their values.
    values = [v for t, v in series if start <= t < end]
    if not values:
        return None
    return sum(values) / len(values)


def daily_values(record, table, segments, first_day, last_day, gap):
    series = discharge_series(record, table, segments)
    return [daily_mean(series, day, gap) for day in range(first_day, last_day + 1)]  # 9


def volume(series, start, end, gap):
    if end <= start:
        return 0.0  # 7
    return float(_span_exact(series, start, end, gap)[1])  # 7


def peaks(series, threshold, separation):
    events = []  # each: [end_time, peak_time, peak_value]
    previous_above = False
    for t, v in series:
        above = v > threshold  # 8.1
        if above and not previous_above:
            if events and t - events[-1][0] < separation:
                pass  # 8.2, the run joins the event before it
            else:
                events.append([t, t, v])
        if above:
            event = events[-1]
            if v > event[2]:
                event[1], event[2] = t, v  # 8.3, first point reaching the greatest value
            event[0] = t  # 8.2, a run's end is its last point
        previous_above = above
    return [(peak_time, value) for _end, peak_time, value in events]


def run_op(op):
    kind = op["op"]
    if kind == "shift":
        return shift_at([tuple(e) for e in op["table"]], op["t"])
    if kind == "rate":
        return rate([tuple(s) for s in op["segments"]], op["stage"])
    if kind == "series":
        return [list(p) for p in discharge_series(op["record"], [tuple(e) for e in op["table"]],
                                                  [tuple(s) for s in op["segments"]])]
    if kind == "pieces":
        return [list(p) for p in joined_pieces([tuple(p) for p in op["series"]], op["gap"])]
    if kind == "span":
        return list(span_totals([tuple(p) for p in op["series"]], op["start"], op["end"], op["gap"]))
    if kind == "daily":
        return daily_mean([tuple(p) for p in op["series"]], op["day"], op["gap"])
    if kind == "volume":
        return volume([tuple(p) for p in op["series"]], op["start"], op["end"], op["gap"])
    if kind == "peaks":
        return [list(p) for p in peaks([tuple(p) for p in op["series"]], op["threshold"], op["separation"])]
    if kind == "daily_values":
        return daily_values(op["record"], [tuple(e) for e in op["table"]], [tuple(s) for s in op["segments"]],
                            op["first"], op["last"], op["gap"])
    raise ValueError(kind)


def run_ops(ops):
    out = []
    for op in ops:
        try:
            out.append({"ok": run_op(op)})
        except Raised as exc:
            out.append({"error": exc.kind})
    return out

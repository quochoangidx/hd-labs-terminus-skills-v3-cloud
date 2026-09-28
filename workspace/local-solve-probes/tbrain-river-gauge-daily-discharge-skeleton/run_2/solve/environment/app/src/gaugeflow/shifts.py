"""Stage shifts applied to recorded stage."""

from bisect import bisect_right


def shift_at(table, t):
    """The shift in force at time ``t`` for a table of ``(time, shift)`` entries."""
    if not table:
        return 0.0
    if t <= table[0][0]:
        return table[0][1]
    if t >= table[-1][0]:
        return table[-1][1]
    times = [entry[0] for entry in table]
    i = bisect_right(times, t) - 1
    t0, s0 = table[i]
    if t == t0:
        return s0
    t1, s1 = table[i + 1]
    return s0 + (s1 - s0) * (t - t0) / (t1 - t0)

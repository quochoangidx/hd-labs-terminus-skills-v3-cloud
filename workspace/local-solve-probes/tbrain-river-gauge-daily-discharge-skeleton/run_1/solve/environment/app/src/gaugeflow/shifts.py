"""Stage shifts applied to recorded stage."""


def shift_at(table, t):
    """The shift in force at time ``t`` for a table of ``(time, shift)`` entries."""
    if not table:
        return 0.0
    if t <= table[0][0]:
        return table[0][1]
    if t >= table[-1][0]:
        return table[-1][1]
    for (t0, s0), (t1, s1) in zip(table, table[1:]):
        if t0 <= t < t1:
            if t == t0:
                return s0
            return s0 + (s1 - s0) * (t - t0) / (t1 - t0)
    return table[-1][1]

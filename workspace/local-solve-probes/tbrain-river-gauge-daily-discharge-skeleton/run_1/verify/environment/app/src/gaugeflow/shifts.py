"""Stage shifts applied to recorded stage."""


def shift_at(table, t):
    """The shift in force at time ``t`` for a table of ``(time, shift)`` entries."""
    for (t0, s0), (t1, _s1) in zip(table, table[1:]):
        if t0 <= t < t1:
            return s0
    if table and t <= table[0][0]:
        return table[0][1]
    return 0.0

"""Resets, shifts and breaks."""

from .stretches import is_driving, is_rest, rest_periods

RESET_MINUTES = 10 * 60
BREAK_MINUTES = 30


def resets(items):
    return [p for p in rest_periods(items) if p[1] - p[0] >= RESET_MINUTES]


def shifts(items):
    """(start, end) of each shift in order; end is None for a shift still open."""
    reset_starts = [p[0] for p in resets(items)]
    groups = {}
    for s in items:
        if is_rest(s):
            continue
        key = sum(1 for r in reset_starts if r <= s.start)
        groups.setdefault(key, []).append(s)
    out = []
    for key in sorted(groups):
        group = groups[key]
        driven = [s for s in group if is_driving(s)]
        start = (driven or group)[0].start
        later = [r for r in reset_starts if r > group[-1].start]
        out.append((start, later[0] if later else None))
    return out


def breaks(items):
    """(start, end) of each break in order."""
    runs = []
    for s in items:
        if is_driving(s):
            continue
        if runs and runs[-1][1] == s.start:
            runs[-1] = (runs[-1][0], s.end)
        else:
            runs.append((s.start, s.end))
    return [r for r in runs if r[1] - r[0] >= BREAK_MINUTES]

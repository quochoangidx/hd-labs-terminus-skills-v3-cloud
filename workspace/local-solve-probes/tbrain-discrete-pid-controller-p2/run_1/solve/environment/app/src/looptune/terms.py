"""The pieces a step is built from.

Each helper follows docs/control-note.md (LT-7) for the settings the note is
written for, and keeps the package's earlier behaviour elsewhere.
"""


def proportional(t, setpoint, measurement):
    b = t.setpoint_weight
    if 0.0 <= b <= 1.0:
        return t.gain * (b * setpoint - measurement)
    return t.gain * t.setpoint_weight * (setpoint - measurement)


def integral_increment(t, setpoint, measurement):
    ti = t.integral_time
    if ti > 0:
        return t.gain * t.period / ti * (setpoint - measurement)
    if ti == 0:
        return 0.0
    return t.period / ti * (t.setpoint_weight * setpoint - measurement)


def derivative_update(t, d, error, previous_error, measurement=None,
                      previous_measurement=None):
    td = t.derivative_time
    n = t.filter_divisor
    if td > 0 and n > 0 and measurement is not None:
        a = 1.0 / (1.0 + n * t.period / td)
        return a * d - t.gain * n * a * (measurement - previous_measurement)
    if td == 0:
        return 0.0
    a = 1.0 - n * t.period / td
    return a * d + t.gain * n * (error - previous_error)


def tracking_increment(t, v, u):
    tt = t.tracking_time
    if tt > 0:
        return t.period / tt * (u - v)
    if tt == 0:
        return 0.0
    return t.period / tt * (v - u)


def hold(x, low, high):
    if low < high:
        if x < low:
            return low
        if x > high:
            return high
        return x
    if x < low:
        return low
    if x > high:
        return low
    return x


def slew(previous, target, rate, period, first=False):
    if rate > 0:
        if first:
            return target
        step = rate * period
        return min(max(target, previous - step), previous + step)
    if not rate:
        return target
    step = rate / period
    return min(max(target, previous - step), previous + step)

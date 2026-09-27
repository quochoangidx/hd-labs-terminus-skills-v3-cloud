"""The pieces a step is built from.

Each helper follows LT-7 (docs/control-note.md) for the setting values the
note gives a rule for, and keeps its earlier result for the values it does not.
"""


def proportional(t, setpoint, measurement):
    b = t.setpoint_weight
    if 0.0 <= b <= 1.0:
        return t.gain * (b * setpoint - measurement)
    return t.gain * b * (setpoint - measurement)


def integral_increment(t, setpoint, measurement):
    ti = t.integral_time
    if ti > 0 and t.period > 0:
        return t.gain * t.period / ti * (setpoint - measurement)
    if ti == 0:
        return 0.0
    return t.period / ti * (t.setpoint_weight * setpoint - measurement)


def derivative_update(t, d, error, previous_error,
                      measurement=None, previous_measurement=None):
    td = t.derivative_time
    n = t.filter_divisor
    h = t.period
    if td > 0 and n > 0 and h > 0:
        a = td / (td + n * h)
        if measurement is not None and previous_measurement is not None:
            return a * d - t.gain * n * a * (measurement - previous_measurement)
        return a * d + t.gain * n * a * (error - previous_error)
    if td == 0:
        return 0.0
    a = 1.0 - n * h / td
    return a * d + t.gain * n * (error - previous_error)


def tracking_increment(t, v, u):
    tt = t.tracking_time
    if tt > 0 and t.period > 0:
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
    if low >= high:
        return high
    return min(max(x, low), high)


def slew(previous, target, rate, period):
    if rate > 0 and period > 0:
        step = rate * period
        return min(max(target, previous - step), previous + step)
    if not rate:
        return target
    step = rate / period
    return min(max(target, previous - step), previous + step)

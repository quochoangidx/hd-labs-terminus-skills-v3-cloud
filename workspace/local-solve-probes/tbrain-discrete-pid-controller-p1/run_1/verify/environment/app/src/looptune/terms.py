"""The pieces a step is built from."""


def proportional(t, setpoint, measurement):
    b = t.setpoint_weight
    if 0.0 <= b <= 1.0:
        return t.gain * (b * setpoint - measurement)
    return t.gain * b * (setpoint - measurement)


def integral_increment(t, setpoint, measurement):
    if t.integral_time > 0:
        return t.gain * t.period / t.integral_time * (setpoint - measurement)
    if t.integral_time == 0:
        return 0.0
    return t.period / t.integral_time * (t.setpoint_weight * setpoint - measurement)


def derivative_update(t, d, error, previous_error, measurement=None, previous_measurement=None):
    td = t.derivative_time
    n = t.filter_divisor
    if td > 0 and n > 0 and measurement is not None:
        if previous_measurement is None:
            previous_measurement = measurement
        a = td / (td + n * t.period)
        return a * d - t.gain * n * a * (measurement - previous_measurement)
    if td == 0:
        return 0.0
    a = 1.0 - n * t.period / td
    return a * d + t.gain * n * (error - previous_error)


def tracking_increment(t, v, u):
    if t.tracking_time > 0:
        return t.period / t.tracking_time * (u - v)
    if t.tracking_time == 0:
        return 0.0
    return t.period / t.tracking_time * (v - u)


def hold(x, low, high):
    return min(max(x, low), high)


def slew(previous, target, rate, period):
    if previous is None:
        return target
    if rate > 0:
        step = rate * period
        return min(max(target, previous - step), previous + step)
    if not rate:
        return target
    step = rate / period
    return min(max(target, previous - step), previous + step)

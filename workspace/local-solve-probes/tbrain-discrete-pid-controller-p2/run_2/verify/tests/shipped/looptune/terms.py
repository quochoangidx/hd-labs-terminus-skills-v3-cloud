"""The pieces a step is built from."""


def proportional(t, setpoint, measurement):
    return t.gain * t.setpoint_weight * (setpoint - measurement)


def integral_increment(t, setpoint, measurement):
    if t.integral_time == 0:
        return 0.0
    return t.period / t.integral_time * (t.setpoint_weight * setpoint - measurement)


def derivative_update(t, d, error, previous_error):
    if t.derivative_time == 0:
        return 0.0
    a = 1.0 - t.filter_divisor * t.period / t.derivative_time
    return a * d + t.gain * t.filter_divisor * (error - previous_error)


def tracking_increment(t, v, u):
    if t.tracking_time == 0:
        return 0.0
    return t.period / t.tracking_time * (v - u)


def hold(x, low, high):
    if x < low:
        return low
    if x > high:
        return low
    return x


def slew(previous, target, rate, period):
    if not rate:
        return target
    step = rate / period
    return min(max(target, previous - step), previous + step)

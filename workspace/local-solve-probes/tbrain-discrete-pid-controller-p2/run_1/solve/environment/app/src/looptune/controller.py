"""The controller: one call to ``step`` per sample period."""

from .terms import (
    derivative_update,
    hold,
    integral_increment,
    proportional,
    slew,
    tracking_increment,
)


class Controller:
    def __init__(self, tuning):
        self.tuning = tuning
        self.integral = 0.0
        self._d = 0.0
        self._previous_error = 0.0
        self._previous_output = 0.0
        self._previous_measurement = None
        self._last = None
        self._manual = None
        self._terms = {}

    def step(self, setpoint, measurement, feedforward=0.0):
        t = self.tuning
        r = float(setpoint)
        y = float(measurement)
        f = float(feedforward)
        error = r - y

        first = self._previous_measurement is None
        y_previous = y if first else self._previous_measurement

        p = proportional(t, r, y)
        self._d = derivative_update(t, self._d, error, self._previous_error,
                                    y, y_previous)
        d = self._d

        if self._manual is not None:
            u = self._manual
            self.integral = u - p - d - f
            i = self.integral
            v = u
        else:
            i = self.integral
            v = p + i + d + f
            w = hold(v, t.low, t.high)
            u = slew(self._previous_output, w, t.slew, t.period, first)
            self.integral = (i + integral_increment(t, r, y)
                             + tracking_increment(t, v, u))

        self._previous_error = error
        self._previous_output = u
        self._previous_measurement = y
        self._last = (r, y)
        self._terms = {"p": p, "i": i, "d": d, "f": f, "v": v, "u": u}
        return u

    def terms(self):
        """The pieces of the last step's output."""
        return dict(self._terms)

    def set_manual(self, output):
        self._manual = float(output)

    def set_auto(self):
        self._manual = None

    def retune(self, **changes):
        old = self.tuning
        new = old.with_changes(**changes)
        if self._last is not None and (
            _changed(old.gain, new.gain)
            or _changed(old.setpoint_weight, new.setpoint_weight)
        ):
            r, y = self._last
            self.integral += proportional(old, r, y) - proportional(new, r, y)
        self.tuning = new


def _changed(a, b):
    if a != a and b != b:
        return False
    return a != b

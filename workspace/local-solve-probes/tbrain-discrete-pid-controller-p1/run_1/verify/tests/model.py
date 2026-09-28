"""Expected values for the verifier, worked out from /app/docs/control-note.md.

Nothing here imports or runs the package under repair. Each rule below cites
the section of the note it comes from. Where a rule of the note is written
only for some settings, the other settings fall under the instruction's
silence clause ("what the package does today stands"), and the expression
used there is copied from the shipped helper named in the comment.
"""

DEFAULTS = {
    "gain": 1.0,
    "integral_time": 0.0,
    "derivative_time": 0.0,
    "filter_divisor": 10.0,
    "tracking_time": 0.0,
    "setpoint_weight": 1.0,
    "period": 0.1,
    "low": -1.0,
    "high": 1.0,
    "slew": 0.0,
}


def proportional(t, r, y):
    b = t["setpoint_weight"]
    if 0 <= b <= 1:  # note section 2
        return t["gain"] * (b * r - y)
    # silent: shipped terms.proportional
    return t["gain"] * b * (r - y)


def integral_addition(t, r, y):
    ti = t["integral_time"]
    if ti > 0:  # note section 3
        return t["gain"] * t["period"] / ti * (r - y)
    # silent: shipped terms.integral_increment
    if ti == 0:
        return 0.0
    return t["period"] / ti * (t["setpoint_weight"] * r - y)


def derivative(t, d_before, y, y_previous, e, e_previous):
    td, n, h = t["derivative_time"], t["filter_divisor"], t["period"]
    if td > 0 and n > 0:  # note section 4
        a = td / (td + n * h)
        return a * d_before - t["gain"] * n * a * (y - y_previous)
    # silent: shipped terms.derivative_update (error-driven, forward difference)
    if td == 0:
        return 0.0
    a = 1.0 - n * h / td
    return a * d_before + t["gain"] * n * (e - e_previous)


def held(t, v):
    low, high = t["low"], t["high"]
    if low < high:  # note section 5
        if v < low:
            return low
        if v > high:
            return high
        return v
    return high  # note section 5, limits at or past each other


def slewed(t, previous, w):
    s, h = t["slew"], t["period"]
    if s > 0:  # note section 5
        return min(max(w, previous - s * h), previous + s * h)
    # silent: shipped terms.slew
    if not s:
        return w
    step = s / h
    return min(max(w, previous - step), previous + step)


def tracking_addition(t, v, u):
    tt = t["tracking_time"]
    if tt > 0:  # note section 6
        return t["period"] / tt * (u - v)
    # silent: shipped terms.tracking_increment
    if tt == 0:
        return 0.0
    return t["period"] / tt * (v - u)


class Loop:
    def __init__(self, tuning):
        self.t = dict(DEFAULTS)
        self.t.update({k: float(v) for k, v in tuning.items()})
        self.integral = 0.0
        self.d = 0.0
        self.first = True
        self.y_previous = None
        self.e_previous = 0.0  # the shipped helper's history, used only where the note is silent
        self.u_previous = None
        self.last = None
        self.manual = None
        self.terms = {}

    def step(self, r, y, f=0.0):
        t = self.t
        r, y, f = float(r), float(y), float(f)
        e = r - y
        p = proportional(t, r, y)
        y_prev = y if self.first else self.y_previous
        self.d = derivative(t, self.d, y, y_prev, e, self.e_previous)
        d = self.d
        if self.manual is not None:  # note section 7
            u = self.manual
            self.integral = u - p - d - f
            i = self.integral
            v = u
        else:
            i = self.integral
            v = p + i + d + f
            w = held(t, v)
            u = w if self.first else slewed(t, self.u_previous, w)
            self.integral = i + integral_addition(t, r, y) + tracking_addition(t, v, u)
        self.first = False
        self.y_previous = y
        self.e_previous = e
        self.u_previous = u
        self.last = (r, y)
        self.terms = {"p": p, "i": i, "d": d, "f": f, "v": v, "u": u}
        return u

    def set_manual(self, m):
        self.manual = float(m)

    def set_auto(self):
        self.manual = None

    def retune(self, changes):
        old = dict(self.t)
        new = dict(self.t)
        new.update({k: float(v) for k, v in changes.items()})
        if self.last is not None and ("gain" in changes or "setpoint_weight" in changes):
            r, y = self.last
            self.integral = self.integral + proportional(old, r, y) - proportional(new, r, y)
        self.t = new


def run(tuning, ops):
    """Replay a session. Returns one record per step: u, integral and terms."""
    loop = Loop(tuning)
    out = []
    for op in ops:
        kind = op[0]
        if kind == "step":
            _, r, y, f = op
            u = loop.step(r, y, f)
            out.append({"u": u, "integral": loop.integral, **{"t_" + k: x for k, x in loop.terms.items()}})
        elif kind == "manual":
            loop.set_manual(op[1])
        elif kind == "auto":
            loop.set_auto()
        elif kind == "retune":
            loop.retune(op[1])
        else:
            raise ValueError(kind)
    return out


def closed_loop_ops(tuning, plan, plant):
    """Turn a closed-loop plan into explicit steps.

    The plant (a first-order lag) is driven by the model's own outputs, and the
    measurements it produces are written into the session, so the package under
    test is replayed open-loop on exactly the same measurements.
    """
    loop = Loop(tuning)
    y = plant["y0"]
    ops = []
    for op in plan:
        if op[0] == "hold":
            _, r, f, count = op
            for _ in range(count):
                ops.append(["step", r, y, f])
                u = loop.step(r, y, f)
                y += plant["pole"] * (plant["gain"] * u - y)
        elif op[0] == "manual":
            ops.append(op)
            loop.set_manual(op[1])
        elif op[0] == "auto":
            ops.append(op)
            loop.set_auto()
        elif op[0] == "retune":
            ops.append(op)
            loop.retune(op[1])
    return ops

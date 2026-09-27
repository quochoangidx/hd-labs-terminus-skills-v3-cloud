"""Expected results worked out from /app/docs/stepping-note.md (TS-4).

Nothing here imports or runs the package under repair. Within a stretch where
the heater state does not change, the state x = (T1, T2) obeys x' = A x + c + d t
(section 1, with the ambient's straight line of section 2), whose exact
solution is

    x(t) = e^{At} x0 + t phi1(At) c + t^2 phi2(At) d,
    phi1(z) = (e^z - 1) / z,   phi2(z) = (e^z - 1 - z) / z^2.

A is similar to a symmetric matrix, so its eigenvalues are real; the matrix
functions are formed from them in 60-digit arithmetic, with the one repeated
eigenvalue case (A a multiple of the identity) handled exactly. Switch instants
(section 4) are located by scanning each stretch densely and bisecting the
first bracket to far below the comparison tolerance.
"""

import mpmath as mp

mp.mp.dps = 60
SCAN = 3000


def _phi(k, z):
    if abs(z) < mp.mpf("1e-25"):
        # series: phi_k(z) = sum z^j / (j + k)!
        return sum(z ** j / mp.factorial(j + k) for j in range(6))
    if k == 0:
        return mp.exp(z)
    if k == 1:
        return mp.expm1(z) / z
    return (mp.expm1(z) - z) / (z * z)


class Dynamics:
    """Exact flow of one network with the heater held at a given power."""

    def __init__(self, net):
        c1, c2, g1, g2, g12 = (mp.mpf(repr(float(v))) for v in net)
        self.a = [[-(g1 + g12) / c1, g12 / c1], [g12 / c2, -(g2 + g12) / c2]]
        self.ba = [g1 / c1, g2 / c2]
        self.bp = [1 / c1, mp.mpf(0)]
        a11, a12 = self.a[0]
        a21, a22 = self.a[1]
        tr = a11 + a22
        disc = (a11 - a22) ** 2 + 4 * a12 * a21
        if disc == 0:
            self.lam = None
            self.single = a11
        else:
            root = mp.sqrt(disc)
            self.lam = ((tr + root) / 2, (tr - root) / 2)

    def _fn(self, k, t):
        """phi_k(A t) as a 2x2 list."""
        if self.lam is None:
            v = _phi(k, self.single * t)
            return [[v, mp.mpf(0)], [mp.mpf(0), v]]
        l1, l2 = self.lam
        f1, f2 = _phi(k, l1 * t), _phi(k, l2 * t)
        a = self.a
        out = [[mp.mpf(0)] * 2 for _ in range(2)]
        for i in range(2):
            for j in range(2):
                eye = 1 if i == j else 0
                out[i][j] = (f1 * (a[i][j] - l2 * eye) - f2 * (a[i][j] - l1 * eye)) / (l1 - l2)
        return out

    def state(self, x0, t, a0, slope, power):
        """State after time t from x0, ambient a0 + slope*s, heater power `power`."""
        c = [self.ba[i] * a0 + self.bp[i] * power for i in range(2)]
        d = [self.ba[i] * slope for i in range(2)]
        e0, e1, e2 = self._fn(0, t), self._fn(1, t), self._fn(2, t)
        return [
            sum(e0[i][j] * x0[j] + t * e1[i][j] * c[j] + t * t * e2[i][j] * d[j] for j in range(2))
            for i in range(2)
        ]


def simulate(net, times, ambient, power, t1, t2, heater_on=True, thermostat=None):
    dyn = Dynamics(net)
    times = [mp.mpf(repr(float(v))) for v in times]
    ambient = [mp.mpf(repr(float(v))) for v in ambient]
    power = [mp.mpf(repr(float(v))) for v in power]
    x = [mp.mpf(repr(float(t1))), mp.mpf(repr(float(t2)))]
    on = bool(heater_on)
    if thermostat is not None:
        lower = mp.mpf(repr(float(thermostat[0])))
        upper = mp.mpf(repr(float(thermostat[1])))

    def reached(temp, state):
        return temp >= upper if state else temp <= lower

    switches = []
    if thermostat is not None and reached(x[0], on):
        on = not on
        switches.append((times[0], on))
    temps = [tuple(x)]
    heater = [on]
    for k in range(len(times) - 1):
        start, end = times[k], times[k + 1]
        slope = (ambient[k + 1] - ambient[k]) / (end - start)
        now = start
        while True:
            span = end - now
            a0 = ambient[k] + slope * (now - start)
            q = power[k] if on else mp.mpf(0)
            hit = None
            if thermostat is not None:
                prev = mp.mpf(0)
                for j in range(1, SCAN + 1):
                    tau = span * j / SCAN
                    if reached(dyn.state(x, tau, a0, slope, q)[0], on):
                        lo, hi = prev, tau
                        for _ in range(140):
                            mid = (lo + hi) / 2
                            if reached(dyn.state(x, mid, a0, slope, q)[0], on):
                                hi = mid
                            else:
                                lo = mid
                        hit = hi
                        break
                    prev = tau
            if hit is None:
                x = dyn.state(x, span, a0, slope, q)
                break
            x = dyn.state(x, hit, a0, slope, q)
            now = now + hit
            on = not on
            switches.append((now, on))
            if now >= end:
                break
        temps.append(tuple(x))
        heater.append(on)
    return {
        "temperatures": [[float(a), float(b)] for a, b in temps],
        "heater": heater,
        "switches": [[float(t), s] for t, s in switches],
    }

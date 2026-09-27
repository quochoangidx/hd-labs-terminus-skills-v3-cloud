"""Exact two-body propagation using universal variables.

Solves the universal Kepler equation with Stumpff functions and applies the
Lagrange f and g coefficients.  Works for elliptic, circular, parabolic,
hyperbolic and rectilinear trajectories.  For closed orbits propagated over
many revolutions, the whole number of periods is removed using extended
precision (``decimal``) so that the phase does not accumulate rounding error.
"""

import math
from decimal import Decimal, localcontext

_PI_DEC = Decimal(
    "3.14159265358979323846264338327950288419716939937510582097494459230781640628620899"
)


def _stumpff(z):
    """Return (C(z), S(z))."""
    if abs(z) < 1.0:
        # series: C = sum (-z)^k/(2k+2)!, S = sum (-z)^k/(2k+3)!
        c = 0.0
        s = 0.0
        tc = 0.5
        ts = 1.0 / 6.0
        k = 0
        while True:
            c += tc
            s += ts
            if abs(tc) < 1e-18 * abs(c) and abs(ts) < 1e-18 * abs(s):
                break
            k += 1
            tc *= -z / ((2 * k + 1) * (2 * k + 2))
            ts *= -z / ((2 * k + 2) * (2 * k + 3))
            if k > 40:
                break
        return c, s
    if z > 0:
        sq = math.sqrt(z)
        sh = math.sin(0.5 * sq)
        c = 2.0 * sh * sh / z
        s = (sq - math.sin(sq)) / (sq * z)
        return c, s
    sq = math.sqrt(-z)
    sh = math.sinh(0.5 * sq)
    c = 2.0 * sh * sh / (-z)
    s = (math.sinh(sq) - sq) / (sq * (-z))
    return c, s


def _dec_state(r0, v0, mu):
    """Return (r0 norm, alpha) in Decimal with high precision."""
    rx, ry, rz = (Decimal(x) for x in r0)
    vx, vy, vz = (Decimal(x) for x in v0)
    rn = (rx * rx + ry * ry + rz * rz).sqrt()
    v2 = vx * vx + vy * vy + vz * vz
    alpha = 2 / rn - v2 / Decimal(mu)
    return rn, alpha


def propagate(r0, v0, dt, mu):
    """State ``(r, v)`` after ``dt`` seconds; metres, m/s, mu in m^3/s^2."""
    r0 = tuple(float(x) for x in r0)
    v0 = tuple(float(x) for x in v0)
    dt = float(dt)
    mu = float(mu)

    with localcontext() as ctx:
        ctx.prec = 60
        rn_d, alpha_d = _dec_state(r0, v0, mu)
        rn = float(rn_d)
        alpha = float(alpha_d)
        if dt == 0.0:
            return r0, v0
        if alpha_d > 0:
            # closed orbit: remove whole periods exactly
            period_d = 2 * _PI_DEC / (Decimal(mu).sqrt() * alpha_d * alpha_d.sqrt())
            dt_d = Decimal(dt)
            if abs(dt_d) >= period_d:
                k = int(dt_d / period_d)  # truncation toward zero
                dt = float(dt_d - k * period_d)

    if dt == 0.0:
        return r0, v0

    smu = math.sqrt(mu)
    sigma0 = (r0[0] * v0[0] + r0[1] * v0[1] + r0[2] * v0[2]) / smu
    beta = 1.0 - alpha * rn
    target = smu * dt

    def evaluate(chi):
        z = alpha * chi * chi
        c, s = _stumpff(z)
        chi2 = chi * chi
        f_val = sigma0 * chi2 * c + beta * chi2 * chi * s + rn * chi - target
        r = chi2 * c + sigma0 * chi * (1.0 - z * s) + rn * (1.0 - z * c)
        return f_val, r, c, s, z

    def fval(chi):
        try:
            return evaluate(chi)[0]
        except OverflowError:
            return math.inf if chi > 0 else -math.inf

    # initial guess
    if alpha > 0:
        chi = smu * dt * alpha
        lim = 2.0 * math.pi / math.sqrt(alpha) * 1.0000001
        chi = max(-lim, min(lim, chi))
    else:
        chi = target / rn
        if alpha < 0:
            # hyperbolic starting guess (Vallado)
            sgn = 1.0 if dt > 0 else -1.0
            a_h = 1.0 / alpha
            den = sigma0 * smu + sgn * math.sqrt(-mu * a_h) * beta
            if den != 0.0:
                arg = -2.0 * mu * alpha * dt / den
                if arg > 0.0 and math.isfinite(arg):
                    cand = sgn * math.sqrt(-a_h) * math.log(arg)
                    if math.isfinite(cand) and cand * dt > 0:
                        chi = cand

    # bracket the root (F is monotone increasing in chi)
    f0 = fval(chi)
    if f0 == 0.0:
        lo = hi = chi
    elif f0 < 0:
        lo = chi
        step = max(abs(chi), 1e-3 * abs(target) / rn, 1e-300)
        hi = chi + step
        while fval(hi) < 0:
            lo = hi
            step *= 2.0
            hi = chi + step
    else:
        hi = chi
        step = max(abs(chi), 1e-3 * abs(target) / rn, 1e-300)
        lo = chi - step
        while fval(lo) > 0:
            hi = lo
            step *= 2.0
            lo = chi - step
    if not (lo <= chi <= hi):
        chi = 0.5 * (lo + hi)

    # safeguarded Newton (Newton step, falling back to bisection when the step
    # leaves the bracket or does not shrink fast enough)
    dx_old = hi - lo
    for _ in range(1000):
        try:
            fv, r, c, s, z = evaluate(chi)
        except OverflowError:
            fv, r = (math.inf if chi > 0 else -math.inf), 0.0
        if fv == 0.0:
            break
        if fv < 0:
            lo = chi
        else:
            hi = chi
        new = None
        if r > 0 and math.isfinite(fv) and abs(2.0 * fv) <= abs(dx_old * r):
            cand = chi - fv / r
            if lo < cand < hi:
                new = cand
        if new is None:
            new = 0.5 * (lo + hi)
        dx_old = abs(new - chi)
        if new == chi or abs(new - chi) <= 2e-16 * abs(chi):
            chi = new
            break
        if hi - lo <= 4e-16 * max(abs(lo), abs(hi)):
            chi = new
            break
        chi = new

    z = alpha * chi * chi
    c, s = _stumpff(z)
    chi2 = chi * chi
    r = chi2 * c + sigma0 * chi * (1.0 - z * s) + rn * (1.0 - z * c)
    f = 1.0 - chi2 * c / rn
    g = (rn * chi * (1.0 - z * s) + sigma0 * chi2 * c) / smu
    fdot = smu / (r * rn) * chi * (z * s - 1.0)
    gdot = 1.0 - chi2 * c / r
    pos = tuple(f * r0[i] + g * v0[i] for i in range(3))
    vel = tuple(fdot * r0[i] + gdot * v0[i] for i in range(3))
    return pos, vel

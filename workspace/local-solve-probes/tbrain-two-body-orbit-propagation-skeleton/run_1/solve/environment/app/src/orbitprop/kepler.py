"""Propagate a two-body state with universal variables.

Solves the universal Kepler equation for the universal anomaly ``chi`` using
Stumpff functions and builds the state from Lagrange f and g coefficients.
Handles elliptic, circular, parabolic, hyperbolic and rectilinear (radial)
trajectories, forward and backward in time.

The scalar orbit quantities (1/a, r0.v0, whole-period reduction of ``dt``) are
formed in extended-precision decimal arithmetic so that nearly parabolic orbits
and propagation over many revolutions keep full double precision.
"""

import decimal
import math

_PI_DEC = decimal.Decimal(
    "3.14159265358979323846264338327950288419716939937510582097494459"
)
_CTX = decimal.Context(prec=50, Emax=999999, Emin=-999999)
_LOG_MAX = 700.0  # sinh/cosh overflow guard


def _stumpff(z):
    """Return (C(z), S(z)); z must satisfy the overflow guard."""
    if abs(z) < 0.5:
        # C = sum (-z)^k/(2k+2)!, S = sum (-z)^k/(2k+3)!
        c = 0.0
        s = 0.0
        tc = 0.5
        ts = 1.0 / 6.0
        for k in range(30):
            c += tc
            s += ts
            tc *= -z / ((2 * k + 3) * (2 * k + 4))
            ts *= -z / ((2 * k + 4) * (2 * k + 5))
            if abs(ts) < 1e-19 * s and abs(tc) < 1e-19 * c:
                break
        return c, s
    if z > 0.0:
        x = math.sqrt(z)
        h = math.sin(0.5 * x)
        return 2.0 * h * h / z, (x - math.sin(x)) / (x * z)
    x = math.sqrt(-z)
    h = math.sinh(0.5 * x)
    return 2.0 * h * h / (-z), (math.sinh(x) - x) / (x * (-z))


def _scalars(r0, v0, dt, mu):
    """Return float (rn, sigma0, alpha, beta, dt_reduced) computed precisely."""
    ctx = _CTX
    D = decimal.Decimal
    rx, ry, rz = D(r0[0]), D(r0[1]), D(r0[2])
    vx, vy, vz = D(v0[0]), D(v0[1]), D(v0[2])
    dmu = D(mu)
    r2 = ctx.add(ctx.add(ctx.multiply(rx, rx), ctx.multiply(ry, ry)), ctx.multiply(rz, rz))
    v2 = ctx.add(ctx.add(ctx.multiply(vx, vx), ctx.multiply(vy, vy)), ctx.multiply(vz, vz))
    rv = ctx.add(ctx.add(ctx.multiply(rx, vx), ctx.multiply(ry, vy)), ctx.multiply(rz, vz))
    rn = ctx.sqrt(r2)
    smu = ctx.sqrt(dmu)
    alpha = ctx.subtract(ctx.divide(2, rn), ctx.divide(v2, dmu))
    beta = ctx.subtract(1, ctx.multiply(alpha, rn))
    sigma0 = ctx.divide(rv, smu)
    ddt = D(dt)
    if alpha > 0:
        # Angular momentum squared = r2*v2 - rv^2 (exact enough in decimal).
        h2 = ctx.subtract(ctx.multiply(r2, v2), ctx.multiply(rv, rv))
        if h2 > 0:
            period = ctx.divide(
                ctx.multiply(2, _PI_DEC),
                ctx.multiply(smu, ctx.multiply(alpha, ctx.sqrt(alpha))),
            )
            if ctx.multiply(2, ctx.abs(ddt)) > period:
                k = ctx.to_integral_value(ctx.divide(ddt, period))
                ddt = ctx.subtract(ddt, ctx.multiply(k, period))
    return float(rn), float(smu), float(sigma0), float(alpha), float(beta), float(ddt)


def propagate(r0, v0, dt, mu):
    """State ``(r, v)`` after ``dt`` seconds; metres, m/s, mu in m^3/s^2."""
    r0 = (float(r0[0]), float(r0[1]), float(r0[2]))
    v0 = (float(v0[0]), float(v0[1]), float(v0[2]))
    dt = float(dt)
    mu = float(mu)
    if dt == 0.0:
        return r0, v0
    rn, smu, sigma0, alpha, beta, dt = _scalars(r0, v0, dt, mu)
    if dt == 0.0:
        return r0, v0
    target = smu * dt
    forward = dt > 0.0
    inf = float("inf")

    def kepler(chi):
        chi2 = chi * chi
        z = alpha * chi2
        if z < -_LOG_MAX * _LOG_MAX:
            return (inf if chi > 0 else -inf), inf
        c, s = _stumpff(z)
        f = sigma0 * chi2 * c + beta * chi2 * chi * s + rn * chi - target
        r = chi2 * c + sigma0 * chi * (1.0 - z * s) + rn * (1.0 - z * c)
        return f, r

    # Initial guess.
    if alpha > 0.0:
        guess = target * alpha
    elif alpha < 0.0:
        a = 1.0 / alpha
        sgn = 1.0 if forward else -1.0
        den = sigma0 * smu + sgn * math.sqrt(-mu * a) * (1.0 - rn * alpha)
        arg = (-2.0 * mu * alpha * dt) / den if den != 0.0 else 0.0
        guess = sgn * math.sqrt(-a) * math.log(arg) if arg > 1.0 else target / rn
    else:
        guess = target / rn
    if guess == 0.0 or (guess > 0.0) != forward:
        guess = target / rn
    if guess == 0.0:
        guess = 5e-324 if forward else -5e-324

    # Bracket the root; F is increasing in chi (dF/dchi = r > 0).
    lo = 0.0
    hi = guess
    for _ in range(4000):
        fh = kepler(hi)[0]
        if (fh >= 0.0) == forward:
            break
        lo = hi
        hi *= 2.0
    a_lo, a_hi = (lo, hi) if lo < hi else (hi, lo)
    chi = guess if a_lo < guess < a_hi else 0.5 * (a_lo + a_hi)

    # Safeguarded Newton iteration (bisection whenever Newton leaves the
    # bracket or fails to shrink it fast enough).
    dx_old = a_hi - a_lo
    dx = dx_old
    for _ in range(1000):
        f, r = kepler(chi)
        if f == 0.0:
            break
        if f > 0.0:
            a_hi = chi
        else:
            a_lo = chi
        new = chi - f / r if 0.0 < r < inf else a_lo - 1.0
        if not (a_lo < new < a_hi) or abs(2.0 * (chi - new)) > abs(dx_old):
            dx_old = dx
            new = 0.5 * (a_lo + a_hi)
            dx = a_hi - a_lo
        else:
            dx_old = dx
            dx = chi - new
        if new == chi or abs(new - chi) <= 1e-16 * abs(chi) or new == a_lo or new == a_hi:
            chi = new
            break
        chi = new
    f, r = kepler(chi)
    if 0.0 < r < inf and abs(f / r) <= 1e-12 * abs(chi) + 1e-300:
        chi -= f / r

    chi2 = chi * chi
    z = alpha * chi2
    c, s = _stumpff(z)
    r = chi2 * c + sigma0 * chi * (1.0 - z * s) + rn * (1.0 - z * c)
    ff = 1.0 - chi2 * c / rn
    gg = (rn * chi * (1.0 - z * s) + sigma0 * chi2 * c) / smu
    fd = smu / (r * rn) * chi * (z * s - 1.0)
    gd = 1.0 - chi2 * c / r
    pos = (
        ff * r0[0] + gg * v0[0],
        ff * r0[1] + gg * v0[1],
        ff * r0[2] + gg * v0[2],
    )
    vel = (
        fd * r0[0] + gd * v0[0],
        fd * r0[1] + gd * v0[1],
        fd * r0[2] + gd * v0[2],
    )
    return pos, vel

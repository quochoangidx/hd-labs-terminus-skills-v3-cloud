"""Propagate a two-body state by solving Kepler's equation.

Converts the state to classical elements, advances the mean anomaly and converts
back. Works for closed (elliptic) orbits.
"""

import math


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a):
    return math.sqrt(_dot(a, a))


def propagate(r0, v0, dt, mu):
    """State ``(r, v)`` after ``dt`` seconds; metres, m/s, mu in m^3/s^2."""
    r = _norm(r0)
    v2 = _dot(v0, v0)
    h = _cross(r0, v0)
    energy = v2 / 2 - mu / r
    a = -mu / (2 * energy)
    e_vec = tuple((v2 - mu / r) * r0[i] / mu - _dot(r0, v0) * v0[i] / mu for i in range(3))
    e = _norm(e_vec)
    n = math.sqrt(mu / a ** 3)
    # eccentric anomaly at epoch
    cos_e0 = (1 - r / a) / e
    sin_e0 = _dot(r0, v0) / (e * math.sqrt(mu * a))
    e0 = math.atan2(sin_e0, cos_e0)
    m = e0 - e * math.sin(e0) + n * dt
    big_e = m
    for _ in range(50):
        big_e -= (big_e - e * math.sin(big_e) - m) / (1 - e * math.cos(big_e))
    # perifocal frame
    p_hat = tuple(c / e for c in e_vec)
    h_hat = tuple(c / _norm(h) for c in h)
    q_hat = _cross(h_hat, p_hat)
    b = a * math.sqrt(1 - e * e)
    x = a * (math.cos(big_e) - e)
    y = b * math.sin(big_e)
    rr = a * (1 - e * math.cos(big_e))
    vx = -math.sqrt(mu * a) / rr * math.sin(big_e)
    vy = math.sqrt(mu * a) / rr * math.sqrt(1 - e * e) * math.cos(big_e)
    pos = tuple(x * p_hat[i] + y * q_hat[i] for i in range(3))
    vel = tuple(vx * p_hat[i] + vy * q_hat[i] for i in range(3))
    return pos, vel

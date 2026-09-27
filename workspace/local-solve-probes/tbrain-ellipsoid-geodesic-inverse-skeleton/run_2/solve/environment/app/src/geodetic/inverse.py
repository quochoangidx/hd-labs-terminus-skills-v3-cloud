"""The inverse geodesic problem: distance and azimuths between two points.

Karney, "Algorithms for geodesics", J. Geodesy 87, 43-55 (2013): series
expansions to sixth order in the third flattening, Newton's method on the
azimuth at the first point with a bisection safeguard, and an astroid-based
starting guess for nearly antipodal points. Accurate to about 15 nm on WGS84
and converges for every pair of points.
"""

import math
import sys

from geodetic.ellipsoid import FLATTENING as _F
from geodetic.ellipsoid import SEMI_MAJOR_AXIS as _A

_NA1 = _NC1 = _NA2 = _NC2 = _NA3 = _NC3 = _NC4 = 6
_NA3X = _NA3
_NC3X = (_NC3 * (_NC3 - 1)) // 2

_DIGITS = 53
_TOL0 = sys.float_info.epsilon
_TINY = math.sqrt(sys.float_info.min)
_TOL1 = 200 * _TOL0
_TOL2 = math.sqrt(_TOL0)
_TOLB = _TOL0 * _TOL2
_XTHRESH = 1000 * _TOL2
_MAXIT1 = 20
_MAXIT2 = _MAXIT1 + _DIGITS + 10


def _sq(x):
    return x * x


def _cbrt(x):
    y = abs(x) ** (1 / 3.0)
    return y if x >= 0 else -y


def _norm(x, y):
    r = math.hypot(x, y)
    return x / r, y / r


def _sum(u, v):
    s = u + v
    up = s - v
    vpp = s - up
    up -= u
    vpp -= v
    t = -(up + vpp) if s != 0 else s
    return s, t


def _polyval(n, p, s, x):
    y = p[s] if n >= 0 else 0.0
    while n > 0:
        n -= 1
        s += 1
        y = y * x + p[s]
    return y


def _ang_round(x):
    z = 1 / 16.0
    y = abs(x)
    w = z - y
    y = z - w if w > 0 else y
    return math.copysign(y, x)


def _remainder360(x):
    return math.remainder(x, 360.0)


def _ang_diff(x, y):
    d, t = _sum(_remainder360(-x), _remainder360(y))
    d, t2 = _sum(_remainder360(d), t)
    if d == 0 or abs(d) == 180:
        d = math.copysign(d, (y - x) if t2 == 0 else -t2)
    return d, t2


def _sincosd(x):
    r = math.fmod(x, 360.0)
    q = 0 if math.isnan(r) else int(round(r / 90))
    r -= 90 * q
    r = math.radians(r)
    s = math.sin(r)
    c = math.cos(r)
    q = q % 4
    if q == 1:
        s, c = c, -s
    elif q == 2:
        s, c = -s, -c
    elif q == 3:
        s, c = -c, s
    c = c + 0.0
    if s == 0:
        s = math.copysign(s, x)
    return s, c


def _atan2d(y, x):
    if abs(y) > abs(x):
        q = 2
        x, y = y, x
    else:
        q = 0
    if x < 0:
        q += 1
        x = -x
    ang = math.degrees(math.atan2(y, x))
    if q == 1:
        ang = (180 if y >= 0 else -180) - ang
    elif q == 2:
        ang = 90 - ang
    elif q == 3:
        ang = -90 + ang
    return ang


def _sin_cos_series(sinp, sinx, cosx, c):
    k = len(c)
    n = k - (1 if sinp else 0)
    ar = 2 * (cosx - sinx) * (cosx + sinx)
    y1 = 0.0
    if n & 1:
        k -= 1
        y0 = c[k]
    else:
        y0 = 0.0
    n = n // 2
    while n:
        n -= 1
        k -= 1
        y1 = ar * y0 - y1 + c[k]
        k -= 1
        y0 = ar * y1 - y0 + c[k]
    return 2 * sinx * cosx * y0 if sinp else cosx * (y0 - y1)


def _a1m1f(eps):
    coeff = [1, 4, 64, 0, 256]
    m = _NA1 // 2
    t = _polyval(m, coeff, 0, _sq(eps)) / coeff[m + 1]
    return (t + eps) / (1 - eps)


def _c1f(eps, c):
    coeff = [
        -1, 6, -16, 32,
        -9, 64, -128, 2048,
        9, -16, 768,
        3, -5, 512,
        -7, 1280,
        -7, 2048,
    ]
    eps2 = _sq(eps)
    d = eps
    o = 0
    for l in range(1, _NC1 + 1):
        m = (_NC1 - l) // 2
        c[l] = d * _polyval(m, coeff, o, eps2) / coeff[o + m + 1]
        o += m + 2
        d *= eps


def _a2m1f(eps):
    coeff = [-11, -28, -192, 0, 256]
    m = _NA2 // 2
    t = _polyval(m, coeff, 0, _sq(eps)) / coeff[m + 1]
    return (t - eps) / (1 + eps)


def _c2f(eps, c):
    coeff = [
        1, 2, 16, 32,
        35, 64, 384, 2048,
        15, 80, 768,
        7, 35, 512,
        63, 1280,
        77, 2048,
    ]
    eps2 = _sq(eps)
    d = eps
    o = 0
    for l in range(1, _NC2 + 1):
        m = (_NC2 - l) // 2
        c[l] = d * _polyval(m, coeff, o, eps2) / coeff[o + m + 1]
        o += m + 2
        d *= eps


class _Ellipsoid:
    def __init__(self, a, f):
        self.a = float(a)
        self.f = float(f)
        self.f1 = 1 - self.f
        self.e2 = self.f * (2 - self.f)
        self.ep2 = self.e2 / _sq(self.f1)
        self.n = self.f / (2 - self.f)
        self.b = self.a * self.f1
        self.etol2 = 0.1 * _TOL2 / math.sqrt(
            max(0.001, abs(self.f)) * min(1.0, 1 - self.f / 2) / 2
        )
        self.A3x = [0.0] * _NA3X
        self.C3x = [0.0] * _NC3X
        self._a3coeff()
        self._c3coeff()

    def _a3coeff(self):
        coeff = [
            -3, 128,
            -2, -3, 64,
            -1, -3, -1, 16,
            3, -1, -2, 8,
            1, -1, 2,
            1, 1,
        ]
        o = k = 0
        for j in range(_NA3 - 1, -1, -1):
            m = min(_NA3 - j - 1, j)
            self.A3x[k] = _polyval(m, coeff, o, self.n) / coeff[o + m + 1]
            k += 1
            o += m + 2

    def _c3coeff(self):
        coeff = [
            3, 128,
            2, 5, 128,
            -1, 3, 3, 64,
            -1, 0, 1, 8,
            -1, 1, 4,
            5, 256,
            1, 3, 128,
            -3, -2, 3, 64,
            1, -3, 2, 32,
            7, 512,
            -10, 9, 384,
            5, -9, 5, 192,
            7, 512,
            -14, 7, 512,
            21, 2560,
        ]
        o = k = 0
        for l in range(1, _NC3):
            for j in range(_NC3 - 1, l - 1, -1):
                m = min(_NC3 - j - 1, j)
                self.C3x[k] = _polyval(m, coeff, o, self.n) / coeff[o + m + 1]
                k += 1
                o += m + 2

    def _a3f(self, eps):
        return _polyval(_NA3 - 1, self.A3x, 0, eps)

    def _c3f(self, eps, c):
        mult = 1.0
        o = 0
        for l in range(1, _NC3):
            m = _NC3 - l - 1
            mult *= eps
            c[l] = mult * _polyval(m, self.C3x, o, eps)
            o += m + 1

    def _lengths(self, eps, sig12, ssig1, csig1, dn1, ssig2, csig2, dn2,
                 cbet1, cbet2, C1a, C2a):
        """Return (s12b, m12b) in units of b."""
        A1 = _a1m1f(eps)
        _c1f(eps, C1a)
        A2 = _a2m1f(eps)
        _c2f(eps, C2a)
        m0x = A1 - A2
        A2 = 1 + A2
        A1 = 1 + A1
        B1 = (_sin_cos_series(True, ssig2, csig2, C1a)
              - _sin_cos_series(True, ssig1, csig1, C1a))
        s12b = A1 * (sig12 + B1)
        B2 = (_sin_cos_series(True, ssig2, csig2, C2a)
              - _sin_cos_series(True, ssig1, csig1, C2a))
        J12 = m0x * sig12 + (A1 * B1 - A2 * B2)
        m12b = dn2 * (csig1 * ssig2) - dn1 * (ssig1 * csig2) - csig1 * csig2 * J12
        return s12b, m12b

    @staticmethod
    def _astroid(x, y):
        p = _sq(x)
        q = _sq(y)
        r = (p + q - 1) / 6
        if not (q == 0 and r <= 0):
            S = p * q / 4
            r2 = _sq(r)
            r3 = r * r2
            disc = S * (S + 2 * r3)
            u = r
            if disc >= 0:
                T3 = S + r3
                T3 += -math.sqrt(disc) if T3 < 0 else math.sqrt(disc)
                T = _cbrt(T3)
                u += T + (r2 / T if T != 0 else 0)
            else:
                ang = math.atan2(math.sqrt(-disc), -(S + r3))
                u += 2 * r * math.cos(ang / 3)
            v = math.sqrt(_sq(u) + q)
            uv = q / (v - u) if u < 0 else u + v
            w = (uv - q) / (2 * v)
            k = uv / (math.sqrt(uv + _sq(w)) + w)
        else:
            k = 0.0
        return k

    def _inverse_start(self, sbet1, cbet1, dn1, sbet2, cbet2, dn2,
                       lam12, slam12, clam12, C1a, C2a):
        f = self.f
        sig12 = -1.0
        salp2 = calp2 = dnm = math.nan
        sbet12 = sbet2 * cbet1 - cbet2 * sbet1
        cbet12 = cbet2 * cbet1 + sbet2 * sbet1
        sbet12a = sbet2 * cbet1 + cbet2 * sbet1
        shortline = cbet12 >= 0 and sbet12 < 0.5 and cbet2 * lam12 < 0.5
        if shortline:
            sbetm2 = _sq(sbet1 + sbet2)
            sbetm2 /= sbetm2 + _sq(cbet1 + cbet2)
            dnm = math.sqrt(1 + self.ep2 * sbetm2)
            omg12 = lam12 / (self.f1 * dnm)
            somg12 = math.sin(omg12)
            comg12 = math.cos(omg12)
        else:
            somg12 = slam12
            comg12 = clam12

        salp1 = cbet2 * somg12
        if comg12 >= 0:
            calp1 = sbet12 + cbet2 * sbet1 * _sq(somg12) / (1 + comg12)
        else:
            calp1 = sbet12a - cbet2 * sbet1 * _sq(somg12) / (1 - comg12)

        ssig12 = math.hypot(salp1, calp1)
        csig12 = sbet1 * sbet2 + cbet1 * cbet2 * comg12

        if shortline and ssig12 < self.etol2:
            salp2 = cbet1 * somg12
            calp2 = sbet12 - cbet1 * sbet2 * (
                _sq(somg12) / (1 + comg12) if comg12 >= 0 else 1 - comg12)
            salp2, calp2 = _norm(salp2, calp2)
            sig12 = math.atan2(ssig12, csig12)
        elif (abs(self.n) > 0.1 or csig12 >= 0
              or ssig12 >= 6 * abs(self.n) * math.pi * _sq(cbet1)):
            pass
        else:
            # Nearly antipodal: f >= 0 branch (WGS84 is oblate).
            lam12x = math.atan2(-slam12, -clam12)
            k2 = _sq(sbet1) * self.ep2
            eps = k2 / (2 * (1 + math.sqrt(1 + k2)) + k2)
            lamscale = f * cbet1 * self._a3f(eps) * math.pi
            betscale = lamscale * cbet1
            x = lam12x / lamscale
            y = sbet12a / betscale
            if y > -_TOL1 and x > -1 - _XTHRESH:
                salp1 = min(1.0, -x)
                calp1 = -math.sqrt(1 - _sq(salp1))
            else:
                k = self._astroid(x, y)
                omg12a = lamscale * (-x * k / (1 + k))
                somg12 = math.sin(omg12a)
                comg12 = -math.cos(omg12a)
                salp1 = cbet2 * somg12
                calp1 = sbet12a - cbet2 * sbet1 * _sq(somg12) / (1 - comg12)

        if not (salp1 <= 0):
            salp1, calp1 = _norm(salp1, calp1)
        else:
            salp1 = 1.0
            calp1 = 0.0
        return sig12, salp1, calp1, salp2, calp2, dnm

    def _lambda12(self, sbet1, cbet1, dn1, sbet2, cbet2, dn2, salp1, calp1,
                  slam120, clam120, diffp, C1a, C2a, C3a):
        if sbet1 == 0 and calp1 == 0:
            calp1 = -_TINY
        salp0 = salp1 * cbet1
        calp0 = math.hypot(calp1, salp1 * sbet1)

        ssig1 = sbet1
        somg1 = salp0 * sbet1
        csig1 = comg1 = calp1 * cbet1
        ssig1, csig1 = _norm(ssig1, csig1)

        salp2 = salp0 / cbet2 if cbet2 != cbet1 else salp1
        if cbet2 != cbet1 or abs(sbet2) != -sbet1:
            calp2 = math.sqrt(
                _sq(calp1 * cbet1)
                + ((cbet2 - cbet1) * (cbet1 + cbet2) if cbet1 < -sbet1
                   else (sbet1 - sbet2) * (sbet1 + sbet2))
            ) / cbet2
        else:
            calp2 = abs(calp1)

        ssig2 = sbet2
        somg2 = salp0 * sbet2
        csig2 = comg2 = calp2 * cbet2
        ssig2, csig2 = _norm(ssig2, csig2)

        sig12 = math.atan2(max(0.0, csig1 * ssig2 - ssig1 * csig2),
                           csig1 * csig2 + ssig1 * ssig2)
        somg12 = max(0.0, comg1 * somg2 - somg1 * comg2)
        comg12 = comg1 * comg2 + somg1 * somg2
        eta = math.atan2(somg12 * clam120 - comg12 * slam120,
                         comg12 * clam120 + somg12 * slam120)
        k2 = _sq(calp0) * self.ep2
        eps = k2 / (2 * (1 + math.sqrt(1 + k2)) + k2)
        self._c3f(eps, C3a)
        B312 = (_sin_cos_series(True, ssig2, csig2, C3a)
                - _sin_cos_series(True, ssig1, csig1, C3a))
        domg12 = -self.f * self._a3f(eps) * salp0 * (sig12 + B312)
        lam12 = eta + domg12

        if diffp:
            if calp2 == 0:
                dlam12 = -2 * self.f1 * dn1 / sbet1
            else:
                _, dlam12 = self._lengths(eps, sig12, ssig1, csig1, dn1,
                                          ssig2, csig2, dn2, cbet1, cbet2,
                                          C1a, C2a)
                dlam12 *= self.f1 / (calp2 * cbet2)
        else:
            dlam12 = math.nan

        return (lam12, salp2, calp2, sig12, ssig1, csig1, ssig2, csig2,
                eps, domg12, dlam12)

    def inverse(self, lat1, lon1, lat2, lon2):
        f, f1, b = self.f, self.f1, self.b

        lon12, lon12s = _ang_diff(lon1, lon2)
        lonsign = math.copysign(1, lon12)
        lon12 = lonsign * _ang_round(lon12)
        lon12s = _ang_round((180 - lon12) - lonsign * lon12s)
        lam12 = math.radians(lon12)
        if lon12 > 90:
            slam12, clam12 = _sincosd(lon12s)
            clam12 = -clam12
        else:
            slam12, clam12 = _sincosd(lon12)

        lat1 = _ang_round(lat1)
        lat2 = _ang_round(lat2)
        swapp = -1 if abs(lat1) < abs(lat2) else 1
        if swapp < 0:
            lonsign *= -1
            lat2, lat1 = lat1, lat2
        latsign = math.copysign(1, -lat1)
        lat1 *= latsign
        lat2 *= latsign

        sbet1, cbet1 = _sincosd(lat1)
        sbet1 *= f1
        sbet1, cbet1 = _norm(sbet1, cbet1)
        cbet1 = max(_TINY, cbet1)

        sbet2, cbet2 = _sincosd(lat2)
        sbet2 *= f1
        sbet2, cbet2 = _norm(sbet2, cbet2)
        cbet2 = max(_TINY, cbet2)

        if cbet1 < -sbet1:
            if cbet2 == cbet1:
                sbet2 = math.copysign(sbet1, sbet2)
        else:
            if abs(sbet2) == -sbet1:
                cbet2 = cbet1

        dn1 = math.sqrt(1 + self.ep2 * _sq(sbet1))
        dn2 = math.sqrt(1 + self.ep2 * _sq(sbet2))

        C1a = [0.0] * (_NC1 + 1)
        C2a = [0.0] * (_NC2 + 1)
        C3a = [0.0] * _NC3

        meridian = lat1 == -90 or slam12 == 0
        s12x = 0.0
        if meridian:
            calp1 = clam12
            salp1 = slam12
            calp2 = 1.0
            salp2 = 0.0
            ssig1 = sbet1
            csig1 = calp1 * cbet1
            ssig2 = sbet2
            csig2 = calp2 * cbet2
            sig12 = math.atan2(max(0.0, csig1 * ssig2 - ssig1 * csig2),
                               csig1 * csig2 + ssig1 * ssig2)
            s12x, m12x = self._lengths(self.n, sig12, ssig1, csig1, dn1,
                                       ssig2, csig2, dn2, cbet1, cbet2,
                                       C1a, C2a)
            if sig12 < 1 or m12x >= 0:
                if sig12 < 3 * _TINY or (sig12 < _TOL0 and (s12x < 0 or m12x < 0)):
                    sig12 = m12x = s12x = 0.0
                s12x *= b
            else:
                meridian = False

        if not meridian and sbet1 == 0 and (f <= 0 or lon12s >= f * 180):
            # Along the equator.
            calp1 = calp2 = 0.0
            salp1 = salp2 = 1.0
            s12x = self.a * lam12
        elif not meridian:
            sig12, salp1, calp1, salp2, calp2, dnm = self._inverse_start(
                sbet1, cbet1, dn1, sbet2, cbet2, dn2, lam12, slam12, clam12,
                C1a, C2a)
            if sig12 >= 0:
                s12x = sig12 * b * dnm
            else:
                numit = 0
                tripn = tripb = False
                salp1a = _TINY
                calp1a = 1.0
                salp1b = _TINY
                calp1b = -1.0
                while numit < _MAXIT2:
                    (v, salp2, calp2, sig12, ssig1, csig1, ssig2, csig2,
                     eps, domg12, dv) = self._lambda12(
                        sbet1, cbet1, dn1, sbet2, cbet2, dn2, salp1, calp1,
                        slam12, clam12, numit < _MAXIT1, C1a, C2a, C3a)
                    if tripb or not (abs(v) >= (8 if tripn else 1) * _TOL0):
                        break
                    if v > 0 and (numit > _MAXIT1 or calp1 / salp1 > calp1b / salp1b):
                        salp1b = salp1
                        calp1b = calp1
                    elif v < 0 and (numit > _MAXIT1 or calp1 / salp1 < calp1a / salp1a):
                        salp1a = salp1
                        calp1a = calp1
                    numit += 1
                    if numit < _MAXIT1 and dv > 0:
                        dalp1 = -v / dv
                        if abs(dalp1) < math.pi:
                            sdalp1 = math.sin(dalp1)
                            cdalp1 = math.cos(dalp1)
                            nsalp1 = salp1 * cdalp1 + calp1 * sdalp1
                            if nsalp1 > 0:
                                calp1 = calp1 * cdalp1 - salp1 * sdalp1
                                salp1 = nsalp1
                                salp1, calp1 = _norm(salp1, calp1)
                                tripn = abs(v) <= 16 * _TOL0
                                continue
                    salp1 = (salp1a + salp1b) / 2
                    calp1 = (calp1a + calp1b) / 2
                    salp1, calp1 = _norm(salp1, calp1)
                    tripn = False
                    tripb = (abs(salp1a - salp1) + (calp1a - calp1) < _TOLB
                             or abs(salp1 - salp1b) + (calp1 - calp1b) < _TOLB)
                s12x, _ = self._lengths(eps, sig12, ssig1, csig1, dn1,
                                        ssig2, csig2, dn2, cbet1, cbet2,
                                        C1a, C2a)
                s12x *= b

        s12 = 0.0 + s12x

        if swapp < 0:
            salp2, salp1 = salp1, salp2
            calp2, calp1 = calp1, calp2
        salp1 *= swapp * lonsign
        calp1 *= swapp * latsign
        salp2 *= swapp * lonsign
        calp2 *= swapp * latsign

        azi1 = _atan2d(salp1, calp1)
        azi2 = _atan2d(salp2, calp2)
        return s12, azi1, azi2


_WGS84 = _Ellipsoid(_A, _F)


def inverse(lat1, lon1, lat2, lon2):
    """``(s12, azi1, azi2)``: metres, and degrees clockwise from north.

    ``azi2`` is the forward azimuth at the second point.
    """
    return _WGS84.inverse(float(lat1), float(lon1), float(lat2), float(lon2))

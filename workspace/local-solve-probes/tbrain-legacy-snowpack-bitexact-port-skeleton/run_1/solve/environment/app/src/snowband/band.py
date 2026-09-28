"""SNOWIN and SNOWPK from legacy/snowpk.f.

One SnowBand is one elevation band run from its start: the constructor is
SNOWIN, day() is one call of SNOWPK, and the attributes we, liqw, heat, kdays
and bal are COMMON /PACK/ after the latest call.

Typing follows the Fortran implicit rules: LIQW, KDAYS, NWARM, ITSUM, ITAVG,
MID, K, NHR and IWE are 32-bit INTEGER; WE, HEAT, OUT, DMTOT, FRTOT and the
band constants are 32-bit REAL; BAL is DOUBLE PRECISION.  Every REAL
operation is done in double and rounded once to single, which is exact for
+, -, *, / and SQRT (53 >= 2*24 + 2).
"""

import math
import struct

_PACK_F = struct.Struct("<f")
_INT_MIN = -(2 ** 31)
_INT_MAX = 2 ** 31 - 1


def _f32(x):
    """Round a Python float to the nearest IEEE single (ties to even)."""
    try:
        return _PACK_F.unpack(_PACK_F.pack(x))[0]
    except OverflowError:
        return math.copysign(math.inf, x)


def _i32(n):
    """Wrap a Python int to 32-bit two's complement."""
    n &= 0xFFFFFFFF
    return n - 0x100000000 if n & 0x80000000 else n


def _real(n):
    """INTEGER -> REAL conversion (FLOAT / mixed-mode promotion)."""
    return _f32(float(n))


def _int(x):
    """REAL -> INTEGER conversion by truncation (assignment / INT)."""
    if math.isnan(x) or math.isinf(x):
        return _INT_MIN
    t = math.trunc(x)
    if t < _INT_MIN or t > _INT_MAX:
        return _INT_MIN
    return t


def _nint(x):
    """NINT: nearest integer, halves rounded away from zero."""
    if math.isnan(x) or math.isinf(x):
        return _INT_MIN
    t = math.trunc(x)
    frac = x - t  # exact in double
    if frac >= 0.5:
        t += 1
    elif frac <= -0.5:
        t -= 1
    if t < _INT_MIN or t > _INT_MAX:
        return _INT_MIN
    return t


def _amin1(a, b):
    """AMIN1(A, B) as gfortran evaluates it (first argument unless B < A)."""
    return b if b < a else a


def _dim(x, y):
    """DIM(X, Y) = X - Y if positive, else zero."""
    d = _f32(x - y)
    return d if d > 0.0 else 0.0


def _sqrt(x):
    if x < 0.0 or math.isnan(x):
        return math.nan
    return _f32(math.sqrt(x))


# Band constants, as REAL literals.
_PXTEMP = _f32(1.0)
_TBASE = _f32(0.0)
_CMELT = _f32(0.15)
_REFRZ = _f32(0.0025)
_HOLD = _f32(0.04)
_TIPM = _f32(0.2)


class SnowBand:
    def __init__(self, we0):
        # SAVEd locals of SNOWPK: a fresh program per band.
        self._totout = 0.0
        self._nwarm = 0
        # SNOWIN(WE0)
        self.we = _f32(float(we0))
        self.liqw = 0
        self.heat = 0.0
        self.kdays = 0
        self.bal = 0.0

    def day(self, px, ta):
        """One call of SNOWPK with PX = px and TA = ta (NHR = len(ta)).

        Returns (outflw, iwe, nhr, itavg, dmtot, frtot), nhr being NHR as
        SNOWPK leaves it.
        """
        ta = [_f32(float(v)) for v in ta]
        px = [_f32(float(v)) for v in px]
        nhr = len(ta)

        we = self.we
        liqw = self.liqw
        heat = self.heat
        bal = self.bal

        # Daily mean temperature in tenths, midpoint hour.
        itsum = 0
        for k in range(nhr):
            itsum = _i32(itsum + _nint(_f32(ta[k] * 10.0)))
        q = abs(itsum) // nhr
        itavg = q if itsum >= 0 else -q
        mid = (nhr + 1) // 2

        if itavg > 0:
            self._nwarm = _i32(self._nwarm + 1)
        nw10 = abs(self._nwarm) // 10
        if self._nwarm < 0:
            nw10 = -nw10
        fmelt = _f32(_CMELT * _f32(1.0 + _f32(_real(nw10) * 0.25)))

        out = 0.0
        dmtot = 0.0
        frtot = 0.0
        k = 1
        while k <= nhr:
            t = ta[k - 1]
            p = px[k - 1] if k - 1 < len(px) else 0.0
            if t < -90.0:
                break
            if _f32(t - _PXTEMP) <= 0.0:
                we = _f32(we + p)
            else:
                liqw = _int(_f32(_real(liqw) + p))
            w = _TIPM
            if k == mid:
                w = _f32(_TIPM * 2.0)
            heat = _f32(heat + _f32(w * _f32(t - heat)))
            if t > _TBASE:
                dmelt = _f32(_f32(fmelt * _f32(t - _TBASE)) / 24.0)
                dmelt = _amin1(dmelt, we)
                we = _f32(we - dmelt)
                liqw = _int(_f32(_real(liqw) + dmelt))
                dmtot = _f32(dmtot + dmelt)
            else:
                frz = _f32(_f32(_REFRZ * _dim(_TBASE, heat))
                           * _sqrt(_f32(_real(liqw) + 1.0)))
                frz = _amin1(frz, _real(liqw))
                liqw = _int(_f32(_real(liqw) - frz))
                we = _f32(we + frz)
                frtot = _f32(frtot + frz)
            cap = _f32(_HOLD * we)
            if _real(liqw) > cap:
                out = _f32(out + _f32(_real(liqw) - cap))
                liqw = _int(cap)
            bal = (bal + p) - out
            k += 1
        nhr = k - 1

        outflw = out
        self._totout = _f32(self._totout + out)
        self.kdays = _i32(self.kdays + 1)
        iwe = _nint(_f32(we * 100.0))

        self.we = we
        self.liqw = liqw
        self.heat = heat
        self.bal = bal
        return (outflw, iwe, nhr, itavg, dmtot, frtot)

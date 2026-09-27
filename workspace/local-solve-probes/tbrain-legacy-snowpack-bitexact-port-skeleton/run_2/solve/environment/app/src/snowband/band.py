"""SNOWIN and SNOWPK from legacy/snowpk.f.

One SnowBand is one elevation band run from its start: the constructor is
SNOWIN, day() is one call of SNOWPK, and the attributes we, liqw, heat, kdays
and bal are COMMON /PACK/ after the latest call.

Arithmetic model (gfortran -O0 -ffp-contract=off, x86-64 SSE):
  * REAL is IEEE binary32; every operation is rounded once to binary32.  The
    exact binary64 result of +, -, *, / or sqrt on binary32 operands, rounded
    to binary32, equals the correctly rounded binary32 result (53 >= 2*24+2),
    so each operation is computed in Python floats and then rounded.
  * Implicit typing: LIQW, KDAYS, NWARM, ITSUM, ITAVG, MID, K are INTEGER;
    everything else not declared is REAL; BAL is DOUBLE PRECISION.
  * REAL -> INTEGER assignment truncates toward zero; NINT rounds half away
    from zero; integer division truncates toward zero.
"""

import math
import struct

_PACK_F = struct.Struct("<f")


def _f32(x):
    """Round a Python float to the nearest binary32 value (ties to even)."""
    try:
        return _PACK_F.unpack(_PACK_F.pack(x))[0]
    except OverflowError:
        return math.copysign(math.inf, x)


def _i32(n):
    """Wrap to a 32-bit two's complement INTEGER."""
    n &= 0xFFFFFFFF
    return n - 0x100000000 if n & 0x80000000 else n


def _ftoi(x):
    """REAL -> INTEGER conversion (truncation, cvttss2si)."""
    if math.isnan(x) or math.isinf(x) or not (-2147483648.0 <= x < 2147483648.0):
        return -2147483648
    return int(math.trunc(x))


def _nint(x):
    """Fortran NINT of a REAL: nearest integer, halves away from zero."""
    if math.isnan(x) or math.isinf(x):
        return -2147483648
    a = abs(x)
    if a >= 8388608.0:  # binary32 values this large are already integral
        r = a
    else:
        r = math.floor(a + 0.5)  # exact in binary64 for |x| < 2**23
    r = int(r)
    if x < 0:
        r = -r
    if not (-2147483648 <= r <= 2147483647):
        return -2147483648
    return r


def _itof(n):
    """FLOAT(INTEGER) -> REAL."""
    return _f32(float(n))


def _idiv(a, b):
    """Fortran INTEGER division (truncation toward zero)."""
    q = abs(a) // abs(b)
    return _i32(q if (a >= 0) == (b >= 0) else -q)


def _amin1(a, b):
    """AMIN1(A, B): keep A unless B is smaller."""
    return b if b < a else a


def _sqrt(x):
    """SQRT of a REAL (NaN for negative arguments, as the hardware gives)."""
    if x < 0.0 or math.isnan(x):
        return math.nan
    return math.sqrt(x)


def _dim(x, y):
    """DIM(X, Y) for REAL."""
    return _f32(x - y) if x > y else 0.0


# Band constants (REAL literals).
_PXTEMP = _f32(1.0)
_TBASE = _f32(0.0)
_CMELT = _f32(0.15)
_REFRZ = _f32(0.0025)
_HOLD = _f32(0.04)
_TIPM = _f32(0.2)
_TEN = _f32(10.0)
_HUNDRED = _f32(100.0)
_ONE = _f32(1.0)
_QUARTER = _f32(0.25)
_TWO = _f32(2.0)
_MISSING = _f32(-90.0)


class SnowBand:
    def __init__(self, we0):
        # SNOWIN(WE0); each band is a fresh program, so SAVEd locals restart.
        self.we = _f32(float(we0))
        self.liqw = 0
        self.heat = 0.0
        self.kdays = 0
        self.bal = 0.0
        self._totout = 0.0
        self._nwarm = 0

    def day(self, px, ta):
        """One call of SNOWPK with PX = px and TA = ta (NHR = len(ta)).

        Returns (outflw, iwe, nhr, itavg, dmtot, frtot), nhr being NHR as
        SNOWPK leaves it.
        """
        f = _f32
        px = [f(float(v)) for v in px]
        ta = [f(float(v)) for v in ta]
        nhr = len(ta)

        we = self.we
        liqw = self.liqw
        heat = self.heat
        bal = self.bal

        # Daily mean temperature in tenths, from rounded hourly values.
        itsum = 0
        for k in range(nhr):
            itsum = _i32(itsum + _nint(f(ta[k] * _TEN)))
        itavg = _idiv(itsum, nhr)
        mid = _idiv(nhr + 1, 2)

        if itavg > 0:
            self._nwarm = _i32(self._nwarm + 1)
        fmelt = f(_CMELT * f(_ONE + f(_itof(_idiv(self._nwarm, 10)) * _QUARTER)))

        out = 0.0
        dmtot = 0.0
        frtot = 0.0
        k = 1
        while k <= nhr:
            t = ta[k - 1]
            p = px[k - 1]
            if t < _MISSING:
                break
            if f(t - _PXTEMP) <= 0.0:
                we = f(we + p)
            else:
                liqw = _ftoi(f(_itof(liqw) + p))
            w = _TIPM
            if k == mid:
                w = f(_TIPM * _TWO)
            heat = f(heat + f(w * f(t - heat)))
            if t > _TBASE:
                dmelt = f(f(fmelt * f(t - _TBASE)) / _itof(24))
                dmelt = _amin1(dmelt, we)
                we = f(we - dmelt)
                liqw = _ftoi(f(_itof(liqw) + dmelt))
                dmtot = f(dmtot + dmelt)
            else:
                frz = f(f(_REFRZ * _dim(_TBASE, heat))
                        * f(_sqrt(f(_itof(liqw) + _ONE))))
                frz = _amin1(frz, _itof(liqw))
                liqw = _ftoi(f(_itof(liqw) - frz))
                we = f(we + frz)
                frtot = f(frtot + frz)
            cap = f(_HOLD * we)
            if _itof(liqw) > cap:
                out = f(out + f(_itof(liqw) - cap))
                liqw = _ftoi(cap)
            bal = (bal + p) - out
            k += 1
        nhr = k - 1

        outflw = out
        self._totout = f(self._totout + out)
        self.kdays = _i32(self.kdays + 1)
        iwe = _nint(f(we * _HUNDRED))

        self.we = we
        self.liqw = liqw
        self.heat = heat
        self.bal = bal
        return (outflw, iwe, nhr, itavg, dmtot, frtot)

"""BANDIN and BANDDY from legacy/bandmd.f.

A Band is one band's program run: the constructor calls BANDIN, day() is one
call of BANDDY, and the attributes hold the common blocks after the latest
call.

Every REAL value is kept as a Python float holding an exact IEEE-754 single
precision value; every REAL operation is done in double and rounded once to
single (double rounding is harmless for +, -, *, / and sqrt).  INTEGER values
are 32-bit two's complement.  BAL is DOUBLE PRECISION.
"""

import math
import struct

_PACK_F = struct.Struct("<f")
_INT_MIN = -(2 ** 31)
_INF = float("inf")
_NAN = float("nan")


def _r(x):
    """Round a double to the nearest single precision value (ties to even)."""
    try:
        return _PACK_F.unpack(_PACK_F.pack(x))[0]
    except OverflowError:
        return math.copysign(_INF, x)


def _i32(n):
    """Wrap an integer to 32-bit two's complement."""
    n &= 0xFFFFFFFF
    return n - 0x100000000 if n & 0x80000000 else n


def _flt(n):
    """FLOAT / REAL() of an INTEGER."""
    return _r(float(n))


def _add(a, b):
    return _r(a + b)


def _sub(a, b):
    return _r(a - b)


def _mul(a, b):
    return _r(a * b)


def _div(a, b):
    if b == 0.0:
        if a != a or a == 0.0:
            return _NAN
        neg = (math.copysign(1.0, a) < 0) != (math.copysign(1.0, b) < 0)
        return -_INF if neg else _INF
    return _r(a / b)


def _sqrt(a):
    if a != a or a < 0.0:
        return _NAN
    if a == _INF:
        return _INF
    return _r(math.sqrt(a))


def _itrunc(x):
    """REAL -> INTEGER by truncation (cvttss2si semantics)."""
    if x != x or x in (_INF, -_INF):
        return _INT_MIN
    t = int(x)
    if t < _INT_MIN or t > 2 ** 31 - 1:
        return _INT_MIN
    return t


def _nint(x):
    """NINT of a REAL: round half away from zero (lroundf, then to int)."""
    if x != x or x in (_INF, -_INF):
        return 0
    a = abs(x)
    r = math.floor(a)
    if a - r >= 0.5:
        r += 1
    r = int(r)
    if x < 0:
        r = -r
    if r < -(2 ** 63) or r >= 2 ** 63:
        return 0
    return _i32(r)


def _idiv(a, b):
    """Fortran INTEGER division (truncates toward zero)."""
    q = abs(a) // abs(b)
    if (a < 0) != (b < 0):
        q = -q
    return _i32(q)


def _imod(a, b):
    """Fortran MOD for INTEGERs (sign of the dividend)."""
    return _i32(a - _idiv(a, b) * b)


def _amin(a, b):
    """AMIN1 as gfortran emits it: first argument kept on ties and NaN."""
    return b if b < a else a


def _amax(a, b):
    return b if b > a else a


def _dim(x, y):
    d = _sub(x, y)
    return d if d > 0.0 else 0.0


def _isign(a, b):
    m = abs(a)
    return _i32(m if b >= 0 else -m)


# single precision constants
_PXTEMP = _r(1.0)
_TBASE = _r(0.0)
_CMELT = _r(0.15)
_REFRZ = _r(0.0025)
_HOLD = _r(0.04)
_TIPM = _r(0.2)
_UH = tuple(_r(v) for v in (0.1, 0.3, 0.25, 0.2, 0.1, 0.05))
_C = tuple(_r(v) for v in (0.55, 0.021, 1.2, 0.4))
# EQUIVALENCE (C(1), D(1,1)), column-major D(2,2)
_D11, _D21, _D12, _D22 = _C
_E0 = _r(6.108)
_E1 = _r(0.4436)
_E2 = _r(0.01428)
_E3 = _r(0.000265)


def _petham(tavg, nday):
    ndy = _imod(_i32(nday - 1), 360)
    iph = _i32(_idiv(ndy, 30) - 6)
    k = _i32(_isign(iph, _i32(6 - _idiv(ndy, 30))) * iph)
    dl = _add(_D12, _mul(_D21, _flt(k)))
    if tavg <= 0.0:
        return 0.0
    t = tavg
    esat = _add(_E0, _mul(t, _add(_E1, _mul(t, _add(_E2, _mul(t, _E3))))))
    v = _mul(_D11, dl)
    v = _mul(v, esat)
    v = _mul(v, _D22)
    return _div(v, _r(5.0))


class Band:
    def __init__(self, we0, sm10, sm20):
        # SAVEd locals, one program per band
        self._nwarm = 0
        self._qprev = 0.0
        # BANDIN
        self.we = _r(float(we0))
        self.liqw = 0
        self.heat = 0.0
        self.kdays = 0
        self.bal = 0.0
        self.qbuf = [0.0] * 24
        self.npos = 1
        self.qtot = 0.0
        # SOILIN
        self.sm1 = _r(float(sm10))
        self.sm2 = _r(float(sm20))
        self._cap1 = _r(25.0)
        self._cap2 = _r(120.0)
        self._ndry = 0
        self._frac = _r(0.35)

    # ------------------------------------------------------------------
    def _snowpk(self, px, ta, nhr):
        itsum = 0
        for k in range(nhr):
            itsum = _i32(itsum + _nint(_mul(ta[k], _r(10.0))))
        itavg = _idiv(itsum, nhr)
        mid = _idiv(_i32(nhr + 1), 2)
        if itavg > 0:
            self._nwarm = _i32(self._nwarm + 1)
        fmelt = _mul(_CMELT, _add(1.0, _mul(_flt(_idiv(self._nwarm, 10)), _r(0.25))))

        out = 0.0
        dmtot = 0.0
        frtot = 0.0
        we = self.we
        liqw = self.liqw
        heat = self.heat
        bal = self.bal
        k = 1
        while k <= nhr:
            t = ta[k - 1]
            p = px[k - 1]
            if t < -90.0:
                break
            d = _sub(t, _PXTEMP)
            if d <= 0.0:
                we = _add(we, p)
            else:
                liqw = _itrunc(_add(_flt(liqw), p))
            w = _TIPM
            if k == mid:
                w = _mul(_TIPM, _r(2.0))
            heat = _add(heat, _mul(w, _sub(t, heat)))
            if t > _TBASE:
                dmelt = _div(_mul(fmelt, _sub(t, _TBASE)), _r(24.0))
                dmelt = _amin(dmelt, we)
                we = _sub(we, dmelt)
                liqw = _itrunc(_add(_flt(liqw), dmelt))
                dmtot = _add(dmtot, dmelt)
            else:
                frz = _mul(_mul(_REFRZ, _dim(_TBASE, heat)),
                           _sqrt(_add(_flt(liqw), 1.0)))
                frz = _amin(frz, _flt(liqw))
                liqw = _itrunc(_sub(_flt(liqw), frz))
                we = _add(we, frz)
                frtot = _add(frtot, frz)
            cap = _mul(_HOLD, we)
            if _flt(liqw) > cap:
                out = _add(out, _sub(_flt(liqw), cap))
                liqw = _itrunc(cap)
            bal = (bal + p) - out
            k += 1
        nhr = _i32(k - 1)
        self.we = we
        self.liqw = liqw
        self.heat = heat
        self.bal = bal
        iwe = _nint(_mul(we, _r(100.0)))
        return nhr, out, iwe, itavg, dmtot, frtot

    def _soilmx(self, win, pet):
        if _sub(win, _r(0.5)) < 0.0:
            self._ndry = _i32(self._ndry + 1)
        else:
            self._ndry = 0
        sm1 = _add(self.sm1, win)
        if sm1 > self._cap1:
            xs = _sub(sm1, self._cap1)
            sm1 = self._cap1
        else:
            xs = 0.0
        perc = _mul(xs, self._frac)
        sm2 = _add(self.sm2, _sub(xs, perc))
        if sm2 > self._cap2:
            perc = _add(perc, _sub(sm2, self._cap2))
            sm2 = self._cap2
        wet = _div(sm1, self._cap1)
        aet = _mul(pet, _amin(1.0, _mul(wet, _r(1.25))))
        aet = _amin(aet, sm1)
        sm1 = _sub(sm1, aet)
        self.sm1 = sm1
        self.sm2 = sm2
        kdry = _idiv(self._ndry, 3)
        istat = min(kdry, 9)
        return perc, aet, istat

    def _uhrout(self, qin):
        q = self.qbuf
        for l in range(1, 7):
            idx = _imod(_i32(self.npos + l - 2), 24) + 1
            q[idx - 1] = _add(q[idx - 1], _mul(qin, _UH[l - 1]))
        qout = q[self.npos - 1]
        q[self.npos - 1] = 0.0
        self.qtot = _add(self.qtot, qout)
        self.npos = _imod(self.npos, 24) + 1
        return qout

    # ------------------------------------------------------------------
    def day(self, px, ta):
        """One call of BANDDY with PX = px, TA = ta and NHR = len(ta).

        Returns None when BANDDY takes its alternate return, and otherwise
        (RES, IRES, NHR, CODE) as BANDDY leaves them.
        """
        px = [_r(float(v)) for v in px]
        ta = [_r(float(v)) for v in ta]
        nhr = len(ta)
        self.kdays = _i32(self.kdays + 1)
        if nhr < 1 or nhr > 24:
            return None

        nhr, outflw, iwe, itavg, dmtot, frtot = self._snowpk(px, ta, nhr)
        pet = _petham(_div(_flt(itavg), _r(10.0)), self.kdays)
        perc, aet, istat = self._soilmx(outflw, pet)
        qout = self._uhrout(perc)

        store1 = 0.0
        store2 = 0.0
        for i in range(12):
            store1 = _add(store1, self.qbuf[i])
            store2 = _add(store2, self.qbuf[12 + i])

        ipeak = _itrunc(_amax(_mul(qout, _r(10.0)), _mul(self._qprev, _r(10.0))))
        rmax = _flt(max(ipeak, _imod(itavg, 7)))
        self._qprev = qout

        nsum = 0
        j = nhr
        count = _idiv(nhr + 3, 4)
        if count < 0:
            count = 0
        for _ in range(count):
            nsum = _i32(nsum + j)
            j = _i32(j - 4)
        jlast = j

        code = "SNOW  " if iwe > 0 else "BARE  "
        if outflw > 0.0:
            code = code[:4] + "RO"
        if code == "SNOW  " and itavg < 0:
            code = code[:4] + "C" + code[5]

        res = (outflw, dmtot, frtot, aet, perc, qout, store1, store2, rmax)
        ires = (iwe, itavg, ipeak, istat, nsum, jlast)
        return res, ires, nhr, code

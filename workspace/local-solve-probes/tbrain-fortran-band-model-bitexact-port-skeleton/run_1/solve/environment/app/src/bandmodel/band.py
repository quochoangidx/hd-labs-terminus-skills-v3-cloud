"""BANDIN and BANDDY from legacy/bandmd.f.

A Band is one band's program run: the constructor calls BANDIN, day() is one
call of BANDDY, and the attributes hold the common blocks after the latest
call.

All REAL arithmetic is emulated in IEEE single precision: every operation is
done on doubles (exact inputs) and rounded once to single, which is exact for
+, -, *, / and sqrt because double carries more than 2*24+2 bits.
"""

import math
import struct

_PACK = struct.Struct("<f")


def _r(x):
    """Round a Python float to the nearest IEEE single (ties to even)."""
    return _PACK.unpack(_PACK.pack(x))[0]


def _add(a, b):
    return _r(a + b)


def _sub(a, b):
    return _r(a - b)


def _mul(a, b):
    return _r(a * b)


def _div(a, b):
    return _r(a / b)


def _float(i):
    """FLOAT / implicit INTEGER -> REAL conversion."""
    return _r(float(i))


def _int(x):
    """REAL -> INTEGER conversion (truncation toward zero)."""
    return int(x)


def _nint(x):
    """NINT: nearest integer, halves away from zero."""
    if x >= 0.0:
        f = math.floor(x)
        return int(f) + (1 if x - f >= 0.5 else 0)
    y = -x
    f = math.floor(y)
    return -(int(f) + (1 if y - f >= 0.5 else 0))


def _idiv(a, b):
    """INTEGER division truncating toward zero."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def _mod(a, b):
    """MOD for INTEGER: result has the sign of a."""
    return a - _idiv(a, b) * b


def _isign(a, b):
    return abs(a) if b >= 0 else -abs(a)


def _amin1(a, b):
    return b if b < a else a


def _amax1(a, b):
    return b if b > a else a


def _dim(a, b):
    d = _sub(a, b)
    return d if d > 0.0 else 0.0


# Single-precision constants
_F = _r
_PXTEMP = _F(1.0)
_TBASE = _F(0.0)
_CMELT = _F(0.15)
_REFRZ = _F(0.0025)
_HOLD = _F(0.04)
_TIPM = _F(0.2)
_UH = tuple(_F(v) for v in (0.1, 0.3, 0.25, 0.2, 0.1, 0.05))
# C(4) equivalenced with D(2,2), column major
_C = tuple(_F(v) for v in (0.55, 0.021, 1.2, 0.4))
_D11, _D21, _D12, _D22 = _C


def _esat(t):
    inner = _add(_F(0.01428), _mul(t, _F(0.000265)))
    inner = _add(_F(0.4436), _mul(t, inner))
    return _add(_F(6.108), _mul(t, inner))


def _petham(tavg, nday):
    ndy = _mod(nday - 1, 360)
    iph = _idiv(ndy, 30) - 6
    k = _isign(iph, 6 - _idiv(ndy, 30)) * iph
    dl = _add(_D12, _mul(_D21, _float(k)))
    if tavg <= 0.0:
        return 0.0
    v = _mul(_D11, dl)
    v = _mul(v, _esat(tavg))
    v = _mul(v, _D22)
    return _div(v, _F(5.0))


class Band:
    def __init__(self, we0, sm10, sm20):
        # BANDIN
        self.we = _r(float(we0))
        self.liqw = 0
        self.heat = 0.0
        self.kdays = 0
        self.bal = 0.0
        self.qbuf = [0.0] * 24
        self.npos = 1
        self.qtot = 0.0
        # SAVEd locals
        self._qprev = 0.0   # BANDDY
        self._nwarm = 0     # SNOWPK
        # ENTRY SOILIN
        self.sm1 = _r(float(sm10))
        self.sm2 = _r(float(sm20))
        self._cap1 = _F(25.0)
        self._cap2 = _F(120.0)
        self._ndry = 0
        self._frac = _F(0.35)

    # ------------------------------------------------------------------
    def _snowpk(self, px, ta, nhr):
        itsum = 0
        for k in range(nhr):
            itsum += _nint(_mul(ta[k], _F(10.0)))
        itavg = _idiv(itsum, nhr)
        mid = _idiv(nhr + 1, 2)
        if itavg > 0:
            self._nwarm += 1
        fmelt = _mul(_CMELT,
                     _add(_F(1.0), _mul(_float(_idiv(self._nwarm, 10)),
                                        _F(0.25))))

        out = 0.0
        dmtot = 0.0
        frtot = 0.0
        k = 1
        while k <= nhr:
            t = ta[k - 1]
            p = px[k - 1]
            if t < -90.0:
                break
            if _sub(t, _PXTEMP) <= 0.0:
                self.we = _add(self.we, p)
            else:
                self.liqw = _int(_add(_float(self.liqw), p))
            w = _TIPM
            if k == mid:
                w = _mul(_TIPM, _F(2.0))
            self.heat = _add(self.heat, _mul(w, _sub(t, self.heat)))
            if t > _TBASE:
                dmelt = _div(_mul(fmelt, _sub(t, _TBASE)), _float(24))
                dmelt = _amin1(dmelt, self.we)
                self.we = _sub(self.we, dmelt)
                self.liqw = _int(_add(_float(self.liqw), dmelt))
                dmtot = _add(dmtot, dmelt)
            else:
                sq = _r(math.sqrt(_add(_float(self.liqw), _F(1.0))))
                frz = _mul(_mul(_REFRZ, _dim(_TBASE, self.heat)), sq)
                frz = _amin1(frz, _float(self.liqw))
                self.liqw = _int(_sub(_float(self.liqw), frz))
                self.we = _add(self.we, frz)
                frtot = _add(frtot, frz)
            cap = _mul(_HOLD, self.we)
            if _float(self.liqw) > cap:
                out = _add(out, _sub(_float(self.liqw), cap))
                self.liqw = _int(cap)
            self.bal = (self.bal + p) - out
            k += 1
        nhr = k - 1
        outflw = out
        iwe = _nint(_mul(self.we, _F(100.0)))
        return nhr, outflw, iwe, itavg, dmtot, frtot

    def _soilmx(self, win, pet):
        if _sub(win, _F(0.5)) < 0.0:
            self._ndry += 1
        else:
            self._ndry = 0
        self.sm1 = _add(self.sm1, win)
        if self.sm1 > self._cap1:
            xs = _sub(self.sm1, self._cap1)
            self.sm1 = self._cap1
        else:
            xs = 0.0
        perc = _mul(xs, self._frac)
        self.sm2 = _add(self.sm2, _sub(xs, perc))
        if self.sm2 > self._cap2:
            perc = _add(perc, _sub(self.sm2, self._cap2))
            self.sm2 = self._cap2
        wet = _div(self.sm1, self._cap1)
        aet = _mul(pet, _amin1(_F(1.0), _mul(wet, _F(1.25))))
        aet = _amin1(aet, self.sm1)
        self.sm1 = _sub(self.sm1, aet)
        kdry = _idiv(self._ndry, 3)
        istat = min(kdry, 9)
        return perc, aet, istat

    def _uhrout(self, qin):
        q = self.qbuf
        for l in range(1, 7):
            idx = _mod(self.npos + l - 2, 24) + 1
            q[idx - 1] = _add(q[idx - 1], _mul(qin, _UH[l - 1]))
        qout = q[self.npos - 1]
        q[self.npos - 1] = 0.0
        self.qtot = _add(self.qtot, qout)
        self.npos = _mod(self.npos, 24) + 1
        return qout

    # ------------------------------------------------------------------
    def day(self, px, ta):
        """One call of BANDDY with PX = px, TA = ta and NHR = len(ta).

        Returns None when BANDDY takes its alternate return, and otherwise
        (RES, IRES, NHR, CODE) as BANDDY leaves them.
        """
        ta = [_r(float(v)) for v in ta]
        px = [_r(float(v)) for v in px]
        nhr = len(ta)
        self.kdays += 1
        if nhr < 1 or nhr > 24:
            return None

        nhr, outflw, iwe, itavg, dmtot, frtot = self._snowpk(px, ta, nhr)
        pet = _petham(_div(_float(itavg), _F(10.0)), self.kdays)
        perc, aet, istat = self._soilmx(outflw, pet)
        qout = self._uhrout(perc)

        store1 = 0.0
        store2 = 0.0
        for i in range(12):
            store1 = _add(store1, self.qbuf[i])
            store2 = _add(store2, self.qbuf[12 + i])

        ipeak = _int(_amax1(_mul(qout, _F(10.0)),
                            _mul(self._qprev, _F(10.0))))
        rmax = _float(max(ipeak, _mod(itavg, 7)))
        self._qprev = qout

        # DO 30 J = NHR, 1, -4
        count = max(_idiv(1 - nhr + (-4), -4), 0)
        nsum = 0
        j = nhr
        for _ in range(count):
            nsum += j
            j -= 4
        jlast = j

        code = "SNOW  " if iwe > 0 else "BARE  "
        if outflw > 0.0:
            code = code[:4] + "RO"
        if code == "SNOW  " and itavg < 0:
            code = code[:4] + "C" + code[5]

        res = (outflw, dmtot, frtot, aet, perc, qout, store1, store2, rmax)
        ires = (iwe, itavg, ipeak, istat, nsum, jlast)
        return res, ires, nhr, code

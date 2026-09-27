"""SNOWIN and SNOWPK from legacy/snowpk.f.

One SnowBand is one elevation band run from its start: the constructor is
SNOWIN, day() is one call of SNOWPK, and the attributes we, liqw, heat, kdays
and bal are COMMON /PACK/ after the latest call.
"""


class SnowBand:
    def __init__(self, we0):
        raise NotImplementedError("port SNOWIN")

    def day(self, px, ta):
        """One call of SNOWPK with PX = px and TA = ta (NHR = len(ta)).

        Returns (outflw, iwe, nhr, itavg, dmtot, frtot), nhr being NHR as
        SNOWPK leaves it.
        """
        raise NotImplementedError("port SNOWPK")

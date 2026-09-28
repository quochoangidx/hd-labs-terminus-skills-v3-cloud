"""BANDIN and BANDDY from legacy/bandmd.f.

A Band is one band's program run: the constructor calls BANDIN, day() is one
call of BANDDY, and the attributes hold the common blocks after the latest
call.
"""


class Band:
    def __init__(self, we0, sm10, sm20):
        raise NotImplementedError("port BANDIN")

    def day(self, px, ta):
        """One call of BANDDY with PX = px, TA = ta and NHR = len(ta).

        Returns None when BANDDY takes its alternate return, and otherwise
        (RES, IRES, NHR, CODE) as BANDDY leaves them.
        """
        raise NotImplementedError("port BANDDY")

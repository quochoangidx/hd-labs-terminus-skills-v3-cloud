"""Running deductible and out-of-pocket totals for one family."""

from collections import defaultdict

from costshare.plan import Plan


class Ledger:
    """What each member, and the family as a whole, has paid so far this year."""

    def __init__(self, plan: Plan) -> None:
        self.plan = plan
        self._deductible: dict[str, int] = defaultdict(int)
        self._oop: dict[str, int] = defaultdict(int)
        self._family_deductible = 0
        self._family_oop = 0

    def deductible_paid(self, member: str) -> int:
        return self._deductible[member]

    def oop_paid(self, member: str) -> int:
        return self._oop[member]

    def family_deductible_paid(self) -> int:
        return self._family_deductible

    def family_oop_paid(self) -> int:
        return self._family_oop

    def record(self, member: str, deductible: int, copay: int, coinsurance: int) -> None:
        """Add one priced line's member parts to the running totals."""
        self._deductible[member] += deductible
        self._family_deductible += deductible
        self._oop[member] += deductible + copay + coinsurance
        self._family_oop += deductible + coinsurance

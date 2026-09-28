"""Price claim lines against a plan and keep the family's totals."""

from dataclasses import dataclass

from costshare.ledger import Ledger
from costshare.money import share
from costshare.plan import Plan


@dataclass(frozen=True)
class Line:
    member: str
    kind: str
    allowed: int


@dataclass(frozen=True)
class Result:
    allowed: int
    deductible: int
    copay: int
    coinsurance: int

    @property
    def member_total(self) -> int:
        return self.deductible + self.copay + self.coinsurance

    @property
    def plan_pays(self) -> int:
        return self.allowed - self.member_total


class Adjudicator:
    """Prices one family's lines, in the order received, for one benefit year."""

    def __init__(self, plan: Plan) -> None:
        self.plan = plan
        self.ledger = Ledger(plan)

    def deductible_left(self, member: str) -> int:
        plan = self.plan
        left = plan.deductible - self.ledger.deductible_paid(member)
        if plan.family_deductible > 0:
            left = min(left, plan.family_deductible - self.ledger.family_deductible_paid())
        return left

    def adjudicate(self, line: Line) -> Result:
        plan = self.plan
        if line.kind == "preventive":
            return Result(line.allowed, 0, 0, 0)

        deductible = copay = coinsurance = 0
        if line.kind == "office":
            copay = plan.office_copay
            if 0 < line.allowed < copay:
                copay = line.allowed
        else:
            deductible = min(line.allowed, self.deductible_left(line.member))
            coinsurance = share(line.allowed - deductible, plan.coinsurance)

        rooms = []
        if plan.oop_max > 0:
            rooms.append(plan.oop_max - self.ledger.oop_paid(line.member))
        if plan.family_oop_max > 0:
            rooms.append(plan.family_oop_max - self.ledger.family_oop_paid())
        if rooms:
            excess = deductible + copay + coinsurance - min(rooms)
            if excess > 0:
                take = min(max(coinsurance, 0), excess)
                coinsurance -= take
                excess -= take
                take = min(max(copay, 0), excess)
                copay -= take
                excess -= take
                take = min(max(deductible, 0), excess)
                deductible -= take

        self.ledger.record(line.member, deductible, copay, coinsurance)
        return Result(line.allowed, deductible, copay, coinsurance)

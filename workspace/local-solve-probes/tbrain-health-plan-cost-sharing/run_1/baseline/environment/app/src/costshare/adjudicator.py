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
        return self.plan.deductible - self.ledger.deductible_paid(member)

    def adjudicate(self, line: Line) -> Result:
        plan = self.plan
        deductible = copay = coinsurance = 0
        if line.kind == "office":
            copay = plan.office_copay
            coinsurance = share(line.allowed - copay, plan.coinsurance)
        else:
            deductible = min(line.allowed, self.deductible_left(line.member))
            coinsurance = share(line.allowed, plan.coinsurance)
        charged_deductible = deductible

        if plan.oop_max > 0:
            room = plan.oop_max - self.ledger.oop_paid(line.member)
            excess = deductible + copay + coinsurance - room
            if excess > 0:
                take = min(deductible, excess)
                deductible -= take
                excess -= take
                take = min(copay, excess)
                copay -= take
                excess -= take
                coinsurance -= min(coinsurance, excess)

        self.ledger.record(line.member, charged_deductible, copay, coinsurance)
        return Result(line.allowed, deductible, copay, coinsurance)

"""Expected cost sharing, worked out from /app/docs/cost-sharing.md.

This module never imports, loads or runs the package under repair. Each rule
cites the note section it comes from. Where the note is silent, the expectation
mirrors the shipped expression and says which one; it never substitutes a
reading of its own.
"""

from __future__ import annotations

from fractions import Fraction
from math import floor

BASIS = 10_000
KINDS_PRICED_AS_FACILITY = "any kind other than preventive or office (2.2)"


def share(amount: int, rate: int) -> int:
    """1.2-1.3: nearest cent, halves to the even cent, for a rate from 0 to 10000."""
    if 0 <= rate <= BASIS:
        exact = Fraction(amount * rate, BASIS)
        low = floor(exact)
        gap = exact - low
        if gap > Fraction(1, 2) or (gap == Fraction(1, 2) and low % 2 == 1):
            return low + 1
        return low
    # Silent: the note describes no rate outside 0..10000. Shipped money.share:
    # (amount * rate + BASIS // 2) // BASIS.
    return (amount * rate + BASIS // 2) // BASIS


class Book:
    """The four running totals of 7.1-7.2."""

    def __init__(self, plan: dict) -> None:
        self.plan = plan
        self.deductible: dict[str, int] = {}
        self.oop: dict[str, int] = {}
        self.family_deductible = 0
        self.family_oop = 0

    def snapshot(self, members) -> dict:
        return {
            "deductible": {m: self.deductible.get(m, 0) for m in members},
            "oop": {m: self.oop.get(m, 0) for m in members},
            "family_deductible": self.family_deductible,
            "family_oop": self.family_oop,
        }

    def record(self, member: str, deductible: int, copay: int, coinsurance: int) -> None:
        cost_share = deductible + copay + coinsurance
        # 7.1: the deductible part goes on the member's and the family's deductible totals.
        self.deductible[member] = self.deductible.get(member, 0) + deductible
        self.family_deductible += deductible
        # 7.2: the whole cost share goes on the member's out-of-pocket total.
        self.oop[member] = self.oop.get(member, 0) + cost_share
        if self.plan["family_oop_max"] > 0:
            # 7.2: the family total is the sum of the members' totals.
            self.family_oop += cost_share
        else:
            # Silent: 7.2 says nothing of a family total without a family maximum.
            # Shipped Ledger.record adds deductible + coinsurance to it.
            self.family_oop += deductible + coinsurance

    def deductible_left(self, member: str) -> int:
        # 5.2: member deductible less the member's deductible total, and on a plan
        # with a family deductible above zero, the smaller of that and the family's.
        left = self.plan["deductible"] - self.deductible.get(member, 0)
        if self.plan["family_deductible"] > 0:
            left = min(left, self.plan["family_deductible"] - self.family_deductible)
        return left


def _cut(parts: dict, excess: int) -> None:
    """6.2: coinsurance, then copay, then deductible; no part taken below zero."""
    for name in ("coinsurance", "copay", "deductible"):
        if excess <= 0:
            return
        available = max(parts[name], 0)
        taken = min(available, excess)
        parts[name] -= taken
        excess -= taken


def price(book: Book, line: dict) -> dict:
    plan = book.plan
    allowed = line["allowed"]
    parts = {"deductible": 0, "copay": 0, "coinsurance": 0}
    if line["kind"] == "preventive":
        # 3: nothing charged, nothing recorded.
        return {"allowed": allowed, **parts}
    if line["kind"] == "office":
        # 4.1-4.2: the copay, or the allowed amount when 0 < allowed < copay.
        copay = plan["office_copay"]
        parts["copay"] = allowed if 0 < allowed < copay else copay
    else:
        # 5.1-5.3, and 2.2 for every other kind.
        deductible = min(allowed, book.deductible_left(line["member"]))
        parts["deductible"] = deductible
        parts["coinsurance"] = share(allowed - deductible, plan["coinsurance"])
    # 6.1: one room per maximum above zero.
    rooms = []
    if plan["oop_max"] > 0:
        rooms.append(plan["oop_max"] - book.oop.get(line["member"], 0))
    if plan["family_oop_max"] > 0:
        rooms.append(plan["family_oop_max"] - book.family_oop)
    if rooms:
        cost_share = parts["deductible"] + parts["copay"] + parts["coinsurance"]
        if cost_share > min(rooms):
            _cut(parts, cost_share - min(rooms))
    # 7.1-7.2 after pricing and cutting.
    book.record(line["member"], parts["deductible"], parts["copay"], parts["coinsurance"])
    return {"allowed": allowed, **parts}


def run_session(plan: dict, lines: list[dict], members: list[str]) -> list[dict]:
    """Price lines in order; after each, the result and all four totals."""
    book = Book(plan)
    out = []
    for line in lines:
        result = price(book, line)
        out.append({"result": result, "totals": book.snapshot(members)})
    return out


def run_ops(ops: list[dict]) -> list[dict]:
    """The expected driver output for a scripted job (see driver/run_ops.py)."""
    book = None
    out: list[dict] = []
    for op in ops:
        kind = op["op"]
        if kind == "new":
            book = Book(dict(op["plan"]))
            out.append({"ok": True})
        elif kind == "line":
            parts = price(book, op)
            cost_share = parts["deductible"] + parts["copay"] + parts["coinsurance"]
            out.append({
                **parts,
                "member_total": cost_share,
                "plan_pays": parts["allowed"] - cost_share,
            })
        elif kind == "totals":
            out.append(book.snapshot(op["members"]))
        elif kind == "left":
            out.append({"left": book.deductible_left(op["member"])})
        elif kind == "record":
            book.record(op["member"], op["deductible"], op["copay"], op["coinsurance"])
            out.append({"ok": True})
        elif kind == "share":
            out.append({"share": share(op["amount"], op["rate"])})
        else:
            raise ValueError(kind)
    return out

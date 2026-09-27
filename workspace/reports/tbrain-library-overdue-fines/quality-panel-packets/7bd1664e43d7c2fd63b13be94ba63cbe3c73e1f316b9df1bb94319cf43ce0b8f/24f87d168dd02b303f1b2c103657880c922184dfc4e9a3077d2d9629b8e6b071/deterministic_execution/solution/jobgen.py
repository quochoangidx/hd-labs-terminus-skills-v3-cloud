"""Return files for the verifier, one family per test (python3 solution/seal.py writes them out).

Named files sit on the edges each rule reaches; seeded files (a constant seed, never candidate bytes) cover the
rest of the rule 1.2 domain. Two figures are left by the policy to today's code: the loan period of a journal, and
the late days and fine of a loan that is not late. Each such loan appears only in the families that grade it.
Day 6 and every seventh day after it is a Sunday.
"""

import random

SEED = 20261003
CODE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
MAX_LOANS = 200


def ln(lid, kind, borrowed, after, daily, replacement=20000):
    """A loan returned ``after`` days after its borrowing day."""
    return {"id": lid, "kind": kind, "borrowed": borrowed, "returned": borrowed + after, "daily_fine": daily,
            "replacement": replacement}


def returns(loans):
    return {"branch": "", "loans": loans}


def loan_period():
    """2.1: a book is due 21 days after borrowing, a DVD 7; one day late each."""
    return [returns([ln("P1", "BOOK", 700, 22, 25), ln("P2", "DVD", 700, 8, 100), ln("P3", "BOOK", 700, 30, 10),
                     ln("P4", "DVD", 700, 16, 10), ln("P5", "BOOK", 0, 22, 1), ln("P6", "DVD", 3650, 8, 500)])]


def sundays():
    """2.2: a Sunday is never a late day; due days and return days on Sundays, spans over one Sunday or many."""
    # 1406 is a Sunday.
    return [returns([ln("S1", "DVD", 1399, 8, 50), ln("S2", "DVD", 1398, 8, 50), ln("S3", "DVD", 1398, 9, 50),
                     ln("S4", "BOOK", 1385, 22, 50), ln("S5", "BOOK", 1385, 23, 50), ln("S6", "BOOK", 1380, 90, 3),
                     ln("S7", "DVD", 1399, 14, 7), ln("S8", "DVD", 1399, 15, 7)])]


def cap():
    """3.1: never more than the replacement cost; short of it, exactly on it and past it."""
    return [returns([ln("C1", "DVD", 2000, 30, 100, 1800), ln("C2", "DVD", 2000, 30, 100, 1900), ln("C3", "DVD", 2000, 30, 100, 2100),
                     ln("C4", "BOOK", 2000, 180, 500, 100), ln("C5", "BOOK", 2000, 180, 1, 20000), ln("C6", "BOOK", 2000, 23, 150, 150)])]


def order_and_total():
    """README: loans in file order; 3.2 the total."""
    return [returns([ln("ZZZZZZZZZZ", "BOOK", 50, 40, 20), ln("0", "DVD", 51, 60, 300, 5000), ln("A1", "BOOK", 52, 23, 1)]),
            returns([ln("ONLY", "DVD", 900, 12, 75, 1500)])]


def journal():
    """A journal: the policy gives no loan period; today's step (14 days) stands."""
    return [returns([ln("J1", "JOURNAL", 1000, 15, 20), ln("J2", "JOURNAL", 1000, 16, 20), ln("J3", "JOURNAL", 1001, 40, 60, 900),
                     ln("J4", "JOURNAL", 3650, 180, 500), ln("J5", "BOOK", 1000, 15 + 7, 20), ln("J6", "DVD", 1000, 15, 20)])]


def not_late():
    """A loan returned on or before its due day: the policy gives no late days or fine; today's step (return day
    less due day, that many days at the daily fine) stands."""
    return [returns([ln("N1", "BOOK", 1400, 0, 25), ln("N2", "BOOK", 1400, 21, 25), ln("N3", "DVD", 1402, 7, 100), ln("N4", "DVD", 1402, 3, 500),
                     ln("N5", "BOOK", 1405, 6, 25, 100), ln("N6", "BOOK", 0, 1, 1), ln("N7", "DVD", 1399, 12, 30)])]


def together():
    """Both figures in one file: journals returned early, on time and late, beside books and DVDs."""
    return [returns([ln("X1", "JOURNAL", 70, 0, 40), ln("X2", "JOURNAL", 70, 14, 40), ln("X3", "JOURNAL", 70, 30, 40, 300),
                     ln("X4", "DVD", 70, 2, 40), ln("X5", "BOOK", 70, 60, 40)])]


def limits():
    """1.2 at its ends: 200 loans, borrowing days 0 and 3,650, returns 180 days later, fines 1 and 500, costs 100
    and 20,000, ids of 1 and 10. Every loan is a late book or DVD."""
    rng = random.Random(SEED + 1)
    out = []
    for k in range(MAX_LOANS):
        kind = rng.choice(["BOOK", "DVD"])
        after = rng.choice([180, rng.randint(22 if kind == "BOOK" else 8, 180)])
        out.append(ln(f"L{k}", kind, rng.choice([0, 3650, rng.randint(0, 3650)]), after, rng.choice([1, 500, rng.randint(1, 500)]),
                      rng.choice([100, 20000, rng.randint(100, 20000)])))
    out[0] = ln("ABCDEFGHIJ", "BOOK", 3650, 180, 500, 20000)
    out[1] = ln("9", "DVD", 0, 180, 1, 100)
    return [returns(out)]


def generated():
    """Seeded files of late books and DVDs."""
    rng = random.Random(SEED)
    out = []
    for _ in range(4):
        items = []
        for k in range(rng.randint(3, 25)):
            kind = rng.choice(["BOOK", "DVD"])
            after = rng.randint(22 if kind == "BOOK" else 8, rng.choice([40, 90, 180]))
            lid = "".join(rng.choice(CODE) for _ in range(rng.randint(1, 7))) + str(k)
            items.append(ln(lid[-10:], kind, rng.randint(0, 3650), after, rng.randint(1, 500), rng.randint(100, 20000)))
        out.append(returns(items))
    return out


FAMILIES = {
    "loan_period": loan_period,
    "sundays": sundays,
    "cap": cap,
    "order_and_total": order_and_total,
    "journal": journal,
    "not_late": not_late,
    "together": together,
    "generated": generated,
    "limits": limits,
}

# Figures left to today's code that each family grades.
GRADES = {"journal": {"journal"}, "not_late": {"idle"}, "together": {"journal", "idle"}}


def families():
    return {name: make() for name, make in FAMILIES.items()}

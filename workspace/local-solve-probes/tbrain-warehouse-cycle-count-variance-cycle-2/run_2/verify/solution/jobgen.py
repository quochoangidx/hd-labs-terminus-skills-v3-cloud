"""Count sheets for the verifier, one family per test (python3 solution/seal.py writes them out).

Named sheets sit on the edges each rule reaches; seeded sheets (a constant seed, never candidate bytes) cover
the rest of the rule 1.3 domain. Two figures are left by the procedure to today's code: the tolerance of a line
that is not a graded item (its class is not A, B or C), and the units booked by a line that is not adjusted.
Lines of other classes appear only in the families that grade them, and the booked figure of a line that is not
adjusted is compared only in its own test.
"""

import random

SEED = 20260929
CODE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"
MAX_LINES = 300


def ln(sku, klass, system, count, recount=None, cost=1000):
    return {"sku": sku, "class": klass, "system": system, "count": count, "recount": recount, "unit_cost": cost}


def sheet(lines):
    return {"sheet": "", "lines": lines}


def recounts():
    """2.1: a recount replaces the count."""
    return [sheet([ln("R1", "A", 240, 238, 240), ln("R2", "A", 240, 238, 239), ln("R3", "B", 500, 480, 505),
                   ln("R4", "C", 100, 100, 0), ln("R5", "B", 0, 3, 0), ln("R6", "A", 7, 9, None)])]


def graded_tolerance():
    """2.3, 2.4, 1.2: A nought, B 2 per cent, C 5 per cent, a fraction of a unit dropped; on the edge and one past."""
    return [
        sheet([ln("A1", "A", 1000, 1000), ln("A2", "A", 1000, 999, 999), ln("A3", "A", 1000, 1001, 1001),
               ln("B1", "B", 1000, 1020, 1020), ln("B2", "B", 1000, 1021, 1021), ln("B3", "B", 1049, 1069, 1069),
               ln("B4", "B", 1049, 1070, 1070), ln("B5", "B", 49, 49, 48)]),
        sheet([ln("C1", "C", 100, 95, 95), ln("C2", "C", 100, 94, 94), ln("C3", "C", 119, 124, 124),
               ln("C4", "C", 119, 125, 125), ln("C5", "C", 19, 18, 18), ln("C6", "C", 95000, 99750, 99750),
               ln("C7", "C", 100000, 94999, 94999), ln("C8", "B", 100000, 98000, 98000)]),
    ]


def status():
    """3.1: outside tolerance with no recount is "recount", with one "adjust"."""
    return [sheet([ln("S1", "A", 50, 48), ln("S2", "A", 50, 48, 47), ln("S3", "B", 300, 290), ln("S4", "B", 300, 290, 300),
                   ln("S5", "C", 60, 70, None), ln("S6", "C", 60, 70, 70)])]


def shrink():
    """3.4: shrink sums adjusted shortages only; a surplus does not reduce it."""
    return [
        sheet([ln("K1", "A", 10, 8, 8, 18450), ln("K2", "A", 10, 13, 13, 999999), ln("K3", "B", 400, 380, 380, 320),
               ln("K4", "C", 40, 30, None, 75), ln("K5", "A", 5, 5, 5, 1000000)]),
        sheet([ln("K6", "A", 3, 5, 5, 700), ln("K7", "C", 1000, 1100, 1100, 12)]),
    ]


def value_and_order():
    """3.2 and README order: every line's value, in sheet order."""
    return [sheet([ln("ZZ-9", "C", 0, 0, None, 1), ln("0", "A", 100000, 0, 0, 1000000), ln("A-1", "B", 0, 100000, 100000, 1),
                   ln("MMMMMMMMMMMM", "A", 12, 12, None, 55)])]


def other_classes():
    """A line that is not a graded item keeps today's tolerance: 5 per cent, a half going to the even unit."""
    return [sheet([ln("X1", "D", 250, 262, 262), ln("X2", "X", 250, 263, 263), ln("X3", "N", 350, 367, 367),
                   ln("X4", "N", 350, 368, 368), ln("X5", "Z", 0, 1, 1), ln("X6", "Q", 1000, 950, None),
                   ln("X7", "E", 30, 32, 32)])]


def booked_not_adjusted():
    """A line that is not adjusted: the procedure gives no booked figure; today's step (its variance) stands."""
    return [sheet([ln("N1", "C", 100, 97), ln("N2", "B", 500, 509, None), ln("N3", "A", 20, 17, None),
                   ln("N4", "A", 20, 17, 20), ln("N5", "C", 1000, 1049, 1003), ln("N6", "B", 60, 61, 60),
                   ln("N7", "C", 400, 300, 390), ln("N8", "B", 1000, 1500, 1020)])]


def together():
    """Both figures in one sheet: other classes, not adjusted, with shortages and surpluses."""
    return [sheet([ln("T1", "D", 250, 262, None), ln("T2", "N", 350, 330, 331), ln("T3", "B", 100, 101),
                   ln("T4", "A", 9, 7, 7, 400)])]


def limits():
    """1.3 at its ends: 300 lines, quantities 0 and 100,000, costs 1 and 1,000,000, SKUs of 1 and 12 characters."""
    rng = random.Random(SEED + 1)
    lines = []
    for k in range(MAX_LINES):
        system = rng.choice([0, 100000, rng.randint(0, 100000)])
        count = max(0, min(100000, system + rng.randint(-3000, 3000)))
        recount = max(0, min(100000, count + rng.randint(-20, 20)))
        lines.append(ln(f"L{k}", rng.choice("ABC"), system, count, recount, rng.choice([1, 1000000, rng.randint(1, 1000000)])))
    lines[0] = ln("ABCDEFGHIJKL", "A", 100000, 0, 0, 1000000)
    lines[1] = ln("9", "C", 0, 100000, 100000, 1)
    lines[299] = ln("LAST", "B", 5000, 4000, 4000, 777)
    return [sheet(lines)]


def generated():
    """Seeded sheets over graded classes, every line recounted."""
    rng = random.Random(SEED)
    out = []
    for _ in range(4):
        lines = []
        for k in range(rng.randint(3, 20)):
            system = rng.randint(0, 5000)
            count = max(0, system + rng.randint(-120, 120))
            recount = max(0, count + rng.randint(-10, 10))
            sku = "".join(rng.choice(CODE) for _ in range(rng.randint(1, 9))) + str(k)
            lines.append(ln(sku[-12:], rng.choice("ABC"), system, count, recount, rng.randint(1, 1000000)))
        out.append(sheet(lines))
    return out


FAMILIES = {
    "recounts": recounts,
    "graded_tolerance": graded_tolerance,
    "status": status,
    "shrink": shrink,
    "value_and_order": value_and_order,
    "other_classes": other_classes,
    "booked_not_adjusted": booked_not_adjusted,
    "together": together,
    "generated": generated,
    "limits": limits,
}

# Figures left to today's code that each family grades.
GRADES = {"other_classes": {"other_class"}, "booked_not_adjusted": {"booked"}, "together": {"other_class", "booked"}}


def families():
    return {name: make() for name, make in FAMILIES.items()}

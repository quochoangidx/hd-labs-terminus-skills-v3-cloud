"""Account files for the verifier, one family per test (python3 solution/seal.py writes them out).

Named files sit on the edges each rule reaches; seeded files (a constant seed, never candidate bytes) cover the
rest of the rule 1.2 domain. Two figures are left by the tariff to today's code: the allowance of a FLEX line, and
the overage and charge of a line that is not over its allowance. Each such line appears only in the families that
grade it.
"""

import random

SEED = 20261002
CODE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
MAX_LINES = 200
MB = 1024


def ln(lid, plan, sessions, rate):
    return {"id": lid, "plan": plan, "sessions": list(sessions), "rate": rate}


def mb(n, extra=0):
    """Sessions of whole megabytes adding up to n megabytes, each at most 1,953 MB, the last with ``extra`` kB more."""
    out = []
    while n > 0:
        take = min(n, 1953)
        out.append(take * MB)
        n -= take
    if extra and out and out[-1] + extra <= 2000000:
        out[-1] += extra
    elif extra:
        out.append(extra)
    return out


def account(lines):
    return {"account": "", "lines": lines}


def sessions():
    """2.1: each session in whole megabytes, a part megabyte counting as a whole one."""
    return [account([ln("S1", "BASIC", mb(2048) + [1], 7), ln("S2", "BASIC", mb(2000) + [512] * 50, 3),
                     ln("S3", "BASIC", [1025, 1025] + mb(2048), 11), ln("S4", "PLUS", mb(10230) + [1] * 20, 2),
                     ln("S5", "PLUS", [2000000] * 6, 500)])]


def plans():
    """2.2: BASIC 2,048 MB and PLUS 10,240 MB; one megabyte over each."""
    return [account([ln("P1", "BASIC", mb(2049), 9), ln("P2", "PLUS", mb(10241), 9), ln("P3", "BASIC", mb(5121), 9),
                     ln("P4", "PLUS", mb(12000), 1), ln("P5", "BASIC", mb(20000), 500)])]


def later_rate():
    """3.1: the rate for each of the first 1,024 MB of overage, 1 cent for each MB after."""
    return [account([ln("R1", "BASIC", mb(2048 + 1023), 40), ln("R2", "BASIC", mb(2048 + 1024), 40), ln("R3", "BASIC", mb(2048 + 1025), 40),
                     ln("R4", "PLUS", mb(10240 + 1024), 1), ln("R5", "PLUS", mb(10240 + 1026), 2), ln("R6", "PLUS", mb(10240 + 50000), 333)])]


def order_and_total():
    """README: lines in file order; 3.2 the total."""
    return [account([ln("ZZZZZZZZZZ", "PLUS", mb(15000, 7), 12), ln("0", "BASIC", mb(2100), 1), ln("A1", "BASIC", [2000000] * 60, 500)]),
            account([ln("ONLY", "BASIC", mb(3000, 3), 25)])]


def flex():
    """A FLEX line: the tariff gives no allowance; today's step (5,120 MB) stands."""
    return [account([ln("F1", "FLEX", mb(5121), 10), ln("F2", "FLEX", mb(5120 + 1024), 10), ln("F3", "FLEX", mb(9000, 1), 3),
                     ln("F4", "FLEX", [2000000] * 60, 500), ln("F5", "BASIC", mb(5121), 10), ln("F6", "PLUS", mb(10300), 10)])]


def not_over():
    """A line inside its allowance: the tariff gives no overage or charge; today's step (usage less allowance, that
    many megabytes at the rate) stands."""
    return [account([ln("N1", "BASIC", [], 9), ln("N2", "BASIC", [1], 500), ln("N3", "BASIC", mb(2048), 1), ln("N4", "PLUS", mb(10240), 4),
                     ln("N5", "PLUS", mb(3000, 1), 7), ln("N6", "BASIC", [1023, 1025, 1], 2), ln("N7", "BASIC", mb(4000), 5)])]


def together():
    """Both figures in one file: FLEX lines inside and past their allowance, beside BASIC and PLUS lines."""
    return [account([ln("X1", "FLEX", [], 6), ln("X2", "FLEX", mb(5120), 6), ln("X3", "FLEX", mb(7000), 6),
                     ln("X4", "PLUS", mb(100), 6), ln("X5", "BASIC", mb(3100), 6)])]


def limits():
    """1.2 at its ends: 200 lines, 60 sessions, sessions of 1 and 2,000,000 kB, rates 1 and 500, ids of 1 and 10.
    Every line is BASIC or PLUS and over its allowance."""
    rng = random.Random(SEED + 1)
    out = []
    for k in range(MAX_LINES):
        plan = rng.choice(["BASIC", "PLUS"])
        need = (2048 if plan == "BASIC" else 10240) + rng.randint(1, 40000)
        items = mb(need, rng.choice([0, 1, rng.randint(1, 1023)]))
        out.append(ln(f"L{k}", plan, items, rng.choice([1, 500, rng.randint(1, 500)])))
    out[0] = ln("ABCDEFGHIJ", "BASIC", [2000000] * 60, 500)
    out[1] = ln("9", "PLUS", [1] * 3 + mb(10240), 1)
    return [account(out)]


def generated():
    """Seeded files of BASIC and PLUS lines over their allowance."""
    rng = random.Random(SEED)
    out = []
    for _ in range(4):
        items = []
        for k in range(rng.randint(3, 25)):
            plan = rng.choice(["BASIC", "PLUS"])
            need = (2048 if plan == "BASIC" else 10240) + rng.randint(1, rng.choice([1500, 40000]))
            lid = "".join(rng.choice(CODE) for _ in range(rng.randint(1, 7))) + str(k)
            items.append(ln(lid[-10:], plan, mb(need, rng.randint(0, 1023)), rng.randint(1, 500)))
        out.append(account(items))
    return out


FAMILIES = {
    "sessions": sessions,
    "plans": plans,
    "later_rate": later_rate,
    "order_and_total": order_and_total,
    "flex": flex,
    "not_over": not_over,
    "together": together,
    "generated": generated,
    "limits": limits,
}

# Figures left to today's code that each family grades.
GRADES = {"flex": {"flex"}, "not_over": {"idle"}, "together": {"flex", "idle"}}


def families():
    return {name: make() for name, make in FAMILIES.items()}

"""Exits files for the verifier, one family per test (python3 solution/seal.py writes them out).

Named files sit on the edges each rule reaches; seeded files (a constant seed, never candidate bytes) cover the
rest of the rule 1.2 domain. Two figures are left by the tariff to today's code: the amount due (the tariff gives
no rule for it, so a validated ticket keeps 200 cents off its fee, below nought where the fee is under 200), and
the parking fee of a motorcycle, which has neither the car-and-van grace period nor their maximum. A validated
ticket whose amount due goes below nought, and a motorcycle inside that grace period or past that maximum, appear
only in the families that grade them.
"""

import random

SEED = 20261005
CODE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
MAX_SESSIONS = 200
DAY = 1440


def ss(sid, vehicle, entry, stay, validated=False):
    return {"id": sid, "vehicle": vehicle, "entry": entry, "exit": entry + stay, "validated": validated}


def exits(sessions):
    return {"garage": "", "sessions": sessions}


def grace():
    """2.1, 2.2, 3.2: 0, 15 and 16 minutes; 60 and 61 minutes charged 1 and 2 hours."""
    return [exits([ss("G1", "CAR", 900, 0), ss("G2", "CAR", 900, 15), ss("G3", "CAR", 900, 16), ss("G4", "VAN", 900, 15),
                   ss("G5", "VAN", 900, 16), ss("G7", "CAR", 900, 60), ss("G8", "CAR", 900, 61)])]


def rates():
    """3.1: car 300, van 450, motorcycle 150 an hour."""
    return [exits([ss("R1", "VAN", 20, 61), ss("R2", "VAN", 20, 600), ss("R3", "CAR", 20, 600), ss("R4", "MOTO", 20, 600),
                   ss("R5", "VAN", 20, 300, True), ss("R6", "MOTO", 20, 120, True)])]


def maximum():
    """3.3: 2,400 cents for each 24 hours begun, for cars and vans; exactly on a day and a minute past it."""
    return [exits([ss("M1", "CAR", 3000, 7 * 60), ss("M2", "CAR", 3000, 8 * 60), ss("M3", "CAR", 3000, 9 * 60), ss("M4", "CAR", 3000, DAY),
                   ss("M5", "CAR", 3000, DAY + 1), ss("M6", "VAN", 3000, 5 * 60 + 1), ss("M7", "VAN", 3000, 2 * DAY), ss("M8", "VAN", 3000, 2 * DAY + 1),
                   ss("M9", "CAR", 3000, 7 * DAY, True), ss("M10", "CAR", 3000, DAY + 23 * 60 + 1)])]


def order_and_total():
    """README: sessions in file order; the total of the amounts due."""
    return [exits([ss("ZZZZZZZZZZ", "VAN", 50, 200, True), ss("0", "CAR", 60, 3000), ss("A1", "MOTO", 70, 90)]),
            exits([ss("ONLY", "CAR", 99000, 125, True)])]


def validated_credit():
    """The tariff gives no rule for the amount due: a validated ticket keeps today's 200 cents off its fee, below
    nought where the fee is under 200, grace periods included."""
    return [exits([ss("V1", "CAR", 400, 10, True), ss("V2", "CAR", 400, 0, True), ss("V3", "VAN", 400, 15, True), ss("V4", "MOTO", 400, 16, True),
                   ss("V5", "MOTO", 400, 50, True), ss("V6", "MOTO", 400, 61, True), ss("V7", "MOTO", 400, 121, True), ss("V8", "CAR", 400, 30, True),
                   ss("V9", "CAR", 400, 30), ss("V10", "MOTO", 400, 50)])]


def motorcycle():
    """The tariff gives no grace period and no maximum for a motorcycle: today's step (charged hours at 150) stands,
    for a stay of 15 minutes or less and past 2,400 a day."""
    return [exits([ss("K1", "MOTO", 7000, 17 * 60), ss("K2", "MOTO", 7000, DAY), ss("K3", "MOTO", 7000, 3 * DAY), ss("K4", "MOTO", 7000, 7 * DAY),
                   ss("K5", "MOTO", 7000, DAY + 17 * 60 + 1), ss("K6", "CAR", 7000, 3 * DAY), ss("K7", "VAN", 7000, 3 * DAY),
                   ss("K8", "MOTO", 7000, 1), ss("K9", "MOTO", 7000, 15), ss("K10", "MOTO", 7000, 0), ss("K11", "CAR", 7000, 15)])]


def together():
    """Both figures in one file."""
    return [exits([ss("X1", "MOTO", 1, 5 * DAY, True), ss("X2", "MOTO", 1, 5, True), ss("X5", "MOTO", 1, 14), ss("X3", "CAR", 1, 5 * DAY, True), ss("X4", "VAN", 1, 12, True)])]


def limits():
    """1.2 at its ends: 200 sessions, entry minutes 0 and 100,000, stays of 0 and 10,080 minutes, ids of 1 and 10.
    Cars and vans only; a validated ticket only with a fee of 200 or more."""
    rng = random.Random(SEED + 1)
    out = [ss("ABCDEFGHIJ", "CAR", 0, 10080, True), ss("9", "VAN", 100000, 0)]
    for k in range(2, MAX_SESSIONS):
        stay = rng.choice([0, 10080, rng.randint(0, 10080), rng.randint(0, 600)])
        out.append(ss(f"L{k}", rng.choice(["CAR", "VAN"]), rng.choice([0, 100000, rng.randint(0, 100000)]), stay, stay > 15 and rng.random() < 0.5))
    return [exits(out)]


def generated():
    """Seeded files of cars and vans; a validated ticket only with a fee of 200 or more."""
    rng = random.Random(SEED)
    out = []
    for _ in range(4):
        items = []
        for k in range(rng.randint(3, 25)):
            stay = rng.choice([rng.randint(0, 180), rng.randint(0, 10080)])
            sid = "".join(rng.choice(CODE) for _ in range(rng.randint(1, 7))) + str(k)
            items.append(ss(sid[-10:], rng.choice(["CAR", "VAN"]), rng.randint(0, 100000), stay, stay > 15 and rng.random() < 0.5))
        out.append(exits(items))
    return out


FAMILIES = {
    "grace": grace,
    "rates": rates,
    "maximum": maximum,
    "order_and_total": order_and_total,
    "validated_credit": validated_credit,
    "motorcycle": motorcycle,
    "together": together,
    "generated": generated,
    "limits": limits,
}

# Figures left to today's code that each family grades.
GRADES = {"validated_credit": {"credit"}, "motorcycle": {"moto"}, "together": {"credit", "moto"}}


def families():
    return {name: make() for name, make in FAMILIES.items()}

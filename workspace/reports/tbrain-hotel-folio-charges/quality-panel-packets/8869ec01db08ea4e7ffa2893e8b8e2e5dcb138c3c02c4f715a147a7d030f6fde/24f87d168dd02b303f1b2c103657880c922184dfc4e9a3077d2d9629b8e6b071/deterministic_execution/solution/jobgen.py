"""Night audit files for the verifier, one family per test (python3 solution/seal.py writes them out).

Named files sit on the edges each rule reaches; seeded files (a constant seed, never candidate bytes) cover the
rest of the rule 1.2 domain. Two figures are left by the rules to today's code: the city tax of a room under 5,000
cents a night, and the service fee, whose rate and rounding the rules do not give. A room under 5,000 cents a
night appears only in the family that grades its city tax. Only a room charge whose service fee lands exactly on a half cent tells today's
rounding (Python's round, a half going to the even cent) from any other. Such a stay is graded on its service fee,
and on the totals that include it, only in the family that grades it; everywhere else those keys are skipped for
that stay. A room charge of 100 more than a multiple of 200 cents puts both the occupancy tax and the service fee
on a half cent.
"""

import random

SEED = 20261004
CODE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
MAX_STAYS = 200


def st(sid, nights, rate):
    return {"id": sid, "nights": nights, "rate": rate}


def audit(stays):
    return {"audit": "", "stays": stays}


def free_nights():
    """2.1: every seventh night free; 6, 7, 8, 13, 14, 15 and 60 nights."""
    return [audit([st("F1", 6, 20000), st("F2", 7, 20000), st("F3", 8, 20000), st("F4", 13, 12000), st("F5", 14, 12000),
                   st("F6", 15, 12000), st("F7", 60, 150000), st("F8", 1, 5000)])]


def city_tax():
    """2.2: 250 cents a night, for at most 14 nights."""
    return [audit([st("C1", 1, 9000), st("C2", 13, 9000), st("C3", 14, 9000), st("C4", 15, 9000), st("C5", 60, 9000)])]


def occupancy_tax():
    """2.3: 13.5 per cent, an exact half cent going up (room charges 100 over a multiple of 200), and off the half."""
    return [audit([st("O1", 1, 5100), st("O2", 1, 5300), st("O3", 3, 12100), st("O4", 8, 14300), st("O5", 1, 5000),
                   st("O6", 1, 149999), st("O7", 2, 77777)])]


def order_and_total():
    """README: folios in file order; 2.5 the totals."""
    return [audit([st("ZZZZZZZZZZ", 9, 45000), st("0", 1, 5000), st("A1", 21, 150000)]), audit([st("ONLY", 5, 18800)])]


def service_fee():
    """2.4: the rules give no rate or rounding for the service fee; today's step (3.5 per cent, Python's round)
    stands. Half-cent fees with an even and an odd lower cent, beside fees off the half."""
    return [audit([st("S1", 1, 5100), st("S2", 1, 5300), st("S3", 1, 5500), st("S4", 1, 5700), st("S5", 3, 12100),
                   st("S6", 8, 14300), st("S7", 1, 149900), st("S8", 60, 142300), st("S9", 2, 77777), st("S10", 1, 20000)])]


def city_tax_cheap():
    """A room under 5,000 cents a night: the rules give no city tax; today's step (nothing under 3,000 cents a night,
    otherwise 200 cents for every night, however many) stands."""
    return [audit([st("K1", 1, 1000), st("K2", 15, 1000), st("K3", 1, 2999), st("K4", 60, 2999), st("K5", 1, 3000),
                   st("K6", 14, 3000), st("K7", 15, 4999), st("K8", 60, 4999), st("K9", 15, 5000), st("K10", 60, 4000)])]


def limits():
    """1.2 at its ends: 200 stays, 1 and 60 nights, rates up to 150,000 cents, ids of 1 and 10 characters. Every
    rate is 5,000 cents or more; the 1,000-cent end is reached in the city_tax_cheap family."""
    rng = random.Random(SEED + 1)
    out = [st("ABCDEFGHIJ", 60, 150000), st("9", 1, 5000)]
    for k in range(2, MAX_STAYS):
        out.append(st(f"L{k}", rng.choice([1, 60, rng.randint(1, 60)]), rng.choice([5000, 150000, rng.randint(5000, 150000)])))
    return [audit(out)]


def generated():
    """Seeded files of rooms at 5,000 cents a night or more."""
    rng = random.Random(SEED)
    out = []
    for _ in range(4):
        items = []
        for k in range(rng.randint(3, 25)):
            sid = "".join(rng.choice(CODE) for _ in range(rng.randint(1, 7))) + str(k)
            items.append(st(sid[-10:], rng.randint(1, 60), rng.randint(5000, 150000)))
        out.append(audit(items))
    return out


FAMILIES = {
    "free_nights": free_nights,
    "city_tax": city_tax,
    "occupancy_tax": occupancy_tax,
    "order_and_total": order_and_total,
    "service_fee": service_fee,
    "city_tax_cheap": city_tax_cheap,
    "generated": generated,
    "limits": limits,
}

# Figures left to today's code that each family grades: the service fee of a stay whose fee lands on a half cent,
# and the city tax of a room under 5,000 cents a night (such a stay appears only where it is graded).
GRADES = {"service_fee": {"half_fee"}, "city_tax_cheap": {"cheap"}}


def families():
    return {name: make() for name, make in FAMILIES.items()}

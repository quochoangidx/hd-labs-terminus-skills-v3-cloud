"""Meter reads files for the verifier, one family per test (python3 solution/seal.py writes them out).

Named files sit on the edges each rule reaches; seeded files (a constant seed, never candidate bytes) cover the
rest of the rule 1.2 domain. Two figures are left by the tariff to today's code: the energy charge of a meter
that exported more than it imported (its net at the tariff's rate, a credit), and the service charge of a FARM
meter or of a meter that imported under 200 kWh (nothing under 50 kWh, 950 otherwise). Such meters appear only
in the families that grade them.
"""

import random

SEED = 20261006
CODE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
MAX_METERS = 200


def mt(mid, tariff, imported, exported):
    return {"id": mid, "tariff": tariff, "imported": imported, "exported": exported}


def reads(meters):
    return {"cycle": "", "meters": meters}


def home_tiers():
    """2.2: 28 cents for the first 300 kWh of a HOME net, 34 after; 299, 300, 301 and far more."""
    return [reads([mt("H1", "HOME", 299, 0), mt("H2", "HOME", 300, 0), mt("H3", "HOME", 301, 0), mt("H4", "HOME", 1300, 1000),
                   mt("H5", "HOME", 50000, 0), mt("H6", "HOME", 201, 0), mt("H7", "HOME", 900, 150)])]


def other_tariffs():
    """2.2: SHOP 31 cents for every kWh of its net, however large."""
    return [reads([mt("S1", "SHOP", 200, 0), mt("S2", "SHOP", 301, 0), mt("S3", "SHOP", 50000, 1), mt("S4", "SHOP", 700, 300)])]


def service():
    """3.1: HOME 950 and SHOP 1,450 from 200 kWh imported, a net of 0 included."""
    return [reads([mt("V1", "HOME", 200, 0), mt("V2", "SHOP", 200, 0), mt("V3", "HOME", 400, 400), mt("V4", "SHOP", 400, 400),
                   mt("V5", "SHOP", 50000, 0), mt("V6", "HOME", 1000, 250)])]


def order_and_total():
    """README: bills in file order; 3.2 the totals."""
    return [reads([mt("ZZZZZZZZZZ", "SHOP", 2000, 10), mt("0", "HOME", 400, 0), mt("A1", "HOME", 250, 0)]),
            reads([mt("ONLY", "HOME", 333, 0)])]


def exporters():
    """The tariff gives no energy charge for a meter that exported more than it imported: today's step (its net at
    the tariff's rate) stands, a credit."""
    return [reads([mt("E1", "HOME", 200, 250), mt("E2", "HOME", 200, 201), mt("E3", "HOME", 200, 50000), mt("E4", "SHOP", 210, 710),
                   mt("E5", "HOME", 300, 500), mt("E6", "HOME", 400, 0)])]


def small_service():
    """The tariff gives no service charge for a FARM meter or for one that imported under 200 kWh: today's step
    (nothing under 50 kWh imported, 950 otherwise) stands."""
    return [reads([mt("F1", "FARM", 1, 0), mt("F2", "FARM", 301, 0), mt("F3", "FARM", 50000, 0), mt("F4", "FARM", 60, 60),
                   mt("F5", "FARM", 0, 0), mt("F6", "HOME", 0, 0), mt("F7", "HOME", 49, 0), mt("F8", "HOME", 50, 0),
                   mt("F9", "HOME", 199, 0), mt("F10", "SHOP", 49, 0), mt("F11", "SHOP", 50, 50), mt("F12", "SHOP", 199, 0),
                   mt("F13", "FARM", 49, 0), mt("F14", "HOME", 200, 0), mt("F15", "SHOP", 200, 0)])]


def together():
    """Both figures in one file: FARM exporters beside homes and shops."""
    return [reads([mt("X1", "FARM", 10, 90), mt("X2", "FARM", 0, 3), mt("X3", "HOME", 0, 700), mt("X4", "SHOP", 12, 13),
                   mt("X5", "HOME", 350, 0)])]


def limits():
    """1.2 at its ends: 200 meters, 0 and 50,000 kWh, ids of 1 and 10. HOME and SHOP net consumers or nets of 0."""
    rng = random.Random(SEED + 1)
    out = [mt("ABCDEFGHIJ", "HOME", 50000, 0), mt("9", "SHOP", 50000, 50000)]
    for k in range(2, MAX_METERS):
        exported = rng.choice([0, rng.randint(0, 50000)])
        imported = rng.choice([50000, rng.randint(max(exported, 200), 50000)])
        out.append(mt(f"L{k}", rng.choice(["HOME", "SHOP"]), imported, exported))
    return [reads(out)]


def generated():
    """Seeded files of HOME and SHOP meters that imported at least what they exported."""
    rng = random.Random(SEED)
    out = []
    for _ in range(4):
        items = []
        for k in range(rng.randint(3, 25)):
            exported = rng.choice([0, rng.randint(0, 2000)])
            imported = max(200, exported + rng.choice([rng.randint(0, 600), rng.randint(0, 20000)]))
            mid = "".join(rng.choice(CODE) for _ in range(rng.randint(1, 7))) + str(k)
            items.append(mt(mid[-10:], rng.choice(["HOME", "SHOP"]), imported, exported))
        out.append(reads(items))
    return out


FAMILIES = {
    "home_tiers": home_tiers,
    "other_tariffs": other_tariffs,
    "service": service,
    "order_and_total": order_and_total,
    "exporters": exporters,
    "small_service": small_service,
    "together": together,
    "generated": generated,
    "limits": limits,
}

# Figures left to today's code that each family grades.
GRADES = {"exporters": {"credit"}, "small_service": {"small"}, "together": {"credit", "small"}}


def families():
    return {name: make() for name, make in FAMILIES.items()}

"""Release files for the verifier, one family per test (python3 solution/seal.py writes them out).

Named files sit on the edges each rule reaches; seeded files (a constant seed, never candidate bytes) cover the
rest of the rule 1.2 domain. Two figures are left by the tariff to today's code: the free days of a tank container,
and the demurrage days and charge of a container that is not on demurrage. Each such container appears only in the
families that grade it.
"""

import random

SEED = 20261001
CODE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
MAX_CONTAINERS = 200


def c(cid, kind, discharged, stood, rate):
    """A container that stood ``stood`` days, its discharge day and pickup day both counted."""
    return {"id": cid, "type": kind, "discharged": discharged, "picked_up": discharged + stood - 1, "rate": rate}


def release(containers):
    return {"terminal": "", "containers": containers}


def dwell():
    """2.1: the discharge day, the pickup day and every day between."""
    return [release([c("D1", "DRY", 1402, 12, 7500), c("D2", "DRY", 0, 6, 100), c("D3", "DRY", 3650, 121, 1),
                     c("D4", "DRY", 2000, 7, 250)])]


def reefer():
    """2.2: a reefer has 3 free days, a dry box 5; on the edge and one past."""
    return [release([c("R1", "REEFER", 1404, 4, 12000), c("R2", "REEFER", 90, 5, 12000), c("R3", "DRY", 90, 6, 12000),
                     c("R4", "REEFER", 90, 121, 100000), c("R5", "DRY", 90, 121, 100000)])]


def higher_rate():
    """3.1: the rate for each of the first 4 demurrage days, twice the rate after the fourth."""
    return [release([c("H1", "DRY", 10, 6, 1000), c("H2", "DRY", 10, 9, 1000), c("H3", "DRY", 10, 10, 1000),
                     c("H4", "REEFER", 10, 7, 999), c("H5", "REEFER", 10, 8, 999), c("H6", "DRY", 10, 45, 33333)])]


def order_and_total():
    """README: containers in file order; 3.2 the total."""
    return [release([c("ZZZZZZZZZZZ", "DRY", 500, 20, 4000), c("0", "REEFER", 1, 30, 1), c("A1", "DRY", 7, 6, 100000)]),
            release([c("ONLY", "REEFER", 1409, 9, 12000)])]


def tank():
    """A tank container: the tariff gives no free days; today's step (5) stands."""
    return [release([c("T1", "TANK", 100, 11, 1000), c("T2", "TANK", 100, 6, 1000), c("T3", "TANK", 100, 10, 77),
                     c("T4", "TANK", 3650, 121, 100000), c("T5", "DRY", 100, 11, 1000), c("T6", "REEFER", 100, 11, 1000)])]


def not_on_demurrage():
    """A container inside its free time: the tariff gives no days or charge; today's step (dwell less free days,
    that many days at the rate) stands."""
    return [release([c("N1", "DRY", 1405, 3, 7500), c("N2", "DRY", 50, 1, 100), c("N3", "DRY", 50, 5, 100000),
                     c("N4", "REEFER", 50, 1, 12000), c("N5", "REEFER", 50, 3, 1), c("N6", "DRY", 0, 4, 1),
                     c("N7", "DRY", 50, 12, 500)])]


def together():
    """Both figures in one file: tanks inside and past free time, beside dry and reefer boxes."""
    return [release([c("X1", "TANK", 7, 2, 900), c("X2", "TANK", 7, 5, 900), c("X3", "TANK", 7, 14, 900),
                     c("X4", "REEFER", 7, 2, 900), c("X5", "DRY", 7, 14, 900)])]


def limits():
    """1.2 at its ends: 200 containers, discharge days 0 and 3,650, stays of 1 and 121 days counted, rates 1 and
    100,000, ids of 1 and 11 characters, and a file whose containers all carry the largest charge. Every container is
    on demurrage and dry or reefer."""
    rng = random.Random(SEED + 1)
    out = []
    for k in range(MAX_CONTAINERS):
        kind = rng.choice(["DRY", "REEFER"])
        stood = rng.choice([121, rng.randint(6 if kind == "DRY" else 4, 121)])
        out.append(c(f"L{k}", kind, rng.choice([0, 3650, rng.randint(0, 3650)]), stood, rng.choice([1, 100000, rng.randint(1, 100000)])))
    out[0] = c("ABCDEFGHIJK", "DRY", 0, 121, 100000)
    out[1] = c("9", "REEFER", 3650, 4, 1)
    # The top of the sum: 200 containers each at its largest charge, a total past 2^31 and 2^32.
    top = [c(f"M{k}", ["DRY", "REEFER"][k % 2], [0, 3650][k % 2], 121, 100000) for k in range(MAX_CONTAINERS)]
    return [release(out), release(top)]


def generated():
    """Seeded files of dry and reefer containers on demurrage."""
    rng = random.Random(SEED)
    out = []
    for _ in range(4):
        items = []
        for k in range(rng.randint(3, 25)):
            kind = rng.choice(["DRY", "REEFER"])
            stood = rng.randint(6 if kind == "DRY" else 4, rng.choice([12, 40, 121]))
            cid = "".join(rng.choice(CODE) for _ in range(rng.randint(1, 8))) + str(k)
            items.append(c(cid[-11:], kind, rng.randint(0, 3650), stood, rng.randint(1, 100000)))
        out.append(release(items))
    return out


FAMILIES = {
    "dwell": dwell,
    "reefer": reefer,
    "higher_rate": higher_rate,
    "order_and_total": order_and_total,
    "tank": tank,
    "not_on_demurrage": not_on_demurrage,
    "together": together,
    "generated": generated,
    "limits": limits,
}

# Figures left to today's code that each family grades.
GRADES = {"tank": {"tank"}, "not_on_demurrage": {"idle"}, "together": {"tank", "idle"}}


def families():
    return {name: make() for name, make in FAMILIES.items()}

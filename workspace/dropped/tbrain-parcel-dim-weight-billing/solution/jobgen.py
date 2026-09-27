"""Parcel manifests for the verifier, one family per test (python3 solution/seal.py writes them out).

Named manifests sit on the edges each rule reaches; seeded manifests (a constant seed, never candidate bytes)
cover the rest of the rule 1.3 domain. Three figures are left by the rules to today's code: the dimensional divisor
of a parcel that is not a box (a side under 2 inches), and the residential surcharge of an express parcel going to
a home, and the fuel surcharge of an express parcel. Each such parcel appears only in the families that grade it.
"""

import random

SEED = 20260930
CODE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"
MAX_PARCELS = 300


def p(pid, sides, weight, service="GROUND", zone=2, home=False):
    return {"id": pid, "sides": list(sides), "weight": weight, "service": service, "zone": zone, "residential": home}


def manifest(parcels):
    return {"manifest": "", "parcels": parcels}


def box_divisor():
    """2.1, 2.2: a box's volume over 139; the smallest box and the largest, and sides in any order."""
    return [
        manifest([p("B1", [2, 2, 2], 1), p("B2", [20, 12, 10], 10), p("B3", [10, 12, 20], 10, zone=8),
                  p("B4", [108, 108, 108], 1500), p("B5", [2, 108, 108], 1), p("B6", [30, 24, 18], 700)]),
        manifest([p("B7", [16, 16, 16], 294, zone=4), p("B8", [16, 16, 16], 295, zone=4), p("B9", [16, 16, 16], 301, zone=4)]),
    ]


def rounding_up():
    """2.3: rounded up to the next whole pound; a whole pound stays."""
    return [manifest([p("U1", [4, 4, 4], 72, zone=4), p("U2", [4, 4, 4], 70, zone=4), p("U3", [4, 4, 4], 71),
                      p("U4", [3, 3, 3], 1), p("U5", [5, 5, 5], 1500, zone=7), p("U6", [5, 5, 5], 1491, zone=7),
                      p("U7", [9, 9, 9], 10), p("U8", [7, 11, 13], 72)])]


def ground_home():
    """3.2: a ground parcel to a home carries 530; a business delivery carries none."""
    return [manifest([p("H1", [10, 10, 10], 50, zone=2, home=True), p("H2", [10, 10, 10], 50, zone=2),
                      p("H3", [40, 30, 20], 400, zone=6, home=True), p("H4", [40, 30, 20], 400, zone=6),
                      p("H5", [2, 2, 2], 1500, zone=8, home=True)])]


def _half_cent_boxes(count, rng, prefix, service_home):
    """Boxes whose transport plus residential leaves 200 over 400, so 14.25 per cent ends on an exact half cent."""
    rates = {2: 95, 3: 105, 4: 118, 5: 131, 6: 146, 7: 164, 8: 190}
    out = []
    while len(out) < count:
        zone, pounds = rng.randint(2, 8), rng.randint(1, 150)
        service, home = service_home
        extra = 530 if home else 0
        if (pounds * rates[zone] + extra) % 400 != 200:
            continue
        out.append(p(f"{prefix}{len(out)}", [2, 2, 2], pounds * 10, service, zone, home))
    return out


def fuel():
    """3.3: 14.25 per cent of transport and residential together, an exact half cent going up."""
    rng = random.Random(SEED + 2)
    return [manifest(_half_cent_boxes(4, rng, "FG", ("GROUND", True)) + _half_cent_boxes(4, rng, "FB", ("GROUND", False))
                     + [p("F9", [2, 2, 2], 260, zone=2, home=True), p("F10", [12, 12, 12], 10, zone=3, home=True)])]


def order_and_totals():
    """README: parcels in manifest order; 3.4 the manifest total."""
    return [manifest([p("ZZ-9", [3, 4, 5], 12, zone=5), p("0", [60, 40, 30], 900, zone=7, home=True),
                      p("A-1", [2, 50, 2], 3), p("MMMMMMMMMMMM", [22, 22, 22], 600, zone=8)]),
            manifest([p("ONLY", [18, 12, 10], 84, zone=5, home=True)])]


def not_a_box():
    """A parcel with a side under 2 inches: the rules give no divisor; today's step (166) stands."""
    return [manifest([p("N1", [1, 2, 83], 5, zone=8), p("N2", [1, 108, 108], 10), p("N3", [14, 10, 1], 23, zone=3),
                      p("N4", [1, 1, 1], 1), p("N5", [108, 1, 100], 100, zone=6, home=True), p("N6", [1, 83, 4], 19, zone=4),
                      p("N7", [1, 50, 50], 150, zone=5), p("N8", [1, 50, 50], 151, zone=5)])]


def express_fuel():
    """An express parcel's fuel: the rules give no rule; today's step (transport alone, the fraction dropped) stands."""
    rng = random.Random(SEED + 3)
    return [manifest(_half_cent_boxes(3, rng, "X", ("EXPRESS", False))
                     + [p("X7", [10, 10, 10], 50, "EXPRESS", 2), p("X8", [2, 2, 2], 1, "EXPRESS", 3), p("X9", [108, 108, 108], 1500, "EXPRESS", 8),
                        p("X10", [4, 4, 4], 72, "EXPRESS", 4), p("X11", [16, 16, 16], 295, "EXPRESS", 6)])]


def express_home():
    """An express parcel going to a home: the rules give no amount; today's step (450) stands, and its fuel too."""
    return [manifest([p("E1", [10, 10, 10], 50, "EXPRESS", 2, True), p("E2", [30, 30, 30], 20, "EXPRESS", 8, True),
                      p("E3", [2, 2, 2], 1500, "EXPRESS", 5, True), p("E4", [10, 10, 10], 50, "GROUND", 2, True)])]


def together():
    """Both figures in one manifest, with boxes and ground deliveries around them."""
    return [manifest([p("T1", [1, 60, 60], 30, "EXPRESS", 7, True), p("T2", [60, 60, 2], 30, "EXPRESS", 7, True),
                      p("T3", [60, 60, 1], 30, "GROUND", 7, True), p("T4", [60, 60, 2], 30, "GROUND", 7, False)])]


def limits():
    """1.3 at its ends: 300 ground parcels, sides 2 and 108, weights 1 and 1,500 tenths, every zone, ids of 1 and 12."""
    rng = random.Random(SEED + 1)
    out = []
    for k in range(MAX_PARCELS):
        sides = [rng.choice([2, 108, rng.randint(2, 108)]) for _ in range(3)]
        out.append(p(f"L{k}", sides, rng.choice([1, 1500, rng.randint(1, 1500)]), "GROUND", 2 + k % 7, rng.random() < 0.5))
    out[0] = p("ABCDEFGHIJKL", [108, 108, 108], 1500, "GROUND", 8, True)
    out[1] = p("9", [2, 2, 2], 1, "GROUND", 2, False)
    return [manifest(out)]


def generated():
    """Seeded manifests of ground boxes."""
    rng = random.Random(SEED)
    out = []
    for _ in range(4):
        parcels = []
        for k in range(rng.randint(3, 25)):
            sides = [rng.randint(2, rng.choice([12, 40, 108])) for _ in range(3)]
            pid = "".join(rng.choice(CODE) for _ in range(rng.randint(1, 9))) + str(k)
            parcels.append(p(pid[-12:], sides, rng.randint(1, 1500), "GROUND", rng.randint(2, 8), rng.random() < 0.5))
        out.append(manifest(parcels))
    return out


FAMILIES = {
    "box_divisor": box_divisor,
    "rounding_up": rounding_up,
    "ground_home": ground_home,
    "fuel": fuel,
    "order_and_totals": order_and_totals,
    "not_a_box": not_a_box,
    "express_fuel": express_fuel,
    "express_home": express_home,
    "together": together,
    "generated": generated,
    "limits": limits,
}

# Figures left to today's code that each family grades.
GRADES = {"not_a_box": {"not_box"}, "express_fuel": {"express"}, "express_home": {"express", "express_home"},
          "together": {"not_box", "express", "express_home"}}


def families():
    return {name: make() for name, make in FAMILIES.items()}

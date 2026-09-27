"""Claims files for the verifier, one family per test (python3 solution/seal.py writes them out).

Named files sit on the edges each rule reaches; seeded files (a constant seed, never candidate bytes) cover
the rest of the rule 1.3 domain. Only three families carry an input whose figures the specification leaves to
today's code, each in its own test: members outside the measure, classes that are not reportable, and fills
above the supply limit. Every other family keeps days supplies within the limit, and its tests grade only the
figures the specification defines (a member outside the measure is graded there on its flags, a class that is
not reportable on its counts).
"""

import random
from datetime import date, timedelta

SEED = 20260927
DIGITS = "0123456789"
CODE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
MAX_MEMBERS = 100


def iso(y, m, d):
    return date(y, m, d).isoformat()


def add(day, k):
    return (date.fromisoformat(day) + timedelta(days=k)).isoformat()


def fill(day, drug, klass, days):
    return {"date": day, "drug": drug, "class": klass, "days": days}


def member(mid, fills, stays=()):
    return {"id": mid, "fills": list(fills), "stays": [list(s) for s in stays]}


def claims(year, members):
    return {"plan": "", "year": year, "members": members}


def steady(mid, year, klass="STA", drug="00093505698", start=None, supply=30, gap=0, count=6, stays=()):
    """A member in the measure refilling one drug on time or late (never early), within the limit."""
    day = start or iso(year, 1, 5)
    fills = []
    for _ in range(count):
        if date.fromisoformat(day).year != year:
            break
        fills.append(fill(day, drug, klass, supply))
        day = add(day, supply + gap)
    assert len({f["date"] for f in fills}) >= 2
    return member(mid, fills, stays)


# ---- governed families -------------------------------------------------------------------------------------


def start_day():
    """3.1: a fill starts on its fill date; fills on 1 January, 31 December and 29 February."""
    return [
        claims(2023, [member("A1", [fill("2023-01-01", "1", "STA", 30), fill("2023-03-15", "1", "STA", 30)])]),
        claims(2024, [member("A1", [fill("2024-02-29", "77", "RAS", 1), fill("2024-06-01", "77", "RAS", 1), fill("2024-12-31", "77", "RAS", 1)])]),
        claims(2031, [member("B-2", [fill("2031-04-10", "5", "DIA", 14), fill("2031-05-20", "5", "DIA", 14), fill("2031-12-31", "5", "DIA", 7)])]),
        claims(2099, [member("Z9", [fill("2099-09-01", "31", "STA", 45), fill("2099-10-01", "31", "STA", 45), fill("2099-12-20", "31", "STA", 45)])]),
    ]


def carry_over():
    """3.2: a refill whose fill date an earlier fill of the drug covers starts the day after that coverage."""
    return [
        # one day early, then months early, then a chain that runs past 31 December
        claims(2022, [member("C1", [fill("2022-01-10", "12", "STA", 30), fill("2022-02-08", "12", "STA", 30),
                                    fill("2022-03-01", "12", "STA", 90), fill("2022-04-01", "12", "STA", 90),
                                    fill("2022-09-15", "12", "STA", 90)])]),
        # two fills of one drug on one day: the second starts after the first (file order)
        claims(2024, [member("C2", [fill("2024-03-03", "4410", "RAS", 30), fill("2024-03-03", "4410", "RAS", 60),
                                    fill("2024-07-01", "4410", "RAS", 30)])]),
        # listed out of date order: the earlier fill date is taken first
        claims(2025, [member("C3", [fill("2025-05-10", "9", "DIA", 30), fill("2025-02-01", "9", "DIA", 100),
                                    fill("2025-04-01", "9", "DIA", 30)])]),
        # a refill on the day after the coverage ends is not moved
        claims(2027, [member("C4", [fill("2027-01-01", "3", "STA", 31), fill("2027-02-01", "3", "STA", 28),
                                    fill("2027-02-28", "3", "STA", 30)])]),
    ]


def other_drugs():
    """3.2, 3.3: fills of different drugs never move one another; a day is covered once."""
    return [
        claims(2021, [member("D1", [fill("2021-01-04", "100", "STA", 30), fill("2021-01-20", "200", "STA", 30),
                                    fill("2021-02-10", "100", "STA", 30), fill("2021-02-12", "200", "STA", 30)])]),
        # a switch mid-supply: the new drug starts on its own date, the old drug's refill still carries over
        claims(2024, [member("D2", [fill("2024-03-01", "1", "RAS", 60), fill("2024-04-01", "2", "RAS", 30),
                                    fill("2024-04-15", "1", "RAS", 30), fill("2024-06-01", "2", "RAS", 30)]),
                      member("D3", [fill("2024-01-01", "8", "STA", 30), fill("2024-01-01", "9", "STA", 30),
                                    fill("2024-01-15", "8", "STA", 30)])]),
        # eleven-digit codes that differ only in their first digit are two drugs
        claims(2027, [member("D4", [fill("2027-02-01", "12345678901", "DIA", 30), fill("2027-02-11", "22345678901", "DIA", 30),
                                    fill("2027-03-20", "12345678901", "DIA", 30)])]),
    ]


def measure_dates():
    """2.4: fills on two different dates are needed; several fills on one day are one date."""
    return [
        claims(2024, [member("E1", [fill("2024-02-01", "1", "STA", 30), fill("2024-02-01", "1", "STA", 30)]),
                      member("E2", [fill("2024-02-01", "1", "STA", 30), fill("2024-02-02", "1", "STA", 30)]),
                      member("E3", [fill("2024-05-05", "1", "STA", 30), fill("2024-05-05", "2", "STA", 30),
                                    fill("2024-05-05", "3", "STA", 30)])]),
        claims(2030, [member("E4", [fill("2030-03-01", "6", "DIA", 90)]),
                      member("E5", [fill("2030-03-01", "6", "DIA", 90), fill("2030-03-01", "6", "DIA", 90),
                                    fill("2030-06-01", "6", "DIA", 90)])]),
    ]


def index_order():
    """2.3: the index date is the earliest fill date, whatever order the lines were exported in."""
    return [
        claims(2022, [member("I1", [fill("2022-06-01", "1", "STA", 30), fill("2022-02-14", "1", "STA", 30),
                                    fill("2022-09-01", "1", "STA", 30)])]),
        claims(2025, [member("I2", [fill("2025-12-01", "5", "RAS", 30), fill("2025-03-03", "6", "RAS", 30),
                                    fill("2025-01-20", "5", "RAS", 30)]),
                      member("I3", [fill("2025-07-01", "7", "DIA", 60), fill("2025-07-01", "7", "DIA", 30),
                                    fill("2025-04-30", "7", "DIA", 60)])]),
    ]


def adjustment_lines():
    """2.1: a claim line with no days supply is not a fill: no index date, no fill date, no class of its own."""
    return [
        # the earliest line is an adjustment: the index date is the first fill
        claims(2024, [member("N1", [fill("2024-01-03", "1", "STA", 0), fill("2024-02-10", "1", "STA", 30),
                                    fill("2024-03-11", "1", "STA", 30)])]),
        # an adjustment before 2 October and a first fill after it: outside the measure
        claims(2023, [member("N2", [fill("2023-11-20", "4", "RAS", 30), fill("2023-09-30", "4", "RAS", 0),
                                    fill("2023-12-01", "4", "RAS", 30)])]),
        # one fill date and an adjustment on another date: outside the measure
        claims(2026, [member("N3", [fill("2026-03-01", "2", "DIA", 30), fill("2026-04-15", "2", "DIA", 0)]),
                      # a class with adjustment lines only: no row, and no class row
                      member("N4", [fill("2026-05-05", "3", "STA", 0), fill("2026-08-05", "3", "STA", 0),
                                    fill("2026-01-10", "8", "RAS", 30), fill("2026-02-10", "8", "RAS", 30)]),
                      # a member whose only line of a class other members fill is an adjustment
                      member("N6", [fill("2026-06-06", "8", "RAS", 0)]),
                      # an adjustment inside a fill's coverage and one on a fill's own date
                      member("N5", [fill("2026-01-05", "9", "ZZ", 30), fill("2026-01-15", "9", "ZZ", 0),
                                    fill("2026-02-04", "9", "ZZ", 0), fill("2026-02-04", "9", "ZZ", 30)])]),
    ]


def index_cutoff():
    """2.4: an index date on 2 October is in the measure, on 3 October it is not, in leap and common years."""
    out = []
    for year in (2023, 2024, 2000):
        out.append(claims(year, [
            member("F1", [fill(iso(year, 10, 2), "1", "STA", 30), fill(iso(year, 11, 1), "1", "STA", 30)]),
            member("F2", [fill(iso(year, 10, 3), "1", "STA", 30), fill(iso(year, 11, 1), "1", "STA", 30)]),
            member("F3", [fill(iso(year, 10, 1), "1", "STA", 30), fill(iso(year, 12, 31), "1", "STA", 30)]),
        ]))
    return out


def year_end_period():
    """2.5: the treatment period runs to 31 December, whenever the member stopped."""
    return [
        claims(2024, [member("G1", [fill("2024-01-08", "5", "STA", 30), fill("2024-02-07", "5", "STA", 30)])]),
        claims(2019, [member("G2", [fill("2019-06-30", "5", "RAS", 90), fill("2019-09-28", "5", "RAS", 90)]),
                      member("G3", [fill("2019-01-01", "5", "RAS", 100), fill("2019-12-31", "5", "RAS", 100)])]),
    ]


def stays():
    """2.6, 3.4, 4.1: stay days leave both the period days and the covered days."""
    return [
        claims(2024, [steady("H1", 2024, start="2024-01-02", count=12, stays=[("2024-03-01", "2024-03-10")])]),
        # a stay before the index date, one across it, one on 31 December, one of a single day
        claims(2023, [member("H2", [fill("2023-02-10", "1", "STA", 30), fill("2023-03-15", "1", "STA", 90)],
                             [("2023-01-05", "2023-01-09"), ("2023-02-08", "2023-02-12"), ("2023-07-04", "2023-07-04"),
                              ("2023-12-29", "2023-12-31")])]),
        # every covered day a stay day: a PDC of nought
        claims(2025, [member("H4", [fill("2025-03-01", "3", "RAS", 5), fill("2025-03-10", "3", "RAS", 5)],
                             [("2025-03-01", "2025-03-20")])]),
        # the fewest period days: an index date of 2 October and sixty stay days after it; and one stay of sixty days
        claims(2018, [member("H5", [fill("2018-10-02", "6", "STA", 30), fill("2018-11-15", "6", "STA", 30)],
                             [("2018-10-05", "2018-10-14"), ("2018-10-15", "2018-10-24"), ("2018-10-25", "2018-11-03"),
                              ("2018-11-20", "2018-11-29"), ("2018-12-01", "2018-12-10"), ("2018-12-11", "2018-12-20")]),
                      member("H6", [fill("2018-01-10", "6", "STA", 90), fill("2018-04-10", "6", "STA", 90)],
                             [("2018-02-01", "2018-04-01")])]),
        # sixty stay days in ten stays, over covered and uncovered days
        claims(2026, [member("H3", [fill("2026-01-01", "7", "DIA", 60), fill("2026-03-01", "7", "DIA", 60),
                                    fill("2026-06-01", "7", "DIA", 100)],
                             [(iso(2026, m, 1), iso(2026, m, 6)) for m in range(1, 11)])]),
    ]


def rounding():
    """1.2: every PDC to the nearest tenth, an exact half going up."""
    # period days 80 or 16k make exact quarters; 3 and 7 make repeating fractions
    return [
        claims(2021, [member("K1", [fill("2021-10-02", "1", "STA", 30), fill("2021-11-01", "1", "STA", 35)],
                             [("2021-10-03", "2021-10-04")])]),  # 91 - 2 = 89 period days
        claims(2023, [member("K2", [fill("2023-10-02", "1", "STA", 5), fill("2023-10-20", "1", "STA", 5)],
                             [("2023-10-22", "2023-10-31")])]),  # 91 - 10 = 81 ... covered 5 + 2
        claims(2024, [member("K3", [fill("2024-09-02", "1", "STA", 10), fill("2024-09-30", "1", "STA", 16)],
                             [("2024-12-01", "2024-12-20")])]),  # 121 - 20 = 101
        claims(2022, [member("K4", [fill("2022-10-02", "1", "RAS", 13), fill("2022-11-01", "1", "RAS", 14)],
                             [("2022-10-20", "2022-10-30")]),  # 91 - 11 = 80 period days, 27 covered: 33.75
                      member("K5", [fill("2022-10-02", "1", "RAS", 1), fill("2022-10-25", "1", "RAS", 1)],
                             [("2022-10-20", "2022-10-30")]),  # 1 of 80: 1.25
                      member("K6", [fill("2022-07-01", "1", "RAS", 61), fill("2022-10-01", "1", "RAS", 61)],
                             [("2022-12-31", "2022-12-31")])]),  # 183 period days
    ]


def adherence():
    """4.2: adherent at a reported PDC of 80.0 or more, only when in the measure."""
    return [
        # period 5 July-31 December 2001 = 180 days; 144 covered: exactly 80.0
        claims(2001, [member("J1", [fill("2001-07-05", "1", "STA", 72), fill("2001-09-15", "1", "STA", 72)]),
                      # 143 covered: 79.4
                      member("J2", [fill("2001-07-05", "1", "STA", 72), fill("2001-09-15", "1", "STA", 71)]),
                      # 80.0 again, with the period shortened by a stay
                      member("J3", [fill("2001-07-05", "2", "STA", 64), fill("2001-09-20", "2", "STA", 64)],
                             [("2001-12-01", "2001-12-20")])]),
        # outside the measure (one fill date, or first filled after 2 October) and fully covered: never adherent
        claims(2024, [member("J4", [fill("2024-03-01", "1", "STA", 30)]),
                      member("J5", [fill("2024-11-01", "1", "STA", 30), fill("2024-12-01", "1", "STA", 31)])]),
    ]


def reportable_rate():
    """2.7, 5.1: a reportable class's rate is over its rate base, the members in the measure for it."""
    rng = random.Random(SEED + 51)
    out = []
    # (in the measure, of them adherent, outside the measure): 30.0 and 43.75 over the rate base
    for measured, adherent, outside, year in ((10, 3, 2, 2024), (16, 7, 3, 2016)):
        members = []
        for k in range(measured):
            start = add(iso(year, 1, 1), rng.randint(0, 150))
            if k < adherent:
                members.append(steady(f"R{k:02d}", year, start=start, supply=90, count=5))
            else:
                members.append(steady(f"R{k:02d}", year, start=start, gap=rng.choice([60, 90]), count=2))
        for k in range(outside):
            members.append(member(f"Q{k:02d}", [fill(add(iso(year, 1, 1), rng.randint(0, 300)), "4", "STA", 30)]))
        rng.shuffle(members)
        out.append(claims(year, members))
    return out


def report_order():
    """README: members in file order, a member's classes and the class list in ascending character order."""
    return [
        claims(2024, [
            member("ZZ", [fill("2024-01-02", "1", "B0", 30), fill("2024-02-01", "1", "B0", 30),
                          fill("2024-01-02", "2", "0A", 30), fill("2024-03-01", "2", "0A", 30),
                          fill("2024-01-02", "3", "A", 30), fill("2024-04-01", "3", "A", 30),
                          fill("2024-01-02", "4", "AA", 30), fill("2024-05-01", "4", "AA", 30),
                          fill("2024-01-02", "5", "9", 30), fill("2024-06-01", "5", "9", 30)]),
            member("AA", [fill("2024-02-02", "3", "A", 30), fill("2024-04-02", "3", "A", 30)]),
            member("NOFILLS", []),
            member("0", [fill("2024-03-03", "12345678901", "ZZZZZZZZ", 30), fill("2024-06-03", "12345678901", "ZZZZZZZZ", 30)]),
        ]),
    ]


def limits_members():
    """1.3 at its ends: 100 members; the sixty with no claim lines list no row, the forty others are in the measure
    for one reportable class."""
    rng = random.Random(SEED + 13)
    year = 2000
    members = []
    for k in range(MAX_MEMBERS):
        if k % 5 in (1, 3, 4) and k != MAX_MEMBERS - 1:
            members.append(member(f"L{k}", []))
            continue
        first = add(iso(year, 1, 1), rng.randint(0, 180))
        supply = 90 if k % 3 == 0 else 30
        members.append(member(f"L{k}", [fill(first, "7", "K", supply), fill(add(first, supply), "7", "K", supply),
                                        fill(add(first, 2 * supply), "7", "K", supply)]))
    members[0]["id"], members[2]["id"] = "A" * 12, "Z-9"
    return [claims(year, members)]


def limits_fills():
    """1.3 at its ends: a member with 400 claim lines under 40 class codes of one to eight characters over the
    whole of a leap year, and 60 stay days in 10 stays."""
    rng = random.Random(SEED + 14)
    year = 2096
    codes = sorted({"".join(rng.choice(CODE) for _ in range(1 if n < 36 else 2)) for n in range(80)})[:38] + ["ZZZZZZZ9", "Z9Z9Z9Z9"]
    assert len(set(codes)) == 40 and {len(c) for c in codes} >= {1, 8}
    big = [fill(add(iso(year, 1, 3), k * 363 // 399), str(k % 40), codes[k % 40], rng.choice([1, 2, 3, 30, 100])) for k in range(399)]
    big.append(fill(iso(year, 1, 1), "0", codes[0], 2))  # the 400th line, listed last, is the earliest fill of its class
    return [claims(year, [member("W", big, [(iso(year, m, 3), iso(year, m, 8)) for m in range(2, 12)])])]


# ---- families for the figures the specification leaves to today's code --------------------------------------


def outside_measure():
    """Members outside the measure: the span, period and covered days stay today's."""
    return [
        # one fill date, with a stay inside its coverage and one after it
        claims(2023, [member("O1", [fill("2023-11-01", "1", "STA", 30)], [("2023-11-05", "2023-11-06"), ("2023-12-10", "2023-12-11")])]),
        # first filled after 2 October, coverage running past 31 December, a refill carried over
        claims(2024, [member("O2", [fill("2024-10-03", "1", "STA", 60), fill("2024-11-20", "1", "STA", 60)]),
                      member("O3", [fill("2024-12-31", "9", "RAS", 30), fill("2024-12-31", "9", "RAS", 30)])]),
        # one fill date, two drugs, early in the year, the stay at the end of the coverage
        claims(2011, [member("O4", [fill("2011-02-01", "1", "DIA", 30), fill("2011-02-01", "2", "DIA", 20)],
                             [("2011-02-28", "2011-03-02")]),
                      member("O5", [fill("2011-05-05", "3", "STA", 1)])]),
    ]


def small_class():
    """Classes with fewer than ten members in the measure: the rate stays today's."""
    rng = random.Random(SEED + 27)
    out = []
    # (in the measure, of them adherent, outside the measure): rates 37.5, 100.0, 0.0, 6.25 and 2/7 of today's divisor
    for measured, adherent, outside, year in ((9, 6, 4, 2024), (0, 0, 3, 2044), (5, 1, 11, 2061)):
        members = []
        for k in range(measured):
            start = add(iso(year, 1, 1), rng.randint(0, 150))
            if k < adherent:
                members.append(steady(f"S{k:02d}", year, start=start, supply=90, count=5))
            else:
                members.append(steady(f"S{k:02d}", year, start=start, gap=rng.choice([60, 90]), count=2))
        for k in range(outside):
            members.append(member(f"T{k:02d}", [fill(add(iso(year, 1, 1), rng.randint(0, 300)), "4", "STA", 30)]))
        rng.shuffle(members)
        out.append(claims(year, members))
    return out


def over_limit():
    """Fills above the supply limit: the coverage stays today's (100 days), refills carried over after it."""
    return [
        claims(2024, [member("V1", [fill("2024-01-01", "1", "STA", 150), fill("2024-02-01", "1", "STA", 30)])]),
        claims(2025, [member("V2", [fill("2025-01-10", "1", "STA", 101), fill("2025-09-01", "1", "STA", 365)]),
                      member("V3", [fill("2025-02-01", "2", "RAS", 180), fill("2025-02-01", "3", "RAS", 30),
                                    fill("2025-06-01", "2", "RAS", 100), fill("2025-06-02", "2", "RAS", 102)])]),
    ]


def traps_combined():
    """The three together: members outside the measure with fills above the limit, in a class below ten."""
    return [
        claims(2024, [member("X1", [fill("2024-11-15", "1", "STA", 200), fill("2024-11-20", "1", "STA", 30)]),
                      member("X2", [fill("2024-03-01", "1", "STA", 120), fill("2024-03-01", "2", "STA", 30)],
                             [("2024-04-01", "2024-04-03")]),
                      steady("X3", 2024, start="2024-01-15", count=11)]),
    ]


# ---- seeded files over the rest of the domain --------------------------------------------------------------


def generated():
    """Seeded files: every member in the measure for every class, every fill within the limit."""
    rng = random.Random(SEED)
    out = []
    for n in range(2):
        year = rng.randint(2000, 2099)
        pool = sorted({"".join(rng.choice(CODE) for _ in range(rng.randint(1, 8))) for _ in range(rng.randint(1, 5))})
        members, ids = [], set()
        for _ in range(rng.randint(2, 7)):
            mid = "".join(rng.choice(CODE + "-") for _ in range(rng.randint(1, 12)))
            if mid in ids:
                continue
            ids.add(mid)
            fills = []
            for klass in rng.sample(pool, rng.randint(1, len(pool))):
                drugs = ["".join(rng.choice(DIGITS) for _ in range(rng.randint(1, 11))) for _ in range(rng.randint(1, 2))]
                day = add(iso(year, 1, 1), rng.randint(0, 250))
                count = 0
                while date.fromisoformat(day).year == year and count < 6:
                    supply = rng.choice([7, 14, 28, 30, 30, 60, 90, 100, rng.randint(1, 100)])
                    fills.append(fill(day, rng.choice(drugs), klass, supply))
                    step = max(1, int(supply * rng.uniform(0.5, 1.5)))
                    day = add(day, step)
                    count += 1
                if len({f["date"] for f in fills if f["class"] == klass}) < 2:
                    fills.append(fill(add(iso(year, 1, 1), 280), drugs[0], klass, 30))
            rng.shuffle(fills)
            stays, used = [], set()
            for _ in range(rng.randint(0, 3)):
                a = add(iso(year, 1, 1), rng.randint(0, 360))
                length = rng.randint(1, 10)
                days = {add(a, k) for k in range(length) if date.fromisoformat(add(a, k)).year == year}
                if days & used or len(used) + len(days) > 60:
                    continue
                used |= days
                stays.append((a, max(days)))
            members.append(member(mid, fills, stays))
        out.append(claims(year, members))
    return out


def differential_pairs():
    """Pairs a/b that differ only in a field the kept step does not use: the shipped package gives the same
    figures for both, and so must the candidate."""
    pairs = {"outside_measure": [], "over_limit": []}
    # outside the measure: b adds a stay after the coverage ends, or moves the member to another year
    base = [fill("2023-11-01", "1", "STA", 30)]
    pairs["outside_measure"].append((claims(2023, [member("P1", base)]),
                                     claims(2023, [member("P1", base, [("2023-12-10", "2023-12-12")])])))
    late = [fill("2021-10-20", "1", "RAS", 20), fill("2021-11-02", "1", "RAS", 20)]
    pairs["outside_measure"].append((claims(2021, [member("P2", late)]),
                                     claims(2021, [member("P2", late, [("2021-12-20", "2021-12-31")])])))
    one_day = [fill("2012-04-01", "1", "DIA", 40), fill("2012-04-01", "2", "DIA", 10)]
    pairs["outside_measure"].append((claims(2012, [member("P3", one_day)]),
                                     claims(2012, [member("P3", one_day, [("2012-09-01", "2012-09-30")])])))
    # above the supply limit: b gives the fill another days supply above the limit
    for mid, year, first, a_days, b_days in (("U1", 2024, "2024-01-01", 101, 365), ("U2", 2019, "2019-03-10", 150, 200),
                                             ("U3", 2032, "2032-06-01", 120, 180)):
        def make(days):
            return claims(year, [member(mid, [fill(first, "1", "STA", days), fill(add(first, 40), "1", "STA", 30),
                                              fill(add(first, 170), "1", "STA", 30)])])
        pairs["over_limit"].append((make(a_days), make(b_days)))
    return pairs


FAMILIES = {
    "start_day": start_day,
    "carry_over": carry_over,
    "other_drugs": other_drugs,
    "index_order": index_order,
    "adjustment_lines": adjustment_lines,
    "measure_dates": measure_dates,
    "index_cutoff": index_cutoff,
    "year_end_period": year_end_period,
    "stays": stays,
    "rounding": rounding,
    "adherence": adherence,
    "reportable_rate": reportable_rate,
    "report_order": report_order,
    "outside_measure": outside_measure,
    "small_class": small_class,
    "over_limit": over_limit,
    "traps_combined": traps_combined,
    "generated": generated,
    "limits_members": limits_members,
    "limits_fills": limits_fills,
}

# Figures the specification leaves to today's code that each family grades; no other family grades them.
# A fill above the supply limit appears only in the families that grade it, and a claim line with no days
# supply only in its own family.
GRADES_SILENT = {
    "outside_measure": {"outside"},
    "small_class": {"small_class"},
    "over_limit": {"over_limit"},
    "traps_combined": {"outside", "small_class", "over_limit"},
    "adjustment_lines": {"no_supply"},
}


def families():
    return {name: make() for name, make in FAMILIES.items()}

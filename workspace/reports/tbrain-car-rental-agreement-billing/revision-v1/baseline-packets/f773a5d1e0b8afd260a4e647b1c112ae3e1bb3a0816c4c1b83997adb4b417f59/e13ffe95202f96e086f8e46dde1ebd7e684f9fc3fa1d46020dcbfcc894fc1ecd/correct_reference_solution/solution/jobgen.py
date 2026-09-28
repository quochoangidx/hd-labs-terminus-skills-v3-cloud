"""Agreement files for the verifier, one family per test (python3 solution/seal.py writes them out).

Named files sit on the edges each rule reaches; seeded files (a constant seed, never candidate bytes) cover
the rest of the rule 1.3 domain. Three inputs carry a figure the manual leaves to today's code, and each
appears only in its own family: a rental shorter than a day (its days, graded where the allowance cannot
matter), a rental shorter than a day that drives past 100 miles (its allowance, graded where the days
cannot differ), and a car back with as much fuel as it left with or more (its fuel charge).
"""

import random
from datetime import datetime, timedelta

SEED = 20260928
CODE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
MAX_AGREEMENTS = 200
FMT = "%Y-%m-%dT%H:%M"


def at(text, minutes=0):
    return (datetime.strptime(text, FMT) + timedelta(minutes=minutes)).strftime(FMT)


def ag(aid, out, length, odo=10000, driven=0, fuel=(8, 8), day=5000, mile=30, fuel_rate=600):
    return {"id": aid, "out": out, "in": at(out, length), "odometer_out": odo, "odometer_in": (odo + driven) % 1_000_000,
            "fuel_out": fuel[0], "fuel_in": fuel[1], "day_rate": day, "mile_rate": mile, "fuel_rate": fuel_rate}


def run(agreements):
    return {"branch": "", "agreements": agreements}


D = 1440


def grace():
    """2.3: whole days, and one more only past 59 minutes over."""
    return [
        run([ag("G1", "2031-05-02T09:15", 3 * D), ag("G2", "2031-05-02T09:15", 3 * D + 1), ag("G3", "2031-05-02T09:15", 3 * D + 59),
             ag("G4", "2031-05-02T09:15", 3 * D + 60), ag("G5", "2031-05-02T09:15", 3 * D + 61), ag("G6", "2031-05-02T09:15", 3 * D + 1439)]),
        run([ag("G7", "2044-12-31T23:30", D + 20, day=100), ag("G8", "2012-02-28T10:00", 2 * D + 59, day=100000),
             ag("G9", "2019-01-31T00:00", D)]),
    ]


def allowance():
    """3.2: 150 miles for each allowance day, the mile rate beyond."""
    return [
        run([ag("M1", "2027-03-01T08:00", 2 * D, driven=300), ag("M2", "2027-03-01T08:00", 2 * D, driven=301),
             ag("M3", "2027-03-01T08:00", 2 * D, driven=250), ag("M4", "2027-03-01T08:00", 7 * D + 59, driven=1051, mile=500),
             ag("M5", "2027-03-01T08:00", 7 * D + 60, driven=1201, mile=1)]),
        run([ag("M6", "2050-06-10T12:00", 60 * D, driven=9000), ag("M7", "2050-06-10T12:00", 60 * D, driven=9001, mile=0),
             ag("M8", "2050-06-10T12:00", D + 30, driven=200, mile=45)]),
    ]


def turnover():
    """2.5: the odometer turns over from 999,999 to 0."""
    return [
        run([ag("T1", "2033-08-08T08:08", 2 * D, odo=999_999, driven=1), ag("T2", "2033-08-08T08:08", 2 * D, odo=999_950, driven=400),
             ag("T3", "2033-08-08T08:08", 5 * D, odo=990_000, driven=20_000), ag("T4", "2033-08-08T08:08", 5 * D, odo=0, driven=20_000),
             ag("T5", "2033-08-08T08:08", 3 * D, odo=999_999, driven=0)]),
    ]


def refuelling():
    """2.6, 3.3: each eighth short at the fuel rate, plus the refuelling fee."""
    return [
        run([ag("F1", "2024-02-28T18:00", 2 * D, fuel=(8, 7)), ag("F2", "2024-02-28T18:00", 2 * D, fuel=(8, 0), fuel_rate=2000),
             ag("F3", "2024-02-28T18:00", 2 * D, fuel=(1, 0), fuel_rate=0), ag("F4", "2024-02-28T18:00", 2 * D, fuel=(5, 2), fuel_rate=333)]),
    ]


def tax_base():
    """4.1: tax on the time and mileage charges; fuel is not taxed."""
    return [
        run([ag("X1", "2040-10-10T10:10", 4 * D, driven=900, fuel=(8, 3), fuel_rate=1999),
             ag("X2", "2040-10-10T10:10", 4 * D, driven=0, fuel=(6, 6), day=4000)]),
        run([ag("X3", "2041-01-01T00:00", 3 * D + 45, driven=700, fuel=(7, 2), mile=18, fuel_rate=1250)]),
    ]


def tax_rounding():
    """1.2: the tax to the nearest cent, an exact half cent going up."""
    # 8.25% of 200 is 16.5 cents; of 600, 49.5; of 1,400, 115.5; of 13,400, 1105.5; of 1,212, 99.99
    return [
        run([ag("R1", "2022-07-01T00:00", D, day=200), ag("R2", "2022-07-01T00:00", 3 * D, day=200),
             ag("R3", "2022-07-01T00:00", 7 * D, day=200), ag("R4", "2022-07-01T00:00", D, day=13400),
             ag("R5", "2022-07-01T00:00", D, day=1212), ag("R6", "2022-07-01T00:00", 2 * D, day=100, driven=301, mile=1)]),
    ]


def order_and_totals():
    """README: bills in file order; 4.3 revenue and tax summed."""
    return [
        run([ag("Z9", "2030-01-01T00:00", 2 * D, driven=500, fuel=(4, 1)), ag("A-1", "2030-01-01T00:00", 3 * D + 90),
             ag("0", "2030-01-01T00:00", 10 * D, driven=2000, mile=12), ag("MMMMMMMMMM", "2030-01-01T00:00", D + 59)]),
    ]


def short_days():
    """A rental under a day: the manual gives it no charged days; today's step (every day begun) stands."""
    return [
        run([ag("S1", "2028-04-04T14:00", 1, driven=5), ag("S2", "2028-04-04T14:00", 30, driven=12), ag("S3", "2028-04-04T14:00", 59, driven=40),
             ag("S4", "2028-04-04T14:00", 60, driven=100), ag("S5", "2028-04-04T14:00", 1439, driven=90)]),
    ]


def short_allowance():
    """3.2 on a rental under a day: 150 miles for each day it is charged for (today's days)."""
    return [
        run([ag("L1", "2036-09-09T07:00", 300, driven=101, mile=40), ag("L2", "2036-09-09T07:00", 1200, driven=150, mile=40),
             ag("L3", "2036-09-09T07:00", 90, driven=151, mile=500), ag("L4", "2036-09-09T07:00", 1439, driven=400, mile=7)]),
    ]


def fuel_not_short():
    """A car back as full or fuller: the manual gives no fuel charge; today's step stands."""
    return [
        run([ag("E1", "2045-11-11T11:00", 2 * D, fuel=(3, 3)), ag("E2", "2045-11-11T11:00", 2 * D, fuel=(3, 4), fuel_rate=650),
             ag("E3", "2045-11-11T11:00", 2 * D, fuel=(0, 8), fuel_rate=2000), ag("E4", "2045-11-11T11:00", 2 * D, fuel=(2, 7), fuel_rate=0)]),
    ]


def traps_combined():
    """All three together: short rentals past 100 miles and under an hour, cars back fuller."""
    return [
        run([ag("C1", "2061-03-03T03:03", 45, driven=130, fuel=(2, 5), mile=20), ag("C2", "2061-03-03T03:03", 2 * D, driven=280, fuel=(4, 6)),
             ag("C3", "2061-03-03T03:03", 700, driven=120, fuel=(6, 6))]),
    ]


def limits():
    """1.3 at its ends: 200 agreements, 60-day and one-minute lengths, the year 2000 and 2099, rate ends."""
    rng = random.Random(SEED + 1)
    out = []
    for k in range(MAX_AGREEMENTS):
        start = datetime(2000, 1, 1) + timedelta(minutes=rng.randint(0, 99 * 365 * D))
        length = rng.choice([D, 2 * D + 60, 5 * D + 59, rng.randint(1, 60) * D + rng.randint(60, 1439)])
        if (start + timedelta(minutes=length)).year > 2099:
            start -= timedelta(days=61)
        fo = rng.randint(1, 8)
        out.append(ag(f"L{k}", start.strftime(FMT), length, odo=rng.randint(0, 999_999), driven=rng.randint(0, 3000),
                      fuel=(fo, rng.randint(0, fo - 1)), day=rng.choice([100, 100000, rng.randint(100, 100000)]),
                      mile=rng.choice([0, 500, rng.randint(0, 500)]), fuel_rate=rng.choice([0, 2000, rng.randint(0, 2000)])))
    out[0] = ag("A" * 10, "2000-01-01T00:00", 60 * D, odo=0, driven=20_000, fuel=(8, 0), day=100000, mile=500, fuel_rate=2000)
    out[1] = ag("Z-9", "2099-12-30T22:58", D, odo=999_999, driven=0, fuel=(8, 7), day=100, mile=0, fuel_rate=0)
    out[2] = ag("B", "2099-10-31T23:59", 60 * D, driven=1, fuel=(8, 7))
    return [run(out)]


def generated():
    """Seeded files: day rentals only, every car back with less fuel than it left with or the same."""
    rng = random.Random(SEED)
    files = []
    for _ in range(4):
        items = []
        for k in range(rng.randint(3, 12)):
            start = datetime(2000, 1, 1) + timedelta(minutes=rng.randint(0, 99 * 365 * D))
            length = rng.randint(D, 30 * D)
            if (start + timedelta(minutes=length)).year > 2099:
                start -= timedelta(days=31)
            fo = rng.randint(0, 8)
            aid = "".join(rng.choice(CODE + "-") for _ in range(rng.randint(1, 10)))
            items.append(ag(f"{aid[:9]}{k}"[-10:], start.strftime(FMT), length, odo=rng.randint(0, 999_999), driven=rng.randint(0, 6000),
                            fuel=(fo, rng.randint(0, fo)), day=rng.randint(100, 100000), mile=rng.randint(0, 500), fuel_rate=rng.randint(0, 2000)))
        files.append(run(items))
    return files


FAMILIES = {
    "grace": grace,
    "allowance": allowance,
    "turnover": turnover,
    "refuelling": refuelling,
    "tax_base": tax_base,
    "tax_rounding": tax_rounding,
    "order_and_totals": order_and_totals,
    "short_days": short_days,
    "short_allowance": short_allowance,
    "fuel_not_short": fuel_not_short,
    "traps_combined": traps_combined,
    "generated": generated,
    "limits": limits,
}

# Inputs carrying a figure the manual leaves to today's code, allowed per family.
SILENT = {
    "short_days": {"short"},
    "short_allowance": {"short"},  # graded only where the days cannot differ (an hour or more)
    "fuel_not_short": {"fuller"},
    "traps_combined": {"short", "fuller"},
}


def families():
    return {name: make() for name, make in FAMILIES.items()}

"""Authoring-only random agreement files within RC-3 1.3."""
import random
from datetime import datetime, timedelta

CODE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"


def agreement(rng, k):
    out = datetime(2000, 1, 1) + timedelta(minutes=rng.randint(0, 99 * 365 * 1440))
    kind = rng.random()
    if kind < 0.3:
        n = rng.randint(1, 1439)
    elif kind < 0.6:
        n = rng.randint(1, 30) * 1440 + rng.choice([0, 1, 30, 59, 60, 61, 300, 1439])
    else:
        n = rng.randint(1, 86400)
    back = out + timedelta(minutes=n)
    if back.year > 2099:
        out -= timedelta(days=61); back -= timedelta(days=61)
    o = rng.randint(0, 999999)
    driven = rng.choice([0, rng.randint(0, 400), rng.randint(0, 20000), 100, 150, 101, 151])
    fo = rng.randint(0, 8)
    return {"id": f"A{k}", "out": out.strftime("%Y-%m-%dT%H:%M"), "in": back.strftime("%Y-%m-%dT%H:%M"),
            "odometer_out": o, "odometer_in": (o + driven) % 1000000, "fuel_out": fo, "fuel_in": rng.randint(0, 8),
            "day_rate": rng.choice([100, 100000, rng.randint(100, 100000)]), "mile_rate": rng.choice([0, 500, rng.randint(0, 500)]),
            "fuel_rate": rng.choice([0, 2000, rng.randint(0, 2000)])}


def agreement_file(rng):
    return {"branch": "B", "agreements": [agreement(rng, k) for k in range(rng.randint(1, 30))]}

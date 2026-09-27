"""Authoring-only random claims files within AM-2 1.3 (fuzz and skeleton scoring)."""

import random
from datetime import date, timedelta

DIG = "0123456789"
CODE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def iso(d):
    return d.isoformat()


def rand_code(rng, lo, hi, alphabet=CODE):
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(lo, hi)))


def stays_for(rng, year, max_days=60, max_stays=10):
    """Non-overlapping stays within the year, total at most max_days."""
    start, end = date(year, 1, 1), date(year, 12, 31)
    n = rng.randint(0, max_stays)
    out, used, total = [], set(), 0
    for _ in range(n):
        length = rng.randint(1, 12)
        if total + length > max_days:
            break
        a = start + timedelta(days=rng.randint(0, (end - start).days))
        b = min(a + timedelta(days=length - 1), end)
        span = {(a + timedelta(days=k)).toordinal() for k in range((b - a).days + 1)}
        if span & used or any(abs(x - y) == 0 for x in span for y in used):
            continue
        used |= span
        total += len(span)
        out.append([iso(a), iso(b)])
    return out


def fills_for(rng, year, classes, n, drugs_per_class=3, supply=(1, 365), early_bias=0.5):
    start = date(year, 1, 1)
    last = (date(year, 12, 31) - start).days
    drugs = {c: [rand_code(rng, 1, 11, DIG) for _ in range(rng.randint(1, drugs_per_class))] for c in classes}
    out = []
    for _ in range(n):
        c = rng.choice(classes)
        d = start + timedelta(days=rng.randint(0, last))
        days = rng.choice([30, 30, 60, 90, 7, 14, 28, 100, 101, 102, rng.randint(*supply)])
        days = max(supply[0], min(supply[1], days))
        if rng.random() < 0.12:
            days = 0
        out.append({"date": iso(d), "drug": rng.choice(drugs[c]), "class": c, "days": days})
    rng.shuffle(out)
    return out


def regular_member(rng, year, mid, classes, gap_bias=True):
    """A member refilling one or two drugs per class with realistic cadence (early and late refills)."""
    fills = []
    for c in classes:
        drugs = [rand_code(rng, 1, 11, DIG) for _ in range(rng.randint(1, 2))]
        d = date(year, 1, 1) + timedelta(days=rng.randint(0, 330))
        while d.year == year:
            supply = rng.choice([30, 30, 90, 60, 28, 100, 101, 180, rng.randint(1, 365)])
            fills.append({"date": iso(d), "drug": rng.choice(drugs), "class": c, "days": supply})
            if rng.random() < 0.1:
                z = date(year, 1, 1) + timedelta(days=rng.randint(0, 364))
                fills.append({"date": iso(z), "drug": rng.choice(drugs), "class": c, "days": 0})
            step = int(supply * rng.uniform(0.6, 1.4)) if rng.random() < 0.9 else rng.randint(0, 3)
            d = d + timedelta(days=max(0, step))
            if rng.random() < 0.08:
                break
    rng.shuffle(fills) if rng.random() < 0.3 else None
    return {"id": mid, "fills": fills[:400], "stays": stays_for(rng, year)}


def claims_file(rng, n_members=None, n_classes=None, year=None):
    year = year or rng.randint(2000, 2099)
    n_classes = n_classes or rng.randint(1, 6)
    pool = sorted({rand_code(rng, 1, 8) for _ in range(n_classes)})
    members, ids = [], set()
    for _ in range(n_members or rng.randint(1, 30)):
        mid = rand_code(rng, 1, 12, CODE + "-")
        while mid in ids:
            mid = rand_code(rng, 1, 12, CODE + "-")
        ids.add(mid)
        k = rng.sample(pool, rng.randint(1, min(3, len(pool))))
        if rng.random() < 0.6:
            members.append(regular_member(rng, year, mid, k))
        else:
            members.append({"id": mid, "fills": fills_for(rng, year, k, rng.randint(0, 12)), "stays": stays_for(rng, year)})
    return {"plan": "FUZZ-" + rand_code(rng, 4, 8), "year": year, "members": members}

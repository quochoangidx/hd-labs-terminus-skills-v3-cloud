"""Seeded job generators for tbrain-3pl-warehouse-client-billing (authoring only).

Every job keeps within billing schedule 1.4. `broad_job(trap_free=True)` rejects any job carrying a T1 or
T2 input (model predicates).
"""

import importlib.util
from datetime import date, timedelta
from pathlib import Path

TASK = Path(__file__).resolve().parents[3] / "tasks" / "tbrain-3pl-warehouse-client-billing"
_spec = importlib.util.spec_from_file_location("wbmodel", TASK / "solution" / "model.py")
model = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(model)

MIN_END = date(2001, 3, 1)
MAX_END = date(2099, 12, 31)


def iso(d):
    return d.isoformat()


def rand_end(rng):
    special = [date(2004, 3, 1), date(2024, 2, 29), date(2001, 3, 1), date(2099, 12, 31), date(2030, 1, 1),
               date(2051, 1, 3)]
    if rng.random() < 0.25:
        return rng.choice(special)
    return MIN_END + timedelta(days=rng.randint(0, (MAX_END - MIN_END).days))


def rand_tiers(rng, hi=100_000):
    n = rng.randint(1, 5)
    return [[None if k == n - 1 else rng.choice([1, 2, 3, 4, 8, 13, 52, rng.randint(1, 52)]),
             rng.randint(0, hi) if rng.random() < 0.9 else rng.choice([0, hi])] for k in range(n)]


def rand_rates(rng):
    return {"storage": rand_tiers(rng),
            "handling": {k: rng.randint(0, 100_000) if rng.random() < 0.9 else rng.choice([0, 100_000])
                         for k in ("fee", "in", "out", "after_hours")}}


def rand_client(rng, end, first_by, pct=None, minimum=None, n=None):
    """Revisions with strictly increasing effective dates, the first on or before `first_by`."""
    n = n or rng.randint(1, 6)
    lo = end - timedelta(days=400)
    first = lo + timedelta(days=rng.randint(0, max(0, (first_by - lo).days)))
    span = (end - first).days
    n = min(n, span + 1)
    offsets = sorted(rng.sample(range(1, span + 1), n - 1)) if n > 1 else []
    effs = [first] + [first + timedelta(days=o) for o in offsets]
    return {"minimum": minimum if minimum is not None else rng.choice([0, 100, 5000, 250000, 1000000, rng.randint(0, 1000000)]),
            "surcharge_percent": pct if pct is not None else rng.choice([0, 3, 5, 7, 12, 25, 50, rng.randint(0, 50)]),
            "revisions": [{"effective": iso(e), "rates": rand_rates(rng)} for e in effs]}


def rand_lot(rng, end, client, lid, shape=None):
    lo = end - timedelta(days=400)
    received = lo + timedelta(days=rng.choice([rng.randint(0, 400), rng.randint(300, 400), rng.randint(380, 400)]))
    pallets = rng.choice([0, 1, 2, 10, 26, 1000, rng.randint(1, 1000)])
    shape = shape or rng.choice(["closed", "open", "untouched", "returns"])
    entries = []
    if shape != "untouched":
        k = rng.randint(1, min(50, pallets + 3))
        span = (end - received).days
        days = sorted(received + timedelta(days=d) for d in rng.sample(range(span + 1), min(k, span + 1)))
        out_before = {}  # running total of entries dated strictly before a date
        total = 0
        last = None
        for day in days:
            if day != last:
                before = total
                last = day
            r = rng.random()
            if shape == "returns" and r < 0.3 and before > 0:
                n = -rng.randint(1, min(before, 1000))
                if total + n < 0:
                    n = -total
                if n == 0:
                    continue
            elif r < 0.05:
                n = 0
            else:
                left = pallets - total
                if left <= 0:
                    continue
                n = rng.randint(1, min(left, 1000)) if shape != "closed" else rng.randint(1, min(left, 1000))
            entries.append({"date": iso(day), "pallets": n})
            total += n
    return {"id": lid, "client": client, "received": iso(received), "pallets": pallets, "dispatches": entries}


def rand_id(rng):
    return rng.choice(["L", "LOT-", "GRN", "R"]) + str(rng.randint(0, 999999)).zfill(rng.choice([1, 6]))


def broad_job(rng, n_lots=None, n_clients=None, trap_free=True):
    for _attempt in range(1000):
        end = rand_end(rng)
        start = end - timedelta(days=rng.choice([0, 6, 7, 27, 30, 61, rng.randint(0, 61)]))
        pool = [end - timedelta(days=k) for k in range(401)]
        holidays = sorted(iso(d) for d in rng.sample(pool, rng.randint(0, 60)))
        cids = []
        for k in range(n_clients or rng.randint(1, 5)):
            cids.append(rng.choice(["ACME", "c", "Client-", "K"]) + str(rng.randint(0, 999)) + chr(65 + k))
        ids, lots = set(), []
        for _ in range(n_lots or rng.randint(1, 25)):
            lid = rand_id(rng)
            while lid in ids:
                lid = rand_id(rng)
            ids.add(lid)
            for _try in range(200):
                cand = rand_lot(rng, end, rng.choice(cids), lid)
                probe = {"period": {"start": iso(start), "end": iso(end)}, "lots": [cand]}
                if not trap_free or not (model.carries_entry_below_nought(probe) or model.carries_empty_arrival(probe)):
                    break
            lots.append(cand)
        clients = {}
        for cid in cids:
            receipts = [date.fromisoformat(x["received"]) for x in lots if x["client"] == cid]
            clients[cid] = rand_client(rng, end, min(receipts + [start]),
                                       pct=None,
                                       minimum=None)
        job = {"statement": f"ST-{rng.randint(0, 99999):05d}", "period": {"start": iso(start), "end": iso(end)},
               "holidays": holidays, "clients": clients, "lots": lots}
        if trap_free and (model.carries_entry_below_nought(job) or model.carries_empty_arrival(job)):
            continue
        return job
    raise RuntimeError("could not draw a job")


def within_limits(job):
    """Executable form of billing schedule 1.4 (the instruction's limits)."""
    end = date.fromisoformat(job["period"]["end"])
    start = date.fromisoformat(job["period"]["start"])
    assert MIN_END <= end <= MAX_END and 0 <= (end - start).days <= 61
    lo = end - timedelta(days=400)

    def ok(text):
        d = date.fromisoformat(text)
        assert lo <= d <= end, text
        return d
    assert 1 <= len(job["lots"]) <= 300 and len({x["id"] for x in job["lots"]}) == len(job["lots"])
    assert 1 <= len(job["clients"]) <= 20
    assert len(job["holidays"]) <= 60 and len(set(job["holidays"])) == len(job["holidays"])
    for h in job["holidays"]:
        ok(h)
    for cid, c in job["clients"].items():
        assert type(c["surcharge_percent"]) is int and 0 <= c["surcharge_percent"] <= 50
        assert type(c["minimum"]) is int and 0 <= c["minimum"] <= 1_000_000
        first = date.fromisoformat(c["revisions"][0]["effective"])
        assert first <= start and all(first <= date.fromisoformat(x["received"]) for x in job["lots"] if x["client"] == cid)
        assert 1 <= len(c["revisions"]) <= 6
        effs = [ok(r["effective"]) for r in c["revisions"]]
        assert all(a < b for a, b in zip(effs, effs[1:]))
        for r in c["revisions"]:
            tiers = r["rates"]["storage"]
            assert 1 <= len(tiers) <= 5
            for i, (length, rate) in enumerate(tiers):
                assert (length is None) if i == len(tiers) - 1 else (type(length) is int and 1 <= length <= 52)
                assert type(rate) is int and 0 <= rate <= 100_000
            assert set(r["rates"]["handling"]) == {"fee", "in", "out", "after_hours"}
            assert all(type(v) is int and 0 <= v <= 100_000 for v in r["rates"]["handling"].values())
    for lot in job["lots"]:
        assert lot["client"] in job["clients"]
        rec = ok(lot["received"])
        assert type(lot["pallets"]) is int and 0 <= lot["pallets"] <= 1000 and len(lot["dispatches"]) <= 50
        assert len({x["date"] for x in lot["dispatches"]}) == len(lot["dispatches"])
        for x in lot["dispatches"]:
            assert ok(x["date"]) >= rec and type(x["pallets"]) is int and -1000 <= x["pallets"] <= 1000
        for d in {x["date"] for x in lot["dispatches"]}:
            before = sum(x["pallets"] for x in lot["dispatches"] if x["date"] < d)
            through = sum(x["pallets"] for x in lot["dispatches"] if x["date"] <= d)
            assert 0 <= before <= lot["pallets"] and 0 <= through <= lot["pallets"], (lot["id"], d)
    return True

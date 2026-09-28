"""Seeded job generators for tbrain-container-demurrage-detention (authoring only).

Every job keeps within tariff rules 1.4. `broad_job` draws over the whole range with a trap switch:
trap_free=True rejects any job carrying a T1 or T2 input (model predicates).
"""

import importlib.util
import random
from datetime import date, timedelta
from pathlib import Path

TASK = Path(__file__).resolve().parents[3] / "tasks" / "tbrain-container-demurrage-detention"
_spec = importlib.util.spec_from_file_location("ddmodel", TASK / "solution" / "model.py")
model = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(model)

MIN_CUT = date(2001, 3, 1)
MAX_CUT = date(2099, 12, 31)


def iso(d):
    return d.isoformat()


def rand_cut(rng):
    special = [date(2004, 3, 1), date(2024, 2, 29), date(2001, 3, 1), date(2099, 12, 31), date(2030, 1, 1),
               date(2051, 1, 3)]
    if rng.random() < 0.25:
        return rng.choice(special)
    return MIN_CUT + timedelta(days=rng.randint(0, (MAX_CUT - MIN_CUT).days))


def rand_scale(rng, rate_hi=100_000):
    n = rng.randint(1, 5)
    tiers = []
    for k in range(n):
        length = None if k == n - 1 else rng.choice([1, 2, 3, 5, 7, 10, 30, 60, rng.randint(1, 60)])
        tiers.append([length, rng.randint(0, rate_hi) if rng.random() < 0.9 else rng.choice([0, rate_hi])])
    return tiers


def rand_revision(rng, effective):
    return {"effective": iso(effective),
            "scales": {st: {sz: rand_scale(rng) for sz in ("20", "40")} for st in ("terminal", "merchant")}}


def rand_contract(rng, cut, earliest_effective=None):
    """Revisions with strictly increasing effective dates in [cut-400, cut]."""
    n = rng.randint(1, 6)
    lo = cut - timedelta(days=400)
    first = earliest_effective if earliest_effective is not None else lo + timedelta(days=rng.randint(0, 200))
    first = max(lo, min(first, cut - timedelta(days=n - 1)))
    span = (cut - first).days
    offsets = sorted(rng.sample(range(1, span + 1), n - 1)) if n > 1 and span >= n - 1 else []
    effs = [first] + [first + timedelta(days=o) for o in offsets]
    return {
        "terminal_free_days": rng.choice([0, 1, 3, 4, 5, 7, 10, 20, rng.randint(0, 20)]),
        "merchant_free_days": rng.choice([0, 1, 4, 7, 10, 14, 30, rng.randint(0, 30)]),
        "discount_percent": rng.choice([0, 5, 10, 12, 15, 25, 33, 50, rng.randint(0, 50)]),
        "revisions": [rand_revision(rng, e) for e in effs],
    }


def rand_history(rng, cut, lo, shape):
    """shape: 'returned', 'out' (gated out, running merchant), 'terminal' (still at the terminal)."""
    lo = max(lo, cut - timedelta(days=400))
    discharge = lo + timedelta(days=rng.randint(0, (cut - lo).days))
    moves = [{"move": "DISCHARGE", "date": iso(discharge)}]
    if shape == "terminal":
        return moves
    go = discharge + timedelta(days=rng.choice([0, rng.randint(0, 40), rng.randint(0, 120)]))
    go = min(go, cut)
    moves.append({"move": "GATE_OUT", "date": iso(go)})
    if shape == "out":
        return moves
    back = go + timedelta(days=rng.choice([0, rng.randint(0, 40), rng.randint(0, 150)]))
    back = min(back, cut)
    moves.append({"move": "EMPTY_RETURN", "date": iso(back)})
    return moves


def rand_calendar(rng, cut, n_hi=60):
    lo = cut - timedelta(days=400)
    pool = [lo + timedelta(days=k) for k in range(401)]
    hol = sorted(rng.sample(pool, rng.randint(0, n_hi)))
    clo = sorted(rng.sample(pool, rng.randint(0, n_hi)))
    return [iso(d) for d in hol], [iso(d) for d in clo]


def rand_id(rng, k):
    owner = "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(3)) + rng.choice("UJZ")
    return f"{owner}{rng.randint(0, 999999):06d}{rng.randint(0, 9)}"


def broad_job(rng, n_containers=None, n_contracts=None, trap_free=True, shapes=("returned", "out", "terminal")):
    for _attempt in range(200):
        cut = rand_cut(rng)
        hol, clo = rand_calendar(rng, cut)
        nc = n_contracts or rng.randint(1, 6)
        contracts = {}
        for k in range(nc):
            cid = rng.choice(["C", "K", "SC-", "Q"]) + str(rng.randint(0, 9999)) + chr(65 + k)
            earliest = cut - timedelta(days=400) if trap_free else None
            contracts[cid] = rand_contract(rng, cut, earliest)
        ids = set()
        containers = []
        for k in range(n_containers or rng.randint(1, 25)):
            cid = rand_id(rng, k)
            while cid in ids:
                cid = rand_id(rng, k)
            ids.add(cid)
            contract = rng.choice(sorted(contracts))
            containers.append({"id": cid, "size": rng.choice(["20", "40"]), "contract": contract,
                               "history": rand_history(rng, cut, cut - timedelta(days=400), rng.choice(shapes))})
        job = {"invoice": f"INV-{rng.randint(0, 99999):05d}", "cut_off": iso(cut), "holidays": hol,
               "closures": clo, "contracts": contracts, "containers": containers}
        if trap_free and (model.carries_running_discount_edge(job) or model.carries_pre_sheet_start(job)):
            continue
        return job
    raise RuntimeError("could not draw a trap-free job")


def within_limits(job):
    """Executable form of tariff rules 1.4 (the instruction's limits)."""
    from datetime import date as _date
    cut = _date.fromisoformat(job["cut_off"])
    assert _date(2001, 3, 1) <= cut <= _date(2099, 12, 31)
    lo = cut - timedelta(days=400)

    def ok(text):
        d = _date.fromisoformat(text)
        assert lo <= d <= cut, text
        return d
    assert 1 <= len(job["containers"]) <= 300
    assert 1 <= len(job["contracts"]) <= 20
    assert len({c["id"] for c in job["containers"]}) == len(job["containers"])
    for key in ("holidays", "closures"):
        assert 0 <= len(job[key]) <= 60 and len(set(job[key])) == len(job[key])
        for x in job[key]:
            ok(x)
    for c in job["contracts"].values():
        assert 0 <= c["terminal_free_days"] <= 20 and 0 <= c["merchant_free_days"] <= 30
        assert 0 <= c["discount_percent"] <= 50
        assert 1 <= len(c["revisions"]) <= 6
        effs = [ok(r["effective"]) for r in c["revisions"]]
        assert all(a < b for a, b in zip(effs, effs[1:]))
        for r in c["revisions"]:
            for st in ("terminal", "merchant"):
                for sz in ("20", "40"):
                    tiers = r["scales"][st][sz]
                    assert 1 <= len(tiers) <= 5
                    for i, (length, rate) in enumerate(tiers):
                        if i == len(tiers) - 1:
                            assert length is None
                        else:
                            assert type(length) is int and 1 <= length <= 60
                        assert type(rate) is int and 0 <= rate <= 100_000
    for c in job["containers"]:
        assert c["size"] in ("20", "40") and c["contract"] in job["contracts"]
        moves = {}
        for m in c["history"]:
            assert m["move"] not in moves
            moves[m["move"]] = ok(m["date"])
        assert "DISCHARGE" in moves
        if "GATE_OUT" in moves:
            assert moves["GATE_OUT"] >= moves["DISCHARGE"]
        if "EMPTY_RETURN" in moves:
            assert "GATE_OUT" in moves and moves["EMPTY_RETURN"] >= moves["GATE_OUT"]
    return True

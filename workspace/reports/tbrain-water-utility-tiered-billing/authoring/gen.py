"""Job generator for tbrain-water-utility-tiered-billing (authoring only, never shipped).

FAMILIES maps a family name to fn(rng) -> job. `broad` and D1-D7 are trap-free by construction
(checked by trap_inputs); T1 and T2 each carry only their own trap input.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

TASK = Path(__file__).resolve().parents[3] / "tasks" / "tbrain-water-utility-tiered-billing"
sys.path.insert(0, str(TASK / "solution"))
import model  # noqa: E402

_ids = iter(range(10**6))


def acct_id(rng):
    return f"{rng.choice(['HC', 'W', 'R', 'ACC', 'M'])}{rng.randint(10, 99)}{next(_ids):05d}{rng.choice(['', 'x', ' b', '-7'])}"[:24]


def iso(d):
    return d.isoformat()


def row(rng, start, blocks=None, service=None):
    k = blocks if blocks is not None else rng.randint(1, 6)
    return {
        "from": iso(start),
        "widths": [rng.choice([100, rng.randint(100, 3000), rng.randint(100, 20000), 20000]) for _ in range(k - 1)],
        "prices": sorted(rng.randint(1, 2000) for _ in range(k)),
        "sewer": rng.randint(1, 2000),
        "service": service if service is not None else rng.choice([0, rng.randint(0, 10000), 10000]),
    }


def schedule(rng, first, n=None, span_days=900):
    n = n if n is not None else rng.randint(1, 4)
    days = sorted(rng.sample(range(1, span_days), n - 1))
    return [row(rng, first)] + [row(rng, first + timedelta(days=d)) for d in days]


def reads(rng, start, n, gaps, use_fn, est_prob=0.0, register=None):
    reg = register if register is not None else rng.choice([0, rng.randint(0, 10**7), 99_000_000])
    d = start
    out = [[iso(d), reg, "actual"]]
    for i in range(n - 1):
        d = d + timedelta(days=gaps(rng))
        reg = min(100_000_000, reg + use_fn(rng))
        kind = "estimated" if rng.random() < est_prob else "actual"
        out.append([iso(d), reg, kind])
    return out


def winter(rng, heavy=False):
    n = rng.randint(1, 6)
    if heavy:  # at least 1,500 cubic feet a day: 30,000 or more over any regular cycle
        return [[20, 30000] for _ in range(n)]
    return [[rng.randint(20, 40), rng.choice([0, rng.randint(0, 800), rng.randint(0, 30000)])] for _ in range(n)]


def account(rng, first, units=1, gaps=None, use=None, est=0.0, heavy=False, n=None, lead=None):
    gaps = gaps or (lambda r: r.randint(20, 62))
    use = use or (lambda r: r.choice([0, r.randint(0, 3000), r.randint(0, 40000)]))
    if heavy:
        inner = use
        use = lambda r: min(inner(r), 29000)  # noqa: E731
    start = first + timedelta(days=lead if lead is not None else rng.randint(0, 200))
    return {
        "account": acct_id(rng),
        "units": units,
        "winter": winter(rng, heavy),
        "reads": reads(rng, start, n or rng.randint(2, 10), gaps, use, est),
    }


def first_day(rng):
    return date(2015, 1, 1) + timedelta(days=rng.randint(0, 6000))


def safe_units(rng):
    return rng.choice([1, 1, rng.randint(2, 8)])


def _job(rng, n_rows=None, **acct_kw):
    first = first_day(rng)
    sched = schedule(rng, first, n_rows)
    accts = []
    for _ in range(rng.randint(1, 6)):
        units = acct_kw.pop("units_fn", safe_units)(rng) if "units_fn" in acct_kw else safe_units(rng)
        accts.append(account(rng, first, units=units, heavy=units > 1, **acct_kw))
    return {"schedule": sched, "accounts": accts}


def fam_broad(rng):
    return _job(rng, est=0.3)


def fam_d1(rng):  # 4.2 scaling of a regular cycle
    first = first_day(rng)
    sched = [row(rng, first, blocks=rng.randint(2, 6))]
    accts = [account(rng, first, units=1, use=lambda r: r.randint(0, 30000), gaps=lambda r: r.choice([20, 21, 29, 31, 45, 62]))
             for _ in range(rng.randint(1, 4))]
    return {"schedule": sched, "accounts": accts}


def fam_d2(rng):  # 3.1 service per dwelling unit and day
    first = first_day(rng)
    sched = [row(rng, first, service=rng.randint(1, 10000))]
    accts = [account(rng, first, units=u, heavy=u > 1) for u in rng.sample(range(1, 9), 3)]
    return {"schedule": sched, "accounts": accts}


def fam_d3(rng):  # 5.2 household allowance
    first = first_day(rng)
    sched = [row(rng, first)]
    accts = []
    for _ in range(rng.randint(1, 4)):
        a = account(rng, first, units=1, use=lambda r: r.randint(500, 40000))
        a["winter"] = [[rng.randint(20, 40), rng.randint(0, 900)] for _ in range(rng.randint(1, 6))]
        accts.append(a)
    return {"schedule": sched, "accounts": accts}


def fam_d4(rng):  # 2.5, 6.1 proration across a change
    first = first_day(rng)
    sched = schedule(rng, first, n=rng.randint(2, 4), span_days=300)
    accts = []
    for _ in range(rng.randint(1, 3)):
        units = safe_units(rng)
        accts.append(account(rng, first, lead=0, n=rng.randint(6, 14), units=units, heavy=units > 1))
    return {"schedule": sched, "accounts": accts}


def fam_d5(rng):  # 1.1 exact halves go up
    first = first_day(rng)
    sched = [{"from": iso(first), "widths": [], "prices": [rng.choice([1, 3, 5, 7, 99, 101, 1999])],
              "sewer": rng.choice([1, 3, 11, 1001]), "service": rng.choice([15, 45, 75, 105])}]
    accts = [account(rng, first, units=1, gaps=lambda r: 30, use=lambda r: 100 * r.randint(0, 200) + 50)
             for _ in range(rng.randint(1, 4))]
    for a in accts:
        a["winter"] = [[30, 30000]]
    return {"schedule": sched, "accounts": accts}


def fam_d6(rng):  # 2.2, 4.3 true-up of estimates
    return _job(rng, est=0.6, n=rng.randint(4, 12))


def fam_d7(rng):  # 5.1 sewer on cubic feet
    first = first_day(rng)
    sched = [row(rng, first)]
    accts = [account(rng, first, units=safe_units(rng), heavy=True, use=lambda r: 100 * r.randint(0, 300) + r.randint(1, 99))
             for _ in range(rng.randint(1, 4))]
    return {"schedule": sched, "accounts": accts}


def fam_t1(rng):  # special-read spans (under 20 days) keep the schedule widths
    first = first_day(rng)
    sched = [row(rng, first, blocks=rng.randint(2, 6))]
    accts = [account(rng, first, units=1, use=lambda r: r.randint(100, 30000), gaps=lambda r: r.randint(1, 19), n=rng.randint(3, 8))
             for _ in range(rng.randint(1, 3))]
    return {"schedule": sched, "accounts": accts}


def fam_t2(rng):  # meters serving 2 to 8 dwelling units keep the span's use as sewer volume
    first = first_day(rng)
    sched = [row(rng, first)]
    accts = []
    for _ in range(rng.randint(1, 3)):
        a = account(rng, first, units=rng.randint(2, 8), use=lambda r: r.randint(800, 40000))
        a["winter"] = [[rng.randint(20, 40), rng.randint(0, 600)] for _ in range(rng.randint(1, 6))]
        accts.append(a)
    return {"schedule": sched, "accounts": accts}


FAMILIES = {"broad": fam_broad, "D1": fam_d1, "D2": fam_d2, "D3": fam_d3, "D4": fam_d4, "D5": fam_d5,
            "D6": fam_d6, "D7": fam_d7, "T1": fam_t1, "T2": fam_t2}
TRAP_FAMILIES = {"T1", "T2"}


def trap_inputs(job):
    """Which trap inputs a job carries: T1 = a span under 20 days whose water charge would change if its
    widths were scaled; T2 = a multi-unit span whose use exceeds the household allowance formula."""
    found = set()
    for a in job["accounts"]:
        for s in model.spans(a):
            if s["days"] < model.REGULAR_CYCLE_DAYS:
                for r, _ in model.rows_under(job["schedule"], s):
                    scaled = dict(r, widths=[model.half_up(w * s["days"], 30) for w in r["widths"]])
                    if model.water(dict(scaled), s["use"], 30) != model.water(r, s["use"], s["days"]):
                        found.add("T1")
            if a["units"] > 1:
                wu = sum(u for _, u in a["winter"]); wd = sum(d for d, _ in a["winter"])
                if s["use"] > model.half_up(wu * s["days"], wd):
                    found.add("T2")
    return found

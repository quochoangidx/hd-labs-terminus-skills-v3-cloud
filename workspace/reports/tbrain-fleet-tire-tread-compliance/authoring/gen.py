"""Job generator for tbrain-fleet-tire-tread-compliance (authoring only, never shipped).

FAMILIES maps a family name to fn(rng) -> job. `broad` and D1-D8 are trap-free by construction
(checked by trap_inputs); T1 and T2 each carry only their own trap input."""

import sys
from datetime import date, timedelta
from pathlib import Path

TASK = Path(__file__).resolve().parents[3] / "tasks" / "tbrain-fleet-tire-tread-compliance"
sys.path.insert(0, str(TASK / "solution"))
import model  # noqa: E402

_n = iter(range(10**7))
POS = ["steer", "drive", "trailer"]


def uid(rng, prefix):
    return f"{prefix}{rng.randint(1, 99)}-{next(_n):05d}"


def iso(d):
    return d.isoformat()


def gauges(rng, nonzero=False):
    out = []
    for _ in range(rng.randint(1, 6)):
        off = rng.choice([o for o in range(-9, 10) if o]) if nonzero else rng.randint(-9, 9)
        out.append({"gauge": uid(rng, "G"), "offset": off})
    return out


def tire(rng, gs, report, reads_n=None, position=None, new=None, casing=None, retreads=None, end_depth=None, step=None):
    """end_depth is the latest reading's depth (after offset)."""
    off = {g["gauge"]: g["offset"] for g in gs}
    n = reads_n or rng.randint(2, 12)
    new = new if new is not None else rng.randint(60, 320)
    mounted = rng.randint(0, 4_000_000)
    days = sorted(rng.sample(range(0, 1500), n), reverse=True)
    dates = [iso(report - timedelta(days=d)) for d in days]
    gz = [rng.choice(gs)["gauge"] for _ in range(n)]
    first_depth = new - rng.randint(0, 10)
    last_depth = end_depth if end_depth is not None else rng.randint(19, first_depth)
    mids = sorted((rng.randint(min(last_depth, first_depth), first_depth) for _ in range(n - 2)), reverse=True)
    wanted = [first_depth] + mids + [last_depth]
    reads, km = [], mounted
    for i in range(n):
        km += step(rng) if step else rng.randint(1, 60000)
        shown = max(10, min(320, wanted[i] - off[gz[i]]))
        reads.append([dates[i], min(km, 5_000_000), shown, gz[i]])
    reads[0][2] = min(320, max(10, new - rng.randint(0, 10) - off[gz[0]]))
    return {"tire": uid(rng, "T"), "position": position or rng.choice(POS), "new_depth": new,
            "casing": casing or iso(max(date(2015, 1, 1), report - timedelta(days=rng.randint(1600, 4000)))),
            "retreads": retreads if retreads is not None else rng.randint(0, 4), "mounted_km": mounted,
            "readings": reads}


def job(rng, n=None, want=frozenset(), nonzero=False, report=None, **kw):
    """A job whose trap inputs are exactly `want` (tires are redrawn until each carries none, or the wanted)."""
    report = report or date(2016, 1, 1) + timedelta(days=rng.randint(1500, 6900))
    gs = gauges(rng, nonzero)
    tires = []
    goal = n or rng.randint(1, 6)
    while len(tires) < goal:
        kwargs = {k: (v(rng) if callable(v) and k != 'step' else v) for k, v in kw.items()}
        t = tire(rng, gs, report, **kwargs)
        j = {"report_date": iso(report), "gauges": gs, "tires": [t]}
        if model.within_limits(j):
            continue
        got = trap_inputs(j)
        if got == set(want) or not got:
            if want and not got and len(tires) == goal - 1 and not trap_inputs({"report_date": iso(report), "gauges": gs, "tires": tires}):
                continue  # the last tire must carry the wanted trap if none does yet
            tires.append(t)
    return {"report_date": iso(report), "gauges": gs, "tires": tires}


def fam_broad(rng):
    return job(rng)


def fam_d1(rng):  # 3.1 offsets
    return job(rng, nonzero=True)


def fam_d2(rng):  # 4.2 from new depth and mounting odometer
    return job(rng)


def fam_d3(rng):  # 2.2 removal depths
    return job(rng, n=4, end_depth=lambda r: r.choice([29, 30, 31, 32, 33, 39, 40, 41, 46, 47, 48, 56]))


def fam_d4(rng):  # 5.1 at or below
    return job(rng, n=4, position=lambda r: r.choice(POS),
               end_depth=lambda r: r.choice([30, 46, 40, 56]))


def fam_d5(rng):  # 1.1 exact halves in the wear rate: distance 20,000 km from mounting
    return job(rng, n=3, step=lambda r: 10000, reads_n=2, retreads=0)


def fam_d6(rng):  # 6.1 casing age in days
    report = date(2016, 1, 1) + timedelta(days=rng.randint(2500, 6900))
    return job(rng, n=3, report=report, casing=lambda r: iso(report - timedelta(days=r.choice([2189, 2190, 2100, 2250]))),
               retreads=lambda r: r.randint(0, 1), end_depth=lambda r: r.randint(19, 29))


def fam_d7(rng):  # 6.1 fewer than two retreads
    return job(rng, retreads=2, end_depth=lambda r: r.randint(19, 29))


def fam_d8(rng):  # 6.1 only a pulled tire goes for retread
    return job(rng, retreads=0)


def fam_t1(rng):  # km_left keeps today's rounding of an exact half
    return job(rng, n=3, want={"T1"}, step=lambda r: r.choice([2500, 5000, 1250, 3125]))


def fam_t2(rng):  # the regrooving check keeps today's floor
    return job(rng, n=3, want={"T2"}, position=lambda r: r.choice(["drive", "trailer"]),
               end_depth=lambda r: r.choice([50, 51, 50, 70]))


FAMILIES = {"broad": fam_broad, "D1": fam_d1, "D2": fam_d2, "D3": fam_d3, "D4": fam_d4, "D5": fam_d5,
            "D6": fam_d6, "D7": fam_d7, "D8": fam_d8, "T1": fam_t1, "T2": fam_t2}
TRAP_FAMILIES = {"T1", "T2"}


def trap_inputs(j):
    """T1 = a tire whose km_left differs between half-even and half-up rounding;
    T2 = a drive or trailer tire whose latest depth is 50 or 51 (the regroove floor moves with REMOVAL)."""
    found = set()
    for e in model.summary(j)["tires"]:
        lim = model.REMOVAL[e["position"]]
        if e["rate"] > 0 and model.half_even((e["latest"] - lim) * model.PER_KM, e["rate"]) != \
                model.half_up((e["latest"] - lim) * model.PER_KM, e["rate"]):
            found.add("T1")
        if e["position"] != "steer" and e["latest"] in (50, 51):
            found.add("T2")
    return found

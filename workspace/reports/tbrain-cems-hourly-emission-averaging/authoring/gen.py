"""Seeded job generators for tbrain-cems-hourly-emission-averaging (authoring only, never shipped).

FAMILIES maps a family name to fn(rng) -> job. `broad` is trap-free and mixes every governed hour
shape; D1..D9 stress one departure each (trap-free); T1 and T2 carry exactly one trap's inputs.
`fuzz` (not a scorer family) draws everything section 1 allows, trap inputs included.
trap_inputs(job) names the trap inputs a job holds, from the model's reading of DRP-4.
"""

import datetime
import sys
from fractions import Fraction
from pathlib import Path

TASK = Path(__file__).resolve().parents[3] / "tasks" / "tbrain-cems-hourly-emission-averaging"
sys.path.insert(0, str(TASK / "solution"))
import model  # noqa: E402

BAD = ("MNT", "OOC", "CAL")


def _start(rng):
    d = datetime.datetime(rng.randint(2020, 2039), rng.randint(1, 12), rng.randint(1, 28))
    if d.year == 2039 and d.month >= 9:
        d = d.replace(month=rng.randint(1, 8))
    return d


def _q(rng, load, o2lo=20, o2hi=180, code="OK"):
    return [load, rng.randint(0, 20000) if rng.random() < 0.05 else rng.randint(200, 2500),
            rng.randint(o2lo, o2hi), rng.randint(1_000_000, 90_000_000) if rng.random() < 0.3
            else rng.randint(0, 90_000_000), code]


def _on(rng):
    return rng.choice([1, rng.randint(1, 1500), 1500, rng.randint(200, 900)])


# ---- hour shapes: each returns four quarter bodies [load, nox, o2, flow, code] ----

def h_off(rng):
    return [_q(rng, 0, 150, 205, rng.choice(("OK", "OK", "OK", "MNT", "OOC"))) for _ in range(4)]


def h_full(rng):
    return [_q(rng, _on(rng)) for _ in range(4)]


def h_partial(rng, off_code=None):
    """1-3 operating quarters, all OK; the rest off (coded OK unless off_code)."""
    n = rng.randint(1, 3)
    on = set(rng.sample(range(4), n))
    out = []
    for k in range(4):
        if k in on:
            out.append(_q(rng, _on(rng)))
        else:
            out.append(_q(rng, 0, 20, 205, off_code or rng.choice(("OK", "OK", "MNT", "OOC"))))
    return out


def h_cal(rng):
    """Operating hour with a CAL record and two or more valid readings, some quarter not OK."""
    while True:
        qs = [_q(rng, _on(rng)) for _ in range(4)]
        k = rng.randrange(4)
        qs[k][4] = "CAL"
        others = [j for j in range(4) if j != k]
        for j in rng.sample(others, rng.randint(0, 1)):
            qs[j][4] = "CAL"
        if rng.random() < 0.3:
            j = rng.choice(others)
            if qs[j][4] != "CAL":
                qs[j][0] = 0
        good = sum(1 for q in qs if q[0] >= 1 and q[4] == "OK")
        if good >= 2:
            return qs


def h_lost(rng):
    qs = []
    codes = ("CAL",) if rng.random() < 0.2 else ("MNT", "OOC")
    for _ in range(4):
        if rng.random() < 0.8:
            qs.append(_q(rng, _on(rng), code=rng.choice(codes)))
        else:
            qs.append(_q(rng, 0, 20, 205, "OK" if codes == ("CAL",) else rng.choice(("OK", "MNT"))))
    if all(q[0] == 0 for q in qs):
        qs[0][0] = 5
        qs[0][4] = codes[0]
    return qs


def h_incomplete(rng):
    """T1 input: an operating hour with a valid reading that is neither valid nor lost."""
    while True:
        qs = [_q(rng, _on(rng)) for _ in range(4)]
        bad = rng.sample(range(4), rng.randint(1, 3))
        codes = ("CAL",) if rng.random() < 0.25 else ("MNT", "OOC")
        for j in bad:
            qs[j][4] = rng.choice(codes)
        good = sum(1 for q in qs if q[4] == "OK")
        has_cal = any(q[4] == "CAL" for q in qs)
        if good >= 1 and not (has_cal and good >= 2):
            return qs


def h_lean(rng):
    """T2 input: a valid hour whose oxygen average is 190 or more."""
    lo, hi = rng.choice(((190, 199), (190, 199), (192, 197), (200, 205), (190, 205)))
    return [_q(rng, _on(rng), lo, hi) for _ in range(4)]


# ---- job assembly ----

def job_from_hours(rng, shapes, ref=None, limit=None, start=None):
    t = start or _start(rng)
    readings = []
    for qs in shapes:
        for q in qs:
            readings.append([t.strftime("%Y-%m-%d %H:%M")] + q)
            t += datetime.timedelta(minutes=15)
    ref = rng.choice((0, 30, 30, 70, 150, rng.randint(0, 150))) if ref is None else ref
    limit = rng.choice((1, 20000, rng.randint(300, 3000))) if limit is None else limit
    return {"unit": {"ref_o2": ref, "limit": limit}, "readings": readings}


def day_shapes(rng, pick, hours=24):
    return [pick(rng) for _ in range(hours)]


def governed_pick(weights):
    def pick(rng):
        r = rng.random()
        acc = 0.0
        for fn, w in weights:
            acc += w
            if r < acc:
                return fn(rng)
        return weights[-1][0](rng)
    return pick


BROAD_PICK = governed_pick([(h_full, 0.55), (h_off, 0.15), (h_partial, 0.1), (h_cal, 0.08), (h_lost, 0.12)])


def fam_broad(rng):
    days = rng.randint(31, 38)
    shapes = []
    for _ in range(days):
        if rng.random() < 0.15:
            shapes += day_shapes(rng, h_off)
        else:
            shapes += day_shapes(rng, BROAD_PICK)
    return job_from_hours(rng, shapes)


def fam_d1(rng):  # 3.1 averages over valid readings only: partial hours with OK off quarters
    shapes = []
    for _ in range(rng.randint(24, 72)):
        shapes.append(rng.choice((lambda r: h_partial(r, "OK"), h_full, h_off))(rng))
    return job_from_hours(rng, shapes)


def fam_d2(rng):  # 2.3 minimum data: CAL hours and partial hours with a bad-coded off quarter
    shapes = []
    for _ in range(rng.randint(24, 72)):
        shapes.append(rng.choice((h_cal, lambda r: h_partial(r, rng.choice(("MNT", "OOC"))), h_full))(rng))
    return job_from_hours(rng, shapes)


def fam_d3(rng):  # 3.2 ambient 20.9 in a firing hour
    return job_from_hours(rng, [h_full(rng) for _ in range(rng.randint(12, 48))])


def fam_d4(rng):  # 3.3 mass rate from the measured NOx average
    return job_from_hours(rng, [h_full(rng) for _ in range(rng.randint(12, 48))], ref=rng.choice((0, 30, 150)))


def fam_d5(rng):  # 5.1 mass times operating time
    return job_from_hours(rng, [rng.choice((lambda r: h_partial(r, "OK"), h_full))(rng)
                                for _ in range(rng.randint(24, 72))])


def fam_d6(rng):  # 4.2-4.3 lost hours: runs between valid hours and at either end
    shapes = [h_lost(rng) for _ in range(rng.randint(0, 3))]
    for _ in range(rng.randint(8, 20)):
        shapes += [h_full(rng) for _ in range(rng.randint(1, 3))]
        shapes += [rng.choice((h_lost, h_lost, h_off))(rng) for _ in range(rng.randint(1, 4))]
    return job_from_hours(rng, shapes)


def _rolling_job(rng, off_day_share):
    shapes = []
    op_days = 0
    while op_days < rng.randint(31, 36):
        if rng.random() < off_day_share:
            shapes += day_shapes(rng, h_off)
        else:
            shapes += day_shapes(rng, BROAD_PICK, 24)
            op_days += 1
    return job_from_hours(rng, shapes)


def fam_d7(rng):  # 6.1 thirty operating days, not calendar days
    return _rolling_job(rng, 0.3)


def fam_d8(rng):  # 6.1 average of valid hours' concentrations, not of daily means of all hours
    shapes = []
    for _ in range(rng.randint(31, 34)):
        n_on = rng.randint(1, 24)
        pick = governed_pick([(h_full, 0.6), (h_lost, 0.4)])
        shapes += [pick(rng) for _ in range(n_on)] + [h_off(rng) for _ in range(24 - n_on)]
    return job_from_hours(rng, shapes)


def fam_d9(rng):  # 6.2 an exceedance day is above the limit, not at it
    job = _rolling_job(rng, 0.0)
    rolls = [d["rolling"] for d in model.report(job)["days"] if d["rolling"] is not None]
    job["unit"]["limit"] = max(1, min(20000, rng.choice(rolls)))
    return job


def fam_t1(rng):
    shapes = []
    for _ in range(rng.randint(10, 24)):
        shapes += [h_full(rng) for _ in range(rng.randint(1, 3))]
        shapes += [rng.choice((h_lost, h_off))(rng) for _ in range(rng.choice((0, 1, 1, 2)))]
        shapes += [rng.choice((h_incomplete, h_incomplete, h_lost, h_off))(rng) for _ in range(rng.randint(1, 3))]
    return job_from_hours(rng, shapes)


def fam_t2(rng):
    shapes = []
    for _ in range(rng.randint(12, 36)):
        shapes.append(rng.choice((h_lean, h_lean, h_full))(rng))
    return job_from_hours(rng, shapes)


def fam_fuzz(rng):
    pick = governed_pick([(h_full, 0.35), (h_off, 0.15), (h_partial, 0.1), (h_cal, 0.1), (h_lost, 0.1),
                          (h_incomplete, 0.1), (h_lean, 0.1)])
    days = rng.choice((1, 2, rng.randint(1, 40)))
    shapes = []
    for _ in range(days):
        shapes += day_shapes(rng, pick if rng.random() > 0.2 else h_off)
    job = job_from_hours(rng, shapes)
    cut = rng.randint(0, 3)
    job["readings"] = job["readings"][cut:]  # start at any quarter
    if not job["readings"]:
        job["readings"] = [[job_from_hours(rng, [h_full(rng)])["readings"][0][0], 1, 0, 0, 0, "OK"]]
    return job


FAMILIES = {"broad": fam_broad, "D1": fam_d1, "D2": fam_d2, "D3": fam_d3, "D4": fam_d4, "D5": fam_d5,
            "D6": fam_d6, "D7": fam_d7, "D8": fam_d8, "D9": fam_d9, "T1": fam_t1, "T2": fam_t2}
TRAP_FAMILIES = {"T1", "T2"}


def trap_inputs(job):
    """Which trap inputs the job holds: T1 = an operating hour neither valid nor lost; T2 = a valid
    hour whose oxygen average is 190 or more."""
    found = set()
    hours = {}
    for rec in job["readings"]:
        hours.setdefault(rec[0][:13], []).append(rec)
    for recs in hours.values():
        op = [r for r in recs if r[1] >= 1]
        if not op:
            continue
        good = [r for r in op if r[5] == "OK"]
        valid = len(good) == len(op) or (any(r[5] == "CAL" for r in recs) and len(good) >= 2)
        if not valid and good:
            found.add("T1")
        if valid and Fraction(sum(r[3] for r in good), len(good)) >= 190:
            found.add("T2")
    return found

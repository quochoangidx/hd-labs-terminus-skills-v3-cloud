"""Random network forms within handbook CN-7 part 3 clause 1.5 (authoring only, never shipped)."""

import importlib.util
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK = HERE.parents[2] / "tasks" / "tbrain-climate-observer-monthly-summary"

_spec = importlib.util.spec_from_file_location("coop_model", TASK / "solution" / "model.py")
model = importlib.util.module_from_spec(_spec)
sys.modules["coop_model"] = model
_spec.loader.exec_module(model)


def fmt_temp(t):
    sign = "-" if t < 0 else ""
    return f"{sign}{abs(t) // 10}.{abs(t) % 10}"


def fmt_amt(h):
    return f"{h // 100}.{h % 100:02d}"


def rand_month(rng):
    r = rng.random()
    if r < 0.15:
        year = rng.choice([y for y in range(1952, 2097, 4)])
        return f"{year}-02"
    if r < 0.25:
        return rng.choice(["1950-01", "2099-12", "2000-02", "2099-02", "1950-02"])
    return f"{rng.randint(1950, 2099)}-{rng.randint(1, 12):02d}"


def rand_hour(rng, morning=None):
    if morning is None:
        return rng.choice([0, 5, 6, 7, 8, 11, 12, 16, 17, 18, 23, rng.randint(0, 23)])
    if morning:
        return rng.choice([0, 6, 7, 8, 11, rng.randint(0, 11)])
    return rng.choice([12, 16, 17, 18, 23, rng.randint(12, 23)])


def clamp(t):
    return max(-600, min(1300, t))


def rand_temps(rng, n, wide=False):
    """n + 1 (max, min) pairs in tenths, following a seasonal regime."""
    base = rng.randint(-450, 1150) if wide else rng.randint(-200, 950)
    spread = rng.randint(0, 400)
    out = []
    for _ in range(n + 1):
        base = clamp(base + rng.randint(-60, 60))
        hi = clamp(base + rng.randint(0, spread) // 2 + rng.randint(-30, 30))
        lo = clamp(hi - rng.randint(0, spread))
        if wide and rng.random() < 0.03:
            hi = rng.choice([1300, -600, 900, 320, 0])
        if wide and rng.random() < 0.03:
            lo = rng.choice([-600, 1300, 320, 0, -1])
        out.append((hi, lo))
    return out


def rand_amount(rng, wide=False):
    r = rng.random()
    if r < 0.45:
        return "0.00"
    if r < 0.6:
        return "T"
    if r < 0.9:
        return fmt_amt(rng.randint(1, 120))
    if wide and r < 0.93:
        return fmt_amt(rng.choice([1, 9, 10, 11, 99, 100, 101, 2000]))
    return fmt_amt(rng.randint(1, 2000 if wide else 600))


def rand_station(rng, sid, n, *, morning=None, missing=(0, 3), unread_ok=True, wide=False, trace_rate=None):
    hour = rand_hour(rng, morning)
    temps = rand_temps(rng, n, wide)
    entries = []
    for hi, lo in temps:
        entries.append({"max": fmt_temp(hi), "min": fmt_temp(lo), "precip": rand_amount(rng, wide)})
        if trace_rate is not None and rng.random() < trace_rate:
            entries[-1]["precip"] = "T"
    for key in ("max", "min"):
        for _ in range(rng.randint(*missing)):
            entries[rng.randint(0, n)][key] = "M"
    for _ in range(rng.randint(0, 3)):
        entries[rng.randint(0, n)]["precip"] = "M"
    if unread_ok:
        for _ in range(rng.randint(0, 2)):
            start = rng.randint(1, n - 1)
            length = rng.randint(1, 6)
            if start + length > n:
                continue
            for k in range(start, start + length):
                entries[k]["precip"] = "A"
            if entries[start + length]["precip"] in ("M", "A"):
                entries[start + length]["precip"] = fmt_amt(rng.randint(0, 2000))
            elif rng.random() < 0.7:
                entries[start + length]["precip"] = fmt_amt(rng.randint(20, 2000))
    fix_runs(entries)
    return {"id": sid, "hour": hour, "days": entries[:n], "next": entries[n]}


def fix_runs(entries):
    """Keep the A rules of 1.5: never followed by M, at most six in a row, never last, never first-of-next."""
    run = 0
    for k, e in enumerate(entries):
        if e["precip"] == "A":
            run += 1
            if run > 6 or k == len(entries) - 1:
                e["precip"] = "0.00"
                run = 0
            continue
        if run and e["precip"] == "M":
            e["precip"] = "0.00"
        run = 0


def rand_id(rng, used):
    while True:
        sid = rng.choice(["CN", "WX", "CO", ""]) + f"{rng.randint(0, 99999):05d}" + rng.choice(["", "-A", " North"])
        if sid not in used:
            used.add(sid)
            return sid


def rand_form(rng, *, stations=None, trap_free=False, wide=True):
    month = rand_month(rng)
    n = model.days_in(month)
    k = stations or rng.choice([1, 1, 2, 3, 5, 8, rng.randint(1, 40)])
    used = set()
    out = []
    for _ in range(k):
        if trap_free:
            morning = rng.random() < 0.5
            st = rand_station(rng, rand_id(rng, used), n, morning=morning, missing=(0, 2),
                              unread_ok=not morning, wide=wide)
        else:
            st = rand_station(rng, rand_id(rng, used), n, missing=rng.choice([(0, 2), (0, 8), (4, 20), (0, 31)]),
                              wide=wide)
        out.append(st)
    form = {"network": rng.choice(["Upper Basin Cooperative Network", "", "Réseau Nord \"B\""]), "month": month,
            "stations": out}
    model.within_limits(form)
    return form


def broad_form(rng):
    """A trap-free form: every month complete for temperature, no accumulated amount at a morning station."""
    while True:
        form = rand_form(rng, trap_free=True)
        if not model.carries_accumulated_at_morning(form) and not model.carries_incomplete_month(form):
            return form

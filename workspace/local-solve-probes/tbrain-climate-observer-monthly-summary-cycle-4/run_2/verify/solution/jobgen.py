"""Seeded forms for every verifier family (used by seal.py; never imported by the verifier).

Every form keeps within handbook 1.5. Trap inputs (an accumulated amount at a morning station; a month
whose gap count is six or more) appear only in the families named for them.
"""

import random

import model

SEED = 20260927
NET = "Upper Basin Cooperative Network"


def ft(t):
    return ("-" if t < 0 else "") + f"{abs(t) // 10}.{abs(t) % 10}"


def fa(h):
    return f"{h // 100}.{h % 100:02d}"


class Gen:
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.ids = 0

    def sid(self):
        self.ids += 1
        r = self.rng
        return r.choice(["CN-", "WX", "", "coop "]) + f"{r.randint(0, 99999):05d}" + r.choice(["", "-A", " north"]) + f"/{self.ids}"

    def month(self, fixed=None):
        if fixed:
            return fixed
        r = self.rng
        return f"{r.randint(1950, 2099)}-{r.randint(1, 12):02d}"

    def temps(self, n, base=None, spread=None):
        r = self.rng
        base = r.randint(-150, 900) if base is None else base
        spread = r.randint(40, 250) if spread is None else spread
        out = []
        for _ in range(n + 1):
            base = max(-550, min(1200, base + r.randint(-40, 40)))
            hi = base + r.randint(0, spread)
            lo = hi - r.randint(20, spread + 20)
            out.append([max(-600, min(1300, hi)), max(-600, min(1300, lo))])
        return out

    def rain(self, n, wet=0.35, trace=0.1):
        r = self.rng
        out = []
        for _ in range(n + 1):
            x = r.random()
            out.append(fa(r.choice([r.randint(1, 60), r.randint(11, 180), r.randint(1, 9)])) if x < wet
                       else ("T" if x < wet + trace else "0.00"))
        return out

    def station(self, month, hour, temps=None, rain=None):
        n = model.days_in(month)
        temps = temps or self.temps(n)
        rain = rain or self.rain(n)
        rows = [{"max": ft(hi), "min": ft(lo), "precip": p} for (hi, lo), p in zip(temps, rain)]
        return {"id": self.sid(), "hour": hour, "days": rows[:n], "next": rows[n]}

    def hour(self, morning):
        r = self.rng
        return r.choice([0, 6, 7, 8, 11]) if morning else r.choice([12, 16, 17, 18, 23])


def form(month, stations, network=NET):
    return {"network": network, "month": month, "stations": stations}


def rows(st):
    return st["days"] + [st["next"]]


# -- families --------------------------------------------------------------------------------------

def fam_traces(g):
    out = []
    for k in range(3):
        m = g.month()
        n = model.days_in(m)
        a = g.station(m, g.hour(k % 2 == 0), rain=g.rain(n, wet=0.25, trace=0.45))
        b = g.station(m, g.hour(k % 2 == 1), rain=[g.rng.choice(["T", "T", "0.00"]) for _ in range(n + 1)])
        out.append(form(m, [a, b] if k else [b]))
    return out


def fam_hour_edges(g):
    out = []
    for m in ("2031-05",):
        sts = []
        for h in (0, 11, 12, 23):
            s = g.station(m, h)
            s["days"][0]["max"] = ft(1000 + h)  # a form-day-1 maximum that becomes the month's highest when kept
            s["next"]["max"] = ft(1100 + h)
            s["next"]["precip"] = fa(250 + h)
            s["days"][0]["precip"] = fa(260 + h)
            sts.append(s)
        out.append(form(m, sts))
    return out


def fam_morning_maximum(g):
    out = []
    for h in (0, 7, 11):
        m = g.month()
        s = g.station(m, h, rain=["0.00"] * (model.days_in(m) + 1))
        n = len(s["days"])
        d = g.rng.randint(2, n - 2)
        s["days"][d]["max"] = "99.9"   # credited to the day before
        s["days"][d]["min"] = "-41.2"  # credited to its form day
        s["next"]["max"] = "98.4"
        out.append(form(m, [s]))
    return out


def fam_morning_precipitation(g):
    out = []
    for h in (0, 7, 11):
        m = g.month()
        n = model.days_in(m)
        s = g.station(m, h, rain=g.rain(n, wet=0.3, trace=0.0))
        s["days"][0]["precip"] = "3.17"
        s["next"]["precip"] = "2.44"
        d = g.rng.randint(3, n - 3)
        s["days"][d]["precip"] = "M"  # the gauge is still emptied: the next reading is a day's precipitation
        s["days"][d + 1]["precip"] = "4.05"
        out.append(form(m, [s]))
    return out


def fam_gap_count(g):
    out = []
    for k, m in enumerate(("2024-02", "2023-02", "2040-07")):
        n = model.days_in(m)
        s = g.station(m, g.hour(True) if k != 1 else 17)
        morning = s["hour"] <= 11
        # morning: form day 1's maximum leaves the month anyway, so an M there lacks nothing
        if morning:
            s["days"][0]["max"] = "M"
            s["next"]["max"] = "M"  # the month's last day lacks a maximum
        picks = g.rng.sample(range(2, n), 8)
        for d in picks[:4 if morning else 5]:
            s["days"][d]["max"] = "M"
        for d in picks[3:8]:
            s["days"][d]["min"] = "M"
        out.append(form(m, [s]))
    return out


def fam_means(g):
    out = []
    for base, m in ((-300, "2024-04"), (-40, "2023-02"), (500, "2061-06")):
        n = model.days_in(m)
        s = g.station(m, 17, temps=g.temps(n, base=base, spread=60), rain=["0.00"] * (n + 1))
        # tune the first maximum until the mean maximum sits on a half tenth
        total = sum(model.temp_tenths(r["max"]) for r in s["days"])
        need = (n * (2 * (total // n) + 1)) // 2 if n % 2 == 0 else None
        if need is not None:
            s["days"][0]["max"] = ft(model.temp_tenths(s["days"][0]["max"]) + need - total)
        out.append(form(m, [s]))
    return out


def fam_tied_temperatures(g):
    out = []
    for h in (7, 17, 23):
        m = g.month()
        s = g.station(m, h, rain=["0.00"] * (model.days_in(m) + 1))
        n = len(s["days"])
        a, b = sorted(g.rng.sample(range(2, n - 1), 2))
        s["days"][a]["max"] = s["days"][b]["max"] = "120.5"
        s["days"][a]["min"] = s["days"][b]["min"] = "-59.5"
        out.append(form(m, [s]))
    return out


def fam_well_observed_mean(g):
    out = []
    for h in (17, 7, 12):
        m = g.month()
        n = model.days_in(m)
        s = g.station(m, h, temps=g.temps(n, spread=300), rain=["0.00"] * (n + 1))
        for d in g.rng.sample(range(2, n - 1), 3):
            s["days"][d]["max"] = "M"
        for d in g.rng.sample(range(2, n - 1), 2):
            s["days"][d]["min"] = "M"
        out.append(form(m, [s]))
    return out


def fam_degree_days(g):
    out = []
    for base in (620, 660, -45):
        m = g.month()
        n = model.days_in(m)
        temps = []
        for _ in range(n + 1):
            hi = base + g.rng.randint(0, 60)
            lo = hi - 2 * g.rng.randint(0, 20) - 5  # hi + lo is odd: every day's mean ends in .x5 or .x0
            temps.append([hi, lo])
        s = g.station(m, 17, temps=temps, rain=["0.00"] * (n + 1))
        s["days"][3]["max"], s["days"][3]["min"] = "70.0", "60.0"  # a mean of exactly 65.0
        s["days"][4]["max"], s["days"][4]["min"] = "70.0", "58.9"  # 64.45 rounds to 64, not 65
        out.append(form(m, [s]))
    return out


def fam_thresholds(g):
    out = []
    for h in (17, 8):
        m = g.month()
        s = g.station(m, h)
        n = len(s["days"])
        for d, (hi, lo) in zip(g.rng.sample(range(2, n), 5),
                               [("90.0", "32.0"), ("32.0", "0.0"), ("90.0", "0.0"), ("89.9", "32.1"), ("32.1", "0.1")]):
            s["days"][d]["max"], s["days"][d]["min"] = hi, lo
        out.append(form(m, [s]))
    return out


def fam_heavy_days(g):
    out = []
    for h in (17, 23):
        m = g.month()
        n = model.days_in(m)
        s = g.station(m, h, rain=["0.00"] * (n + 1))
        for d, p in zip(g.rng.sample(range(0, n), 6), ["0.10", "1.00", "0.09", "0.99", "1.00", "0.10"]):
            s["days"][d]["precip"] = p
        out.append(form(m, [s]))
    return out


def fam_tied_precipitation(g):
    out = []
    for h in (18, 6):
        m = g.month()
        n = model.days_in(m)
        s = g.station(m, h, rain=g.rain(n, wet=0.3, trace=0.1))
        a, b = sorted(g.rng.sample(range(2, n - 1), 2))
        s["days"][a]["precip"] = s["days"][b]["precip"] = "5.55"
        out.append(form(m, [s]))
    return out


def fam_accumulated_morning(g):
    out = []
    for k, h in enumerate((7, 0, 11, 6)):
        m = g.month()
        n = model.days_in(m)
        s = g.station(m, h, rain=g.rain(n, wet=0.3, trace=0.1))
        length = [2, 1, 6, 3][k]
        start = n - length if k == 3 else g.rng.randint(2, n - length - 2)
        for d in range(start, start + length):
            rows(s)[d]["precip"] = "A"
        rows(s)[start + length]["precip"] = fa([655, 1840, 2000, 915][k])
        if k == 2:  # the next day's reading lands on the same day: 20.00 + 20.00 credited to one day
            rows(s)[start + length + 1]["precip"] = "20.00"
        out.append(form(m, [s]))
    return out


def fam_gappy_months(g):
    out = []
    for k, (h, gaps) in enumerate([(17, 6), (7, 11), (12, 20), (18, 99)]):
        m = g.month()
        n = model.days_in(m)
        s = g.station(m, h, temps=g.temps(n, spread=300))
        key = "max" if k % 2 == 0 else "min"
        for d in g.rng.sample(range(1, n), gaps) if gaps < 99 else range(n + 1):
            rows(s)[d][key] = "M"
        if gaps == 99:  # no day has a mean temperature at all
            for r in rows(s):
                r["max"] = "M"
        out.append(form(m, [s]))
    return out


def fam_limits(g):
    m = "2096-02"
    n = model.days_in(m)
    sts = [g.station(m, g.rng.randint(0, 23), temps=g.temps(n, spread=100), rain=g.rain(n, wet=0.2, trace=0.05)) for _ in range(40)]
    for s in sts:
        if s["hour"] <= 11:
            s["hour"] += 12  # keep the forty-station form free of trap inputs
    a = g.station("1950-01", 23)
    a["days"][4]["max"], a["days"][9]["min"] = "130.0", "-60.0"
    a["days"][12]["precip"] = "20.00"
    for d in range(20, 26):
        a["days"][d]["precip"] = "A"  # six unread observations at an afternoon station
    a["days"][26]["precip"] = "20.00"
    b = g.station("2099-12", 0)
    b["days"][1]["max"], b["next"]["max"] = "-60.0", "130.0"
    b["days"][5]["precip"] = "20.00"
    c = g.station("2099-12", 13, rain=["20.00"] * 32)  # 20.00 inches every day: 620.00 for the month
    return [form(m, sts), form("1950-01", [a]), form("2099-12", [b, c], network="")]


def fam_generated(g):
    out = []
    for k in range(6):
        m = g.month()
        n = model.days_in(m)
        sts = []
        for j in range([1, 2, 3, 3, 2, 1][k]):
            morning = g.rng.random() < 0.5
            s = g.station(m, g.hour(morning), rain=g.rain(n, wet=g.rng.choice([0.1, 0.3, 0.6]), trace=0.1))
            for d in g.rng.sample(range(n + 1), g.rng.randint(0, 3)):
                rows(s)[d][g.rng.choice(["max", "min", "precip"])] = "M"
            if not morning and g.rng.random() < 0.6:
                st = g.rng.randint(2, n - 4)
                rows(s)[st]["precip"] = "A"
                rows(s)[st + 1]["precip"] = fa(g.rng.randint(0, 900))
            sts.append(s)
        out.append(form(m, sts, network=["Réseau \"Nord\"", NET, "x"][k % 3]))
    return out


FAMILIES = {
    "traces": fam_traces, "hour_edges": fam_hour_edges, "morning_maximum": fam_morning_maximum,
    "morning_precipitation": fam_morning_precipitation, "gap_count": fam_gap_count, "means": fam_means,
    "tied_temperatures": fam_tied_temperatures, "well_observed_mean": fam_well_observed_mean,
    "degree_days": fam_degree_days, "thresholds": fam_thresholds, "heavy_days": fam_heavy_days,
    "tied_precipitation": fam_tied_precipitation, "accumulated_morning": fam_accumulated_morning,
    "gappy_months": fam_gappy_months, "limits": fam_limits, "generated": fam_generated,
}
TRAP_FAMILIES = {"accumulated_morning": "accumulated_at_morning", "gappy_months": "gap_count_above_five"}


def families():
    g = Gen(SEED)
    return {name: fn(g) for name, fn in FAMILIES.items()}

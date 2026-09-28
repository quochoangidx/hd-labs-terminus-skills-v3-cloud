"""Adapter for fixture_bounds_check.py: the extremes the sealed forms reach, per ranges.json key."""


def _days(month):
    y, m = int(month[:4]), int(month[5:])
    return [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]


def _t(text):
    whole, frac = text.lstrip("-").split(".")
    return (-1 if text.startswith("-") else 1) * (int(whole) * 10 + int(frac))


def observe(rows):
    out = {k: [] for k in ("month_index", "stations", "hour", "temperature", "amount", "unread_run", "days", "gap_count", "day_total", "month_total")}
    for row in rows:
        form = row.get("form")
        if not form:
            continue
        m = form["month"]
        out["month_index"].append((int(m[:4]) - 1950) * 12 + int(m[5:]) - 1)
        out["stations"].append(len(form["stations"]))
        n = _days(m)
        out["days"].append(n)
        for s in form["stations"]:
            out["hour"].append(s["hour"])
            entries = [e.split(" ") for e in s["days"] + [s["next"]]]
            run = 0
            for hi, lo, p in entries:
                for v in (hi, lo):
                    if v != "M":
                        out["temperature"].append(_t(v))
                if p == "A":
                    run += 1
                    continue
                if run:
                    out["unread_run"].append(run)
                run = 0
                if p not in ("M", "T"):
                    w, f = p.split(".")
                    out["amount"].append(int(w) * 100 + int(f))
            shift = 1 if s["hour"] <= 11 else 0
            highs = {k + 1 - shift for k, e in enumerate(entries) if e[0] != "M"} & set(range(1, n + 1))
            lows = {k + 1 for k, e in enumerate(entries) if e[1] != "M"} & set(range(1, n + 1))
            out["gap_count"].append(max(n - len(highs), n - len(lows)))
        summary = row.get("summary")
        for st in summary["stations"]:
            out["month_total"].append(round(st[17] * 100))
            if st[21] is not None:
                out["day_total"].append(round(st[21] * 100))
    return out

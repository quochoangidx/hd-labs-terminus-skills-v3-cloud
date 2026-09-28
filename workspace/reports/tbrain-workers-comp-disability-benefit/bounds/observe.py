"""Adapter for fixture_bounds_check.py: the extremes the sealed jobs reach, per ranges.json key.

limits_job holds five claims that the verifier repeats under fresh claim numbers into one job of 200
claims (test_section_one_limits_reached); its claim count is observed as that 200.
"""

from datetime import date, timedelta

EPOCH = date(2016, 1, 1)


def _d(text):
    return date.fromisoformat(text)


def _sunday(d):
    return d + timedelta(days=6 - d.weekday())


def observe(rows):
    keys = ("rows", "row_max", "row_min", "row_gap", "claims", "claim_len", "date", "injury_after_first_row", "lines",
            "line_cents", "paid_offset", "periods", "period_span", "first_start", "period_gap", "partial_weeks", "earned",
            "partial_start", "weeks_paid", "aww", "rate", "disability_days", "ttd", "tpd")
    out = {k: [] for k in keys}
    for row in rows:
        job = row.get("job")
        if not job:
            continue
        rates, claims = job["rates"], job["claims"]
        out["rows"].append(len(rates))
        for r in rates:
            out["row_max"].append(r["max"])
            out["row_min"].append(r["min"])
            out["row_gap"].append(r["max"] - r["min"])
            out["date"].append((_d(r["from"]) - EPOCH).days)
        out["claims"].append(200 if len(claims) == 5 and all(c["claim"].startswith("L") for c in claims) else len(claims))
        for c in claims:
            inj = _d(c["injury"])
            out["claim_len"].append(len(c["claim"]))
            out["date"].append((inj - EPOCH).days)
            out["injury_after_first_row"].append((inj - _d(rates[0]["from"])).days)
            out["lines"].append(len(c["wages"]))
            base = {_sunday(inj) - timedelta(days=7 * k) for k in range(1, 14)}
            paid = set()
            for p, cents in c["wages"]:
                out["line_cents"].append(cents)
                out["paid_offset"].append((_d(p) - inj).days)
                out["date"].append((_d(p) - EPOCH).days)
                if cents >= 2000 and _sunday(_d(p)) - timedelta(days=7) in base:
                    paid.add(_sunday(_d(p)) - timedelta(days=7))
            out["weeks_paid"].append(len(paid))
            out["periods"].append(len(c["disability"]))
            prev = None
            for first, last in c["disability"]:
                f, e = _d(first), _d(last)
                out["period_span"].append((e - f).days)
                out["date"] += [(f - EPOCH).days, (e - EPOCH).days]
                if prev is None:
                    out["first_start"].append((f - inj).days)
                else:
                    out["period_gap"].append((f - prev).days)
                prev = e
            out["partial_weeks"].append(len(c["earnings"]))
            for k, (w, e) in enumerate(c["earnings"]):
                out["earned"].append(e)
                out["date"].append((_d(w) - EPOCH).days)
                if k == 0:
                    out["partial_start"].append((_d(w) - timedelta(days=6) - prev).days)
        for s in row.get("statements", {"statements": []})["statements"]:  # differential rows carry no statements
            out["aww"].append(s["aww"])
            out["rate"].append(s["rate"])
            out["disability_days"].append(s["ttd_days"] - s["retro_days"] + s["waiting_days"])
            out["ttd"].append(s["ttd"])
            out["tpd"].append(s["tpd"])
    return out

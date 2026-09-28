"""Adapter for fixture_bounds_check.py: the extremes the sealed jobs reach, per ranges.json key.

limits_job holds one rep (one entry per list, repeated per its `repeat` field) that the verifier repeats under
60 fresh codes (test_section_one_limits_reached); its rep count is observed as that 60.
"""

from datetime import date, timedelta


def _span(q):
    y, n = int(q[:4]), int(q[6:])
    first = date(y, 3 * n - 2, 1)
    after = date(y + 1, 1, 1) if n == 4 else date(y, 3 * n + 1, 1)
    return first, after - timedelta(days=1)


def observe(rows):
    keys = ["reps", "code_len", "year", "qnum", "quota", "draw", "owed_in", "carried_in", "orders_n", "credits_n", "value",
            "order_split", "amount", "credit_split", "age", "offset", "bookings", "bonus", "clawback"]
    out = {k: [] for k in keys}
    for row in rows:
        job = row.get("job")
        if not job:
            continue
        reps = job["reps"]
        if "repeat" in row:  # limits_job: each entry repeated to the list's longest, the rep under 60 codes
            r = dict(reps[0])
            for key, n in row["repeat"].items():
                r[key] = r[key] * n
            reps = [r]
            out["reps"].append(60)
        else:
            out["reps"].append(len(reps))
        for r in reps:
            first, last = _span(r["quarter"])
            off = lambda s: (date.fromisoformat(s) - first).days if date.fromisoformat(s) < first else max(0, (date.fromisoformat(s) - last).days)  # noqa: E731
            out["code_len"].append(len(r["rep"]))
            out["year"].append(int(r["quarter"][:4]))
            out["qnum"].append(int(r["quarter"][6:]))
            for k, o in (("quota", "quota"), ("draw", "draw"), ("owed", "owed_in"), ("carried", "carried_in")):
                out[o].append(r[k])
            out["orders_n"].append(len(r["orders"]))
            out["credits_n"].append(len(r["credits"]))
            for d, v, s, _f in r["orders"]:
                out["value"].append(v)
                out["order_split"].append(s)
                out["offset"].append(off(d))
            for d, b, a, s in r["credits"]:
                out["amount"].append(a)
                out["credit_split"].append(s)
                out["offset"].append(off(d))
                out["age"].append((date.fromisoformat(d) - date.fromisoformat(b)).days)
        for s in row.get("statements", []):
            for k in ("bookings", "bonus", "clawback"):
                out[k].append(s[k])
    return out

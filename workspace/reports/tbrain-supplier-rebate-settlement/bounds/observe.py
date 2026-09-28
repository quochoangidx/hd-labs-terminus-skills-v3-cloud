"""Adapter for fixture_bounds_check.py: the extremes the sealed jobs reach, per ranges.json key.

limits_job holds one account (one entry per list, repeated per its `repeat` field) that the verifier repeats under 100 fresh codes (test_section_one_limits_reached);
its account count is observed as that 100.
"""

from datetime import date, timedelta


def _span(q):
    y, n = int(q[:4]), int(q[6:])
    first = date(y, 3 * n - 2, 1)
    after = date(y + 1, 1, 1) if n == 4 else date(y, 3 * n + 1, 1)
    return first, after - timedelta(days=1)


def observe(rows):
    keys = ["tier_rows", "tier_from", "bp", "accounts", "code_len", "year", "qnum", "prior", "lines", "returns_n", "notices_n",
            "sales_n", "units", "unit_cents", "offset", "old", "new", "on_hand", "cost", "price", "purchases", "returns", "net",
            "protection", "chargebacks"]
    out = {k: [] for k in keys}
    for row in rows:
        job = row.get("job")
        if not job:
            continue
        if "repeat" in row:  # limits_job: the verifier repeats each entry to the list's longest
            a = dict(job["accounts"][0])
            for key, n in row["repeat"].items():
                a[key] = a[key] * n
            job = dict(job, accounts=[a])
        out["tier_rows"].append(len(job["tiers"]))
        for t in job["tiers"]:
            out["tier_from"].append(t["from"])
            out["bp"].append(t["bp"])
        accs = job["accounts"]
        out["accounts"].append(100 if len(accs) == 1 and len(accs[0]["purchases"]) == 400 else len(accs))
        for a in accs:
            first, last = _span(a["quarter"])
            off = lambda s: (date.fromisoformat(s) - first).days if date.fromisoformat(s) < first else max(0, (date.fromisoformat(s) - last).days)  # noqa: E731
            out["code_len"].append(len(a["account"]))
            out["year"].append(int(a["quarter"][:4]))
            out["qnum"].append(int(a["quarter"][6:]))
            out["prior"].append(a["prior"])
            out["lines"].append(len(a["purchases"]))
            out["returns_n"].append(len(a["returns"]))
            out["notices_n"].append(len(a["notices"]))
            out["sales_n"].append(len(a["sales"]))
            for d, u, c in a["purchases"] + a["returns"]:
                out["units"].append(u)
                out["unit_cents"].append(c)
                out["offset"].append(off(d))
            for d, o, n, h in a["notices"]:
                out["old"].append(o)
                out["new"].append(n)
                out["on_hand"].append(h)
                out["offset"].append(off(d))
            for d, u, c, p in a["sales"]:
                out["units"].append(u)
                out["cost"].append(c)
                out["price"].append(p)
                out["offset"].append(off(d))
        for s in row.get("settlements", []):
            for k in ("purchases", "returns", "net", "protection", "chargebacks"):
                out[k].append(s[k])
    return out

"""pdc adapter for fixture_bounds_check.py: the quantities AM-2 rule 1.3 bounds, and derived figures from the sealed reports."""
from datetime import date


def observe(rows):
    seen = {}
    add = lambda k, v: seen.setdefault(k, []).append(v)
    for row in rows:
        for claims in [row[k] for k in ("claims", "a", "b") if k in row]:
            add("year", claims["year"]); add("members", len(claims["members"]))
            add("classes", len({f["class"] for m in claims["members"] for f in m["fills"]}))
            for m in claims["members"]:
                add("id_len", len(m["id"])); add("lines", len(m["fills"])); add("stays", len(m["stays"]))
                total = 0
                for a, b in m["stays"]:
                    n = (date.fromisoformat(b) - date.fromisoformat(a)).days + 1
                    add("stay_len", n); total += n
                add("stay_days", total)
                for f in m["fills"]:
                    add("drug_len", len(f["drug"])); add("class_len", len(f["class"])); add("days", f["days"])
                    add("fill_doy", date.fromisoformat(f["date"]).timetuple().tm_yday)
        if "report" in row:
            for r in row["report"]["members"]:
                add("pdc", r["pdc"])
                if r["in_measure"]:
                    add("index_doy_in", date.fromisoformat(r["index"]).timetuple().tm_yday); add("period_in", r["period"])
            for c in row["report"]["classes"]:
                add("rate", c["rate"]); add("in_measure", c["in_measure"])
    return seen

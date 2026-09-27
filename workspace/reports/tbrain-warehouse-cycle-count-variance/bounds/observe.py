def observe(rows):
    s = {}
    add = lambda k, v: s.setdefault(k, []).append(v)
    for r in rows:
        ls = r["sheet"]["lines"]; add("n", len(ls))
        for x in ls:
            add("skulen", len(x["sku"])); add("system", x["system"]); add("count", x["count"]); add("cost", x["unit_cost"])
            if x["recount"] is not None: add("recount", x["recount"])
    return s

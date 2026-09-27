def observe(rows):
    s = {}
    add = lambda k, v: s.setdefault(k, []).append(v)
    for r in rows:
        ps = r["manifest"]["parcels"]; add("n", len(ps))
        for x in ps:
            add("idlen", len(x["id"])); add("weight", x["weight"]); add("zone", x["zone"])
            for side in x["sides"]:
                add("side", side)
            if min(x["sides"]) >= 2:
                add("boxside", min(x["sides"])); add("boxside", max(x["sides"]))
    return s

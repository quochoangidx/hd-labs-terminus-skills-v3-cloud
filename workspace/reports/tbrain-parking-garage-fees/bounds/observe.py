def observe(rows):
    s = {}
    add = lambda k, v: s.setdefault(k, []).append(v)
    for r in rows:
        items = r["sessions"]["sessions"]; add("n", len(items))
        for x in items:
            add("idlen", len(x["id"])); add("entry", x["entry"]); add("stay", x["exit"] - x["entry"])
    return s

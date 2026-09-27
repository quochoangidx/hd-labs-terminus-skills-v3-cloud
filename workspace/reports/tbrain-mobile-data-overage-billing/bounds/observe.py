def observe(rows):
    s = {}
    add = lambda k, v: s.setdefault(k, []).append(v)
    for r in rows:
        items = r["usage"]["lines"]; add("n", len(items))
        for x in items:
            add("idlen", len(x["id"])); add("count", len(x["sessions"])); add("rate", x["rate"])
            for kb in x["sessions"]:
                add("kb", kb)
    return s

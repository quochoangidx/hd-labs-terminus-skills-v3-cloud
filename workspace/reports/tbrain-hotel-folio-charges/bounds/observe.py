def observe(rows):
    s = {}
    add = lambda k, v: s.setdefault(k, []).append(v)
    for r in rows:
        items = r["stays"]["stays"]; add("n", len(items))
        for x in items:
            add("idlen", len(x["id"])); add("nights", x["nights"]); add("rate", x["rate"])
    return s

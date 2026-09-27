def observe(rows):
    s = {}
    add = lambda k, v: s.setdefault(k, []).append(v)
    for r in rows:
        items = r["loans"]["loans"]; add("n", len(items))
        for x in items:
            add("idlen", len(x["id"])); add("borrowed", x["borrowed"]); add("after", x["returned"] - x["borrowed"])
            add("fine", x["daily_fine"]); add("cost", x["replacement"])
    return s

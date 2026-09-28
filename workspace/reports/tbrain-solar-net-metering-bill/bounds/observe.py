def observe(rows):
    s = {}
    add = lambda k, v: s.setdefault(k, []).append(v)
    for r in rows:
        items = r["reads"]["meters"]; add("n", len(items))
        for x in items:
            add("idlen", len(x["id"])); add("imported", x["imported"]); add("exported", x["exported"])
    return s

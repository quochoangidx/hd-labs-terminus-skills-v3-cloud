def observe(rows):
    s = {}
    add = lambda k, v: s.setdefault(k, []).append(v)
    for r in rows:
        bs = r["release"]["containers"]; add("n", len(bs))
        for x in bs:
            add("idlen", len(x["id"])); add("discharged", x["discharged"]); add("rate", x["rate"])
            add("after", x["picked_up"] - x["discharged"])
    return s

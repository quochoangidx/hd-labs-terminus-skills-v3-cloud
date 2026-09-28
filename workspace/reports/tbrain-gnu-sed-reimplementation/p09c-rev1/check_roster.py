import json, sys
r = json.load(open(sys.argv[1]))
n = 0
for fam, rows in r.items():
    for x in rows:
        n += 1
        c = x["case"]; st = x["gnu"][1]
        if x["ref"] is not None and x["gnu"] != x["ref"]:
            print("REFDIFF", fam, c["opts"], repr(c["script"])[:90], "gnu", repr(x["gnu"])[:80], "ref", repr(x["ref"])[:80])
        if st not in (0, 2) and "q" not in c["script"] and "Q" not in c["script"]:
            print("STATUS", st, fam, c["opts"], repr(c["script"])[:100], c.get("files"))
print("cases", n)

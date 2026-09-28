import json,sys,collections
for d in ["day-1","day-2","day-3","day-4"]:
    day=json.load(open(f"days/{d}.json"))
    st=day["stands"]; tu=day["turns"]
    print(d, "stands",len(st),"turns",len(tu),"transfers",len(day["transfers"]),"wt",len(day["wingtip_pairs"]),"bus",day["bus_cost_per_passenger"],"buf",day["buffer_minutes"])
    print(" stand types",collections.Counter((s["pier"],s["size"],s["international"],s["remote"]) for s in st))
    print(" turn types",collections.Counter((t["size"],t["international"]) for t in tu))
    w=day["walk_metres"]; print(" walk sample",w[0][:5], w[0][0], min(min(r) for r in w), max(max(r) for r in w))
    print(" pax total transfers",sum(x["passengers"] for x in day["transfers"]), "span",min(t["arrive"] for t in tu),max(t["depart"] for t in tu))
    print(" wt",day["wingtip_pairs"][:5])
    print(" keys",list(day.keys()))

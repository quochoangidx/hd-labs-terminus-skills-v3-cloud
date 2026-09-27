import json,sys,collections
for e in ["mon","wed","fri","sat"]:
    ed=json.load(open(f"editions/{e}.json"))
    ads=ed["ads"]
    print(e,{k:ed[k] for k in ed if k not in("ads","name")})
    print(" nads",len(ads),"booked",sum(a["booked"] for a in ads),"total rate",sum(a["rate"] for a in ads),"cells",sum(a["width"]*a["depth"] for a in ads))
    print(" shapes",collections.Counter((a["width"],a["depth"]) for a in ads))
    print(" groups",collections.Counter(a["competitor_group"] for a in ads))
    print(" rh",sum(a["right_hand"] for a in ads), "sec",collections.Counter(a["section"] for a in ads))

import json,collections
for e in ["mon","wed","fri","sat"]:
    ed=json.load(open(f"editions/{e}.json"))
    ads=ed["ads"]
    print(e,{k:ed[k] for k in ed if k!="ads"})
    print(" nads",len(ads),"booked",sum(a["booked"] for a in ads),"totalrate",sum(a["rate"] for a in ads))
    print(" area",sum(a["width"]*a["depth"] for a in ads),"cap",ed["front_page_ad_rows"]*ed["columns"]+(ed["pages"]-1)*(ed["max_ad_share_percent"]*ed["rows"]*ed["columns"]//100))
    print(" shapes",collections.Counter((a["width"],a["depth"]) for a in ads))
    print(" groups",collections.Counter(a["competitor_group"] for a in ads))
    print(" rh",sum(a["right_hand"] for a in ads), "rate/area", sorted(set(round(a["rate"]/(a["width"]*a["depth"]),2) for a in ads))[:5])

import json,sys
E=sys.argv[1]
ed=json.load(open(f"editions/{E}.json")); b=json.load(open(f"work/best_{E}.json"))
ads=ed["ads"]; pg=b["pg"]
om=sum(a["rate"] for a,p in zip(ads,pg) if p==0)
print("cost",b["cost"],"omitted",om, "omitted area",sum(a["width"]*a["depth"] for a,p in zip(ads,pg) if p==0))
for p in range(1,ed["pages"]+1):
    m=[a for a,q in zip(ads,pg) if q==p]
    print(p,sum(a["width"]*a["depth"] for a in m),[(a["width"],a["depth"],a["section"],a["right_hand"]) for a in m])
print("omitted",sorted([(round(a["rate"]/a["width"]/a["depth"],2),a["width"],a["depth"],a["rate"]) for a,p in zip(ads,pg) if p==0]))
print("placed low",sorted([(round(a["rate"]/a["width"]/a["depth"],2),a["width"],a["depth"],a["rate"]) for a,p in zip(ads,pg) if p!=0])[:15])
pen=b["cost"]-om
print("penalty",pen,"waste",sum((36 if p==1 else ed["max_ad_share_percent"]*ed["rows"]*ed["columns"]//100)-sum(a["width"]*a["depth"] for a,q in zip(ads,pg) if q==p) for p in range(1,ed["pages"]+1)))

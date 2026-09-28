import json,sys
E=sys.argv[1]
ed=json.load(open(f"editions/{E}.json")); lay=json.load(open(f"layouts/{E}.json"))["placements"]
ads={a["id"]:a for a in ed["ads"]}
C,R=ed["columns"],ed["rows"]
for p in range(1,ed["pages"]+1):
    l=[k for k,v in lay.items() if v["page"]==p]
    print(p,sum(ads[k]["width"]*ads[k]["depth"] for k in l),[(ads[k]["width"],ads[k]["depth"],ads[k]["section"],ads[k]["right_hand"],ads[k]["rate"]) for k in l])
print("dropped",sorted([(a["rate"],a["width"],a["depth"],a["section"],a["right_hand"],a["competitor_group"]) for a in ed["ads"] if a["id"] not in lay]))
print(sorted(set(a["rate"]/(a["width"]*a["depth"]) for a in ed["ads"])))

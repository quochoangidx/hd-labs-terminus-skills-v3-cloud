import json, collections, sys
g=json.load(open('gnu.json')); r=json.load(open('ref.json'))
valid=[i for i,a in enumerate(g) if "syntax error" not in a["stderr"] and "illegal character" not in a["stderr"] and a["stdout"]!="<timeout>" and len(a["stdout"])<20000]
bad=[i for i in valid if g[i]["stdout"]!=r[i]["stdout"]]
print("valid",len(valid),"/",len(g),"ref mismatch",len(bad), bad[:5])
drop=set()
for v in "boolclean limits raisenegzero stmtprint".split():
    x=json.load(open(f'var_{v}.json'))
    d=[i for i in valid if x[i]["stdout"]!=g[i]["stdout"]]
    drop|=set(d)
    print(v, len(d), collections.Counter(g[i]["family"] for i in d).most_common(5))
keep=[i for i in valid if i not in drop and i not in bad]
print("keep",len(keep)); print(sorted(collections.Counter(g[i]["family"] for i in keep).items()))
json.dump(keep,open("keep_idx.json","w"))

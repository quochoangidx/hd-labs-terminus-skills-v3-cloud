import json, random, sys, math, time, os
sys.setrecursionlimit(10000)
E = sys.argv[1]; SEED = int(sys.argv[2]); TLIM = float(sys.argv[3])
ed = json.load(open(f"editions/{E}.json"))
COLS, ROWS, P = ed["columns"], ed["rows"], ed["pages"]
ads = ed["ads"]; N = len(ads)
CAPN = ed["max_ad_share_percent"]*ROWS*COLS//100
CAP1 = ed["front_page_ad_rows"]*COLS
FR = ed["front_page_ad_rows"]
W=[a["width"] for a in ads]; D=[a["depth"] for a in ads]; AR=[W[i]*D[i] for i in range(N)]
R=[a["rate"] for a in ads]; BK=[a["booked"] for a in ads]; G=[a["competitor_group"] for a in ads]
def spread(p): return 0 if p==1 else p//2
cost_tab=[[0]*(P+1) for _ in range(N)]
for i,a in enumerate(ads):
    cost_tab[i][0]=R[i] if not BK[i] else 10**9
    for p in range(1,P+1):
        c=0
        if a["section"] is not None:
            f,l=ed["sections"][a["section"]]
            if not f<=p<=l: c+=R[i]*ed["wrong_section_percent"]//100
        if a["right_hand"] and p%2==0: c+=R[i]*ed["left_hand_percent"]//100
        if p==1 and D[i]>FR: c=None
        cost_tab[i][p]=c
# packer
memo={}
def pack(shapes, rows):
    # shapes: sorted tuple of (w,d); returns list of (w,d,col,h) or None
    key=(shapes,rows)
    if key in memo: return memo[key]
    res=None
    if sum(w*d for w,d in shapes) <= rows*COLS:
        res=dfs([0]*COLS, list(shapes), rows, {})
    memo[key]=res
    return res
def dfs(sky, rem, rows, seen):
    if not rem: return []
    k=(tuple(sky),tuple(rem))
    if k in seen: return None
    # choose the ad to place: try all distinct shapes, all flat positions
    tried=set()
    for idx,(w,d) in enumerate(rem):
        if (w,d) in tried: continue
        tried.add((w,d))
        for c in range(COLS-w+1):
            h=sky[c]
            if h+d>rows: continue
            ok=True
            for x in range(c+1,c+w):
                if sky[x]!=h: ok=False;break
            if not ok: continue
            ns=sky[:]
            for x in range(c,c+w): ns[x]=h+d
            nr=rem[:idx]+rem[idx+1:]
            r=dfs(ns,nr,rows,seen)
            if r is not None:
                return [(w,d,c,h)]+r
    seen[k]=1
    return None
def page_ok(p, members):
    shapes=tuple(sorted((W[i],D[i]) for i in members))
    return pack(shapes, FR if p==1 else ROWS) is not None
def cap(p): return CAP1 if p==1 else CAPN

# initial: planner
sys.path.insert(0,"planner")
import plan_edition
init=plan_edition.plan(ed)["placements"]
idx={a["id"]:i for i,a in enumerate(ads)}
pg=[0]*N
for aid,v in init.items(): pg[idx[aid]]=v["page"]
best_file=f"work/best_{E}.json"
if os.path.exists(best_file) and os.environ.get("RESUME"):
    b=json.load(open(best_file)); pg=b["pg"]
members={p:set() for p in range(0,P+1)}
for i in range(N): members[pg[i]].add(i)
area=[0]*(P+1)
for i in range(N):
    if pg[i]: area[pg[i]]+=AR[i]
gcount={}
for i in range(N):
    if pg[i] and G[i]: gcount[(G[i],spread(pg[i]))]=gcount.get((G[i],spread(pg[i])),0)+1
def total():
    return sum(cost_tab[i][pg[i]] for i in range(N))
cur=total(); best=cur; bestpg=pg[:]
print("init",cur,flush=True)
rng=random.Random(SEED)
T0=float(sys.argv[4]) if len(sys.argv)>4 else 30.0
t0=time.time(); it=0
def gfree(i,p,excl=()):
    if not G[i] or p==0: return True
    c=gcount.get((G[i],spread(p)),0)
    for j in excl:
        if G[j]==G[i] and pg[j] and spread(pg[j])==spread(p): c-=1
    return c==0
def setpg(i,p):
    o=pg[i]
    if o:
        members[o].discard(i); area[o]-=AR[i]
        if G[i]: gcount[(G[i],spread(o))]-=1
    else: members[0].discard(i)
    pg[i]=p; members[p].add(i)
    if p:
        area[p]+=AR[i]
        if G[i]: gcount[(G[i],spread(p))]=gcount.get((G[i],spread(p)),0)+1

def gok(i):
    p=pg[i]
    return (not p) or (not G[i]) or gcount[(G[i],spread(p))]==1
def propose():
    m=rng.random()
    i=rng.randrange(N)
    if m<0.3:
        p=rng.randint(0 if not BK[i] else 1,P)
        return [(i,p)]
    if m<0.6:
        j=rng.randrange(N)
        return [(i,pg[j]),(j,pg[i])]
    if m<0.75:
        p=rng.randint(1,P)
        if cost_tab[i][p] is None or pg[i]==p: return []
        ch=[(i,p)]; a=area[p]+AR[i]; c=cap(p)
        mem=list(members[p]); rng.shuffle(mem)
        while a>c and mem:
            k=mem.pop(); a-=AR[k]
            ch.append((k,0 if not BK[k] and rng.random()<0.7 else rng.randint(1,P)))
        if len(ch)>1 and rng.random()<0.3 and mem:
            k=mem.pop(); ch.append((k,0 if not BK[k] and rng.random()<0.7 else rng.randint(1,P)))
        return ch
    # insert i into page p, eject k from p to q
    p=rng.randint(1,P)
    if not members[p]: return [(i,p)]
    k=rng.choice(list(members[p]))
    if rng.random()<0.5 and not BK[k]: q=0
    else: q=rng.randint(1,P)
    ch=[(i,p),(k,q)]
    if rng.random()<0.3 and len(members[p])>1:
        k2=rng.choice(list(members[p]))
        if k2!=k and k2!=i:
            ch.append((k2,0 if not BK[k2] and rng.random()<0.5 else rng.randint(1,P)))
    return ch
frac=0
while True:
    it+=1
    if it%500==0:
        frac=(time.time()-t0)/TLIM
        if frac>1: break
    T=T0*(1-frac)**2+0.3
    ch=propose()
    seen=set(); bad=False
    for (a,p) in ch:
        if a in seen or cost_tab[a][p] is None or (p==0 and BK[a]): bad=True;break
        seen.add(a)
    if bad or not ch: continue
    old=[(a,pg[a]) for a,_ in ch]
    d=sum(cost_tab[a][p]-cost_tab[a][pg[a]] for a,p in ch)
    if d>0 and rng.random()>=math.exp(-d/T): continue
    for a,p in ch: setpg(a,p)
    aff={p for _,p in ch if p}
    ok=all(area[p]<=cap(p) for p in aff) and all(gok(a) for a,_ in ch)
    if ok:
        for p in aff:
            if not page_ok(p,members[p]): ok=False;break
    if ok: cur+=d
    else:
        for a,p in old: setpg(a,p)
    if cur<best:
        best=cur; bestpg=pg[:]
        print(f"{time.time()-t0:.0f}s best {best}",flush=True)
print("final best",best, "memo",len(memo),"it",it)
# write
pl={}
for p in range(1,P+1):
    mem=[i for i in range(N) if bestpg[i]==p]
    rows=FR if p==1 else ROWS
    sol=pack(tuple(sorted((W[i],D[i]) for i in mem)),rows)
    pool={}
    for i in mem: pool.setdefault((W[i],D[i]),[]).append(i)
    for (w,d,c,h) in sol:
        i=pool[(w,d)].pop()
        pl[ads[i]["id"]]={"page":p,"column":c,"row":ROWS-h-d}
old=None
if os.path.exists(best_file): old=json.load(open(best_file))["cost"]
if old is None or best<old:
    json.dump({"cost":best,"pg":bestpg},open(best_file,"w"))
    json.dump({"placements":pl},open(f"layouts/{E}.json","w"),indent=1)
    print("wrote",best)

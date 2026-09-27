s=open("work/sa.py").read()
start=s.index("while True:")
end=s.index('print("final best"')
new='''
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
    if bad: continue
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
'''
s=s[:start]+new+s[end:]
open("work/sa.py","w").write(s)

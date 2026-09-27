s=open("work/sa.py").read()
old='''    # insert i into page p, eject k from p to q
'''
new='''    if m<0.75:
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
'''
assert old in s
s=s.replace(old,new)
s=s.replace("    if bad: continue\n","    if bad or not ch: continue\n")
open("work/sa.py","w").write(s)

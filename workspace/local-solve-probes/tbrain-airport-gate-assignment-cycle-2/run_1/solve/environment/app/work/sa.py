import json, sys, random, math, time, os
sys.path.insert(0, '/app/tools')
import check_plan

PW = float(os.environ.get("PW", "0.2"))
WIN = int(os.environ.get("WIN", "240"))
MAXD = int(os.environ.get("MAXD", "2"))
def run(dname, secs, seed, T0, T1, init=None):
    rnd = random.Random(seed)
    day = json.load(open(f'/app/days/{dname}.json'))
    S = day['stands']; T = day['turns']
    ns, nt = len(S), len(T)
    sidx = {s['id']: i for i, s in enumerate(S)}
    tidx = {t['id']: i for i, t in enumerate(T)}
    W = day['walk_metres']; buf = day['buffer_minutes']; bus = day['bus_cost_per_passenger']
    A = [t['arrive'] for t in T]; D = [t['depart'] for t in T]; SZ = [t['size'] for t in T]
    busc = [bus * (t['pax_in'] + t['pax_out']) for t in T]
    remote = [s['remote'] for s in S]
    elig = [[j for j, s in enumerate(S) if t['size'] <= s['size'] and (not t['international'] or s['international'])] for t in T]
    nb = [[] for _ in range(ns)]
    for a, b in day['wingtip_pairs']:
        nb[sidx[a]].append(sidx[b]); nb[sidx[b]].append(sidx[a])
    adj = [[] for _ in range(nt)]  # (other, pax, out?) out means t is from
    trs = []
    for k, tr in enumerate(day['transfers']):
        a, b, p = tidx[tr['from']], tidx[tr['to']], tr['passengers']
        trs.append((a, b, p))
        adj[a].append((k, b, p, True)); adj[b].append((k, a, p, False))
    st = [0] * nt
    occ = [set() for _ in range(ns)]
    plan = json.load(open(init))
    for sid, lst in plan['stands'].items():
        for tid in lst:
            st[tidx[tid]] = sidx[sid]; occ[sidx[sid]].add(tidx[tid])

    def conflicts(t, s):
        c = []
        a, d = A[t], D[t]
        for o in occ[s]:
            if o != t and not (D[o] + buf <= a or d + buf <= A[o]):
                c.append(o)
        if SZ[t] == 3:
            for n in nb[s]:
                for o in occ[n]:
                    if o != t and SZ[o] == 3 and A[o] < d and a < D[o]:
                        c.append(o)
        return c

    def total():
        c = sum(busc[t] for t in range(nt) if remote[st[t]])
        for a, b, p in trs:
            c += p * W[st[a]][st[b]]
        return c

    def local(M):
        c = 0
        seen = set()
        for t in M:
            if remote[st[t]]: c += busc[t]
            s = st[t]
            for k, o, p, out in adj[t]:
                if k in seen: continue
                seen.add(k)
                c += p * (W[s][st[o]] if out else W[st[o]][s])
        return c

    def tcost(t, s):
        c = busc[t] if remote[s] else 0
        for k, o, p, out in adj[t]:
            c += p * (W[s][st[o]] if out else W[st[o]][s])
        return c

    eset = [set(e) for e in elig]
    cur = total(); best = cur; bestst = st[:]
    t0 = time.time(); it = 0
    lastsave = t0
    while True:
        it += 1
        if it & 255 == 0:
            el = time.time() - t0
            if el > secs: break
            frac = el / secs
            temp = T0 * (T1 / T0) ** frac
        elif it < 256:
            temp = T0
        t = rnd.randrange(nt)
        s = rnd.choice(elig[t])
        s0 = st[t]
        if s == s0: continue
        if rnd.random() < PW:
            s1, s2 = s0, s
            if rnd.random() < 0.1:
                lo, hi = -10**9, 10**9
            else:
                lo = A[t] - rnd.randint(0, WIN); hi = D[t] + rnd.randint(0, WIN)
            X1 = [x for x in occ[s1] if lo <= A[x] <= hi]
            X2 = [x for x in occ[s2] if lo <= A[x] <= hi]
            if any(s2 not in eset[x] for x in X1) or any(s1 not in eset[x] for x in X2):
                continue
            for x in X1: occ[s1].discard(x)
            for x in X2: occ[s2].discard(x)
            ok = True
            done = []
            for x, ns_ in [(x, s2) for x in X1] + [(x, s1) for x in X2]:
                if conflicts(x, ns_):
                    ok = False; break
                occ[ns_].add(x); st[x] = ns_; done.append(x)
            if ok:
                M = X1 + X2
                after = local(M)
                for x in X1: st[x] = s1
                for x in X2: st[x] = s2
                before = local(M)
                for x in X1: st[x] = s2
                for x in X2: st[x] = s1
                delta = after - before
                if delta <= 0 or rnd.random() < math.exp(-delta / temp):
                    cur += delta
                    if cur < best:
                        best = cur; bestst = st[:]
                    continue
            for x in done: occ[st[x]].discard(x)
            for x in X1: st[x] = s1; occ[s1].add(x)
            for x in X2: st[x] = s2; occ[s2].add(x)
            continue
        C = conflicts(t, s)
        if len(C) > 2: continue
        M = [t] + C
        old = [(x, st[x]) for x in M]
        # apply
        occ[s0].discard(t); occ[s].add(t); st[t] = s
        for c in C:
            occ[st[c]].discard(c)
        ok = True
        placed = []
        queue = list(C)
        depth = 0
        while queue:
            c = queue.pop()
            opts = []
            for s2 in elig[c]:
                if not conflicts(c, s2):
                    opts.append(s2)
            if not opts:
                if depth >= MAXD:
                    ok = False; break
                depth += 1
                s2 = rnd.choice(elig[c])
                C2 = conflicts(c, s2)
                if len(C2) != 1 or C2[0] in M:
                    ok = False; break
                c2 = C2[0]
                old.append((c2, st[c2])); M.append(c2)
                occ[st[c2]].discard(c2)
                queue.append(c2)
            elif rnd.random() < 0.7:
                s2 = min(opts, key=lambda x: tcost(c, x) + rnd.random())
            else:
                s2 = rnd.choice(opts)
            st[c] = s2; occ[s2].add(c); placed.append(c)
        if ok:
            after = local(M)
            newpos = [st[x] for x in M]
            for x, sx in old: st[x] = sx
            before = local(M)
            for x, sx in zip(M, newpos): st[x] = sx
            delta = after - before
            if delta <= 0 or rnd.random() < math.exp(-delta / temp):
                cur += delta
                if cur < best:
                    best = cur; bestst = st[:]
                continue
        # revert
        for c in placed:
            occ[st[c]].discard(c)
        occ[s].discard(t)
        for x, sx in old:
            st[x] = sx; occ[sx].add(x)
    print("final cur", cur, flush=True)
    st[:] = bestst
    assert total() == best
    out = {'stands': {S[j]['id']: [] for j in range(ns)}}
    for t in range(nt):
        out['stands'][S[st[t]]['id']].append(T[t]['id'])
    return best, out, it

if __name__ == '__main__':
    dname, secs, seed, T0, T1 = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
    init = sys.argv[6] if len(sys.argv) > 6 else f'/app/plans/{dname}.json'
    best, out, it = run(dname, secs, seed, T0, T1, init)
    day = json.load(open(f'/app/days/{dname}.json'))
    c = check_plan.evaluate(day, out)
    print(dname, 'best', best, 'check', c, 'iters', it, flush=True)
    fn = f'/app/work/{dname}.s{seed}.json'
    json.dump(out, open(fn, 'w'))
    import fcntl
    lk = open('/app/work/lock', 'w'); fcntl.flock(lk, fcntl.LOCK_EX)
    cp = check_plan.evaluate(day, check_plan.load_plan(f'/app/plans/{dname}.json'))
    if c < cp:
        tmp = f'/app/plans/.{dname}.{seed}.tmp'
        json.dump(out, open(tmp, 'w'))
        os.replace(tmp, f'/app/plans/{dname}.json')
        print('saved', dname, c, 'was', cp, flush=True)

import json, sys, random, math, time, os, fcntl
sys.path.insert(0, '/app/tools'); sys.path.insert(0, '/app/planner')
import check_plan, plan_day

def save_if_better(dname, day, assign_ids):
    plan = {"stands": assign_ids}
    cost = check_plan.evaluate(day, plan)
    path = f'/app/plans/{dname}.json'
    with open('/app/work/lock', 'w') as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        cur = None
        try:
            cur = check_plan.evaluate(day, check_plan.load_plan(path))
        except Exception:
            cur = None
        if cur is None or cost < cur:
            tmp = path + '.tmp'
            with open(tmp, 'w') as fh: json.dump(plan, fh)
            os.replace(tmp, path)
            return cost, True
    return cur, False

def run(dname, seconds, seed, T0=30000.0, T1=30.0):
    rng = random.Random(seed)
    day = json.load(open(f'/app/days/{dname}.json'))
    S = day['stands']; TT = day['turns']; nS = len(S); nT = len(TT)
    sidx = {s['id']: i for i, s in enumerate(S)}; tidx = {t['id']: i for i, t in enumerate(TT)}
    W = day['walk_metres']; buf = day['buffer_minutes']; bus = day['bus_cost_per_passenger']
    arr = [t['arrive'] for t in TT]; dep = [t['depart'] for t in TT]; sz = [t['size'] for t in TT]
    buscost = [bus * (t['pax_in'] + t['pax_out']) for t in TT]
    remote = [s['remote'] for s in S]
    compat = [[j for j, s in enumerate(S) if t['size'] <= s['size'] and (not t['international'] or s['international'])] for t in TT]
    conf = [set() for _ in range(nT)]
    wconf = [set() for _ in range(nT)]
    for i in range(nT):
        for j in range(i + 1, nT):
            if not (dep[i] + buf <= arr[j] or dep[j] + buf <= arr[i]):
                conf[i].add(j); conf[j].add(i)
            if sz[i] == 3 and sz[j] == 3 and arr[i] < dep[j] and arr[j] < dep[i]:
                wconf[i].add(j); wconf[j].add(i)
    wn = [[] for _ in range(nS)]
    for a, b in day['wingtip_pairs']:
        wn[sidx[a]].append(sidx[b]); wn[sidx[b]].append(sidx[a])
    adjd = [dict() for _ in range(nT)]
    for tr in day['transfers']:
        a = tidx[tr['from']]; b = tidx[tr['to']]; p = tr['passengers']
        adjd[a][b] = adjd[a].get(b, 0) + p
        if a != b: adjd[b][a] = adjd[b].get(a, 0) + p
    adj = [list(d.items()) for d in adjd]
    # init from existing plan file or planner
    try:
        plan = check_plan.load_plan(f'/app/plans/{dname}.json'); check_plan.evaluate(day, plan)
    except Exception:
        plan = plan_day.plan(day)
    A = [0] * nT
    on = [set() for _ in range(nS)]
    for sid, lst in plan['stands'].items():
        for tid in lst:
            A[tidx[tid]] = sidx[sid]; on[sidx[sid]].add(tidx[tid])

    def local(M, Mset):
        c = 0
        for t in M:
            st = A[t]
            if remote[st]: c += buscost[t]
            Wt = W[st]
            for u, p in adj[t]:
                if u in Mset and u < t: continue
                c += p * Wt[A[u]]
        return c

    def wing_ok(t):
        if sz[t] != 3: return True
        wc = wconf[t]
        for nb in wn[A[t]]:
            for u in on[nb]:
                if u in wc: return False
        return True

    def total():
        return local(range(nT), set(range(nT)))
    cur = total(); best = cur; bestA = A[:]
    t0 = time.time(); last_save = t0; it = 0
    T = T0
    while True:
        it += 1
        if it & 1023 == 0:
            el = time.time() - t0
            if el > seconds: break
            frac = el / seconds
            T = T0 * (T1 / T0) ** frac
            if time.time() - last_save > 60 and best < cur_saved if 'cur_saved' in dir() else False:
                pass
        t = rng.randrange(nT)
        r = A[t]
        cs = compat[t]
        s = cs[rng.randrange(len(cs))]
        if s == r: continue
        C = [u for u in on[s] if u in conf[t]]
        ok = True
        if C:
            if len(C) > 3: continue
            for u in C:
                if r not in compat[u]: ok = False; break
                cu = conf[u]
                for v in on[r]:
                    if v != t and v in cu: ok = False; break
                if not ok: break
            if not ok: continue
        M = [t] + C; Mset = set(M)
        before = local(M, Mset)
        # apply
        on[r].discard(t); on[s].add(t); A[t] = s
        for u in C:
            on[s].discard(u); on[r].add(u); A[u] = r
        good = wing_ok(t) and all(wing_ok(u) for u in C)
        if good:
            after = local(M, Mset)
            d = after - before
            if d <= 0 or rng.random() < math.exp(-d / T):
                cur += d
                if cur < best:
                    best = cur; bestA = A[:]
                continue
        # revert
        for u in C:
            on[r].discard(u); on[s].add(u); A[u] = s
        on[s].discard(t); on[r].add(t); A[t] = r
    out = {S[j]['id']: [] for j in range(nS)}
    for i in range(nT): out[S[bestA[i]]['id']].append(TT[i]['id'])
    fc, wrote = save_if_better(dname, day, out)
    print(dname, 'seed', seed, 'best', best, 'iters', it, 'file', fc, 'wrote', wrote, flush=True)
    return best

if __name__ == '__main__':
    from multiprocessing import Pool
    secs = float(sys.argv[1]); jobs = []
    for spec in sys.argv[2:]:
        d, seed = spec.split(':'); jobs.append((d, secs, int(seed)))
    with Pool(2) as p:
        p.starmap(run, jobs)

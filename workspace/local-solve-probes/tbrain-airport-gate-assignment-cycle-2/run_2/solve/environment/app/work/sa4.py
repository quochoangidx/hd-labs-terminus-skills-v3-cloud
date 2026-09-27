import json, sys, random, math, time, os
sys.path.insert(0, 'tools')
from check_plan import evaluate

dname = sys.argv[1]; tlimit = float(sys.argv[2]); seed = int(sys.argv[3])
T0 = float(sys.argv[4]); T1 = float(sys.argv[5]); NC = int(sys.argv[6])
random.seed(seed)
day = json.load(open(f'days/{dname}.json'))
S0 = day['stands']; T = day['turns']
tid = [t['id'] for t in T]; tidx = {t['id']: i for i, t in enumerate(T)}
W0 = day['walk_metres']; buf = day['buffer_minutes']; bus = day['bus_cost_per_passenger']
rem0 = [i for i, s in enumerate(S0) if s['remote']]
con0 = [i for i, s in enumerate(S0) if not s['remote']]
R = len(rem0)
# sanity: remote stands identical
wset = set()
for a, b in day['wingtip_pairs']: wset |= {a, b}
assert all(S0[i]['id'] not in wset for i in rem0)
assert all(S0[i]['size'] == 3 and S0[i]['international'] for i in rem0)
for i in rem0:
    for j in range(len(S0)):
        assert W0[i][j] == W0[rem0[0]][j] and W0[j][i] == W0[j][rem0[0]]
        if j in rem0: assert W0[i][j] == W0[rem0[0]][rem0[0]]
# new stand indices: contact stands 0..NC0-1, pool = P
old2new = {}
for k, i in enumerate(con0): old2new[i] = k
P = len(con0)
for i in rem0: old2new[i] = P
NS = P + 1
orig = con0 + [rem0[0]]
W = [[W0[orig[i]][orig[j]] for j in range(NS)] for i in range(NS)]
S = [S0[i] for i in orig]
sid = [s['id'] for s in S]; sidx = {s['id']: i for i, s in enumerate(S)}
NT = len(T)
arr = [t['arrive'] for t in T]; dep = [t['depart'] for t in T]
big = [t['size'] == 3 for t in T]
remote = [False] * P + [True]
buscost = [bus * (t['pax_in'] + t['pax_out']) for t in T]
compat = [[j for j, s in enumerate(S) if t['size'] <= s['size'] and (not t['international'] or s['international'])] for t in T]
compatset = [set(c) for c in compat]
wn = [[] for _ in range(NS)]
for a, b in day['wingtip_pairs']:
    wn[sidx[a]].append(sidx[b]); wn[sidx[b]].append(sidx[a])
adj = [[] for _ in range(NT)]
edges = []
for tr in day['transfers']:
    a = tidx[tr['from']]; b = tidx[tr['to']]; p = tr['passengers']
    edges.append((a, b, p))
    adj[a].append((b, p, True)); adj[b].append((a, p, False))

fn = f'plans/{dname}.json'
init = json.load(open(fn))
where = [None] * NT
sidx0 = {s['id']: i for i, s in enumerate(S0)}
for s, lst in init['stands'].items():
    for t in lst: where[tidx[t]] = old2new[sidx0[s]]
occ = [set() for _ in range(NS)]
for t in range(NT): occ[where[t]].add(t)

def fullcost():
    c = sum(buscost[t] for t in range(NT) if remote[where[t]])
    for a, b, p in edges: c += p * W[where[a]][where[b]]
    return c

def pool_fits(t):
    a = arr[t]; d = dep[t] + buf
    ev = []
    for o in occ[P]:
        oa = arr[o]; od = dep[o] + buf
        if oa < d and a < od:
            ev.append((max(oa, a), 1)); ev.append((od, -1))
    if len(ev) < 2 * R: return True
    ev.sort()
    c = 0
    for _, k in ev:
        c += k
        if c >= R: return False
    return True

def fits(t, s):
    if s == P: return pool_fits(t)
    a = arr[t]; d = dep[t]
    for o in occ[s]:
        if not (dep[o] + buf <= a or d + buf <= arr[o]): return False
    if big[t]:
        for n in wn[s]:
            for o in occ[n]:
                if big[o] and arr[o] < d and a < dep[o]: return False
    return True

def turncost(t, s, moved):
    c = buscost[t] if remote[s] else 0
    for o, p, out in adj[t]:
        so = moved.get(o, where[o])
        if o in moved and o < t: continue
        c += p * (W[s][so] if out else W[so][s])
    return c

def delta(moves):
    old = 0; new = 0
    oldm = {t: where[t] for t in moves}
    for t, s in moves.items():
        old += turncost(t, where[t], oldm)
        new += turncost(t, s, moves)
    return new - old

def apply(moves):
    for t in moves: occ[where[t]].discard(t)
    done = []
    ok = True
    for t, s in moves.items():
        if s not in compatset[t] or not fits(t, s):
            ok = False; break
        occ[s].add(t); done.append(t)
    if not ok:
        for t in done: occ[moves[t]].discard(t)
        for t in moves: occ[where[t]].add(t)
        return False
    for t, s in moves.items(): where[t] = s
    return True

def conflicts(t, s, exclude):
    a = arr[t]; d = dep[t]
    return [o for o in occ[s] if o not in exclude and not (dep[o] + buf <= a or d + buf <= arr[o])]

def kempe(t, s2):
    s1 = where[t]
    X = {t}; Y = set(); fx = [t]
    while True:
        ny = set()
        for x in fx:
            for o in conflicts(x, s2, Y): ny.add(o)
        ny -= Y
        if not ny: break
        Y |= ny
        nx = set()
        for y in ny:
            for o in conflicts(y, s1, X): nx.add(o)
        nx -= X
        X |= nx
        fx = list(nx)
        if len(X) + len(Y) > 12: return None
    m = {x: s2 for x in X}
    for y in Y: m[y] = s1
    return m

def to_plan(wh):
    plan = {'stands': {s['id']: [] for s in S0}}
    for t in range(NT):
        if wh[t] != P: plan['stands'][sid[wh[t]]].append(tid[t])
    pool = sorted((arr[t], t) for t in range(NT) if wh[t] == P)
    free_at = {S0[i]['id']: -10**9 for i in rem0}
    for a, t in pool:
        for r in free_at:
            if free_at[r] <= a:
                plan['stands'][r].append(tid[t]); free_at[r] = dep[t] + buf; break
        else:
            raise RuntimeError('pool coloring failed')
    return plan

cur = fullcost(); best = cur; bestwhere = where[:]
print(dname, 'start', cur, flush=True)
start = time.time(); lastw = start; it = 0
def write_best():
    plan = to_plan(bestwhere)
    c = evaluate(day, plan)
    assert c == best, (c, best)
    try: oc = evaluate(day, json.load(open(fn)))
    except Exception: oc = None
    if oc is None or c < oc:
        tmp = fn + f'.{seed}.tmp'
        json.dump(plan, open(tmp, 'w')); os.replace(tmp, fn)
    return c
Tcur = T0
while True:
    it += 1
    if it & 1023 == 0:
        el = time.time() - start
        if el > tlimit: break
        phase = (el / tlimit * NC) % 1.0
        Tcur = T0 * (T1 / T0) ** phase
        if time.time() - lastw > 30:
            write_best(); lastw = time.time()
            print(dname, int(el), 'cur', cur, 'best', best, 'T', int(Tcur), flush=True)
    t = random.randrange(NT)
    r = random.random()
    s2 = random.choice(compat[t])
    if s2 == where[t]: continue
    if r < 0.03:
        if s2 == P or where[t] == P: continue
        s1 = where[t]
        m = {x: s2 for x in occ[s1]}
        for y in occ[s2]: m[y] = s1
    elif r < 0.4:
        m = {t: s2}
    elif r < 0.7:
        if not occ[s2]: m = {t: s2}
        else:
            u = random.choice(list(occ[s2]))
            if where[t] not in compatset[u]: continue
            m = {t: s2, u: where[t]}
    else:
        if s2 == P or where[t] == P:
            # pool kempe: t <-> overlapping ones
            m = kempe(t, s2)
            if m is None: continue
        else:
            m = kempe(t, s2)
            if m is None: continue
    d = delta(m)
    if d <= 0 or random.random() < math.exp(-d / Tcur):
        if apply(m):
            cur += d
            if cur < best:
                best = cur; bestwhere = where[:]
write_best()
assert fullcost() == cur
print(dname, 'final best', best, 'iters', it, flush=True)

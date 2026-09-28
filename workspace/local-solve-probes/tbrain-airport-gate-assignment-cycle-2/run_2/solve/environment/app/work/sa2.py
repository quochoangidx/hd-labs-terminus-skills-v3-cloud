import json, sys, random, math, time, os
sys.path.insert(0, 'tools')
from check_plan import evaluate

dname = sys.argv[1]; tlimit = float(sys.argv[2]); seed = int(sys.argv[3])
T0 = float(sys.argv[4]); T1 = float(sys.argv[5]); ncyc = int(sys.argv[6])
random.seed(seed)
day = json.load(open(f'days/{dname}.json'))
S = day['stands']; T = day['turns']
NS = len(S); NT = len(T)
sid = [s['id'] for s in S]; sidx = {s['id']: i for i, s in enumerate(S)}
tid = [t['id'] for t in T]; tidx = {t['id']: i for i, t in enumerate(T)}
W = day['walk_metres']; buf = day['buffer_minutes']; bus = day['bus_cost_per_passenger']
arr = [t['arrive'] for t in T]; dep = [t['depart'] for t in T]
big = [t['size'] == 3 for t in T]
remote = [s['remote'] for s in S]
buscost = [bus * (t['pax_in'] + t['pax_out']) for t in T]
compat = [[j for j, s in enumerate(S) if t['size'] <= s['size'] and (not t['international'] or s['international'])] for t in T]
compatset = [set(c) for c in compat]
compat_contact = [[j for j in c if not remote[j]] for c in compat]
remotes = [j for j in range(NS) if remote[j]]
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
for s, lst in init['stands'].items():
    for t in lst: where[tidx[t]] = sidx[s]
occ = [set() for _ in range(NS)]
for t in range(NT): occ[where[t]].add(t)

def fullcost():
    c = sum(buscost[t] for t in range(NT) if remote[where[t]])
    for a, b, p in edges: c += p * W[where[a]][where[b]]
    return c

def lcost(M):
    c = 0
    for t in M:
        s = where[t]
        if remote[s]: c += buscost[t]
        for o, p, out in adj[t]:
            if o in M and o < t: continue
            so = where[o]
            c += p * (W[s][so] if out else W[so][s])
    return c

def tcost(t, s):
    c = buscost[t] if remote[s] else 0
    for o, p, out in adj[t]:
        so = where[o]
        c += p * (W[s][so] if out else W[so][s])
    return c

def conflicts(t, s):
    a = arr[t]; d = dep[t]
    res = [o for o in occ[s] if not (dep[o] + buf <= a or d + buf <= arr[o])]
    if big[t]:
        for n in wn[s]:
            for o in occ[n]:
                if big[o] and arr[o] < d and a < dep[o]: res.append(o)
    return res

def fits(t, s):
    a = arr[t]; d = dep[t]
    for o in occ[s]:
        if not (dep[o] + buf <= a or d + buf <= arr[o]): return False
    if big[t]:
        for n in wn[s]:
            for o in occ[n]:
                if big[o] and arr[o] < d and a < dep[o]: return False
    return True

def unplace(t):
    occ[where[t]].discard(t)
def place(t, s):
    where[t] = s; occ[s].add(t)

def try_moves(m):
    """m: dict t->s. returns old dict if applied else None"""
    old = {t: where[t] for t in m}
    for t in m: unplace(t)
    done = []
    for t, s in m.items():
        if s not in compatset[t] or not fits(t, s):
            for u in done: occ[m[u]].discard(u)
            for u in m: place(u, old[u])
            return None
        place(t, s); done.append(t)
    return old

def revert(old):
    for t in old: unplace(t)
    for t, s in old.items(): place(t, s)

def pick_stand(t):
    if random.random() < 0.25:
        rs = [s for s in remotes if s in compatset[t] and s != where[t]]
        random.shuffle(rs)
        for s in rs:
            if fits(t, s): return s
        return random.choice(compat[t])
    return random.choice(compat[t])

def kempe(t, s2):
    s1 = where[t]
    X = {t}; Y = set(); fx = [t]
    while True:
        ny = set()
        for x in fx:
            for o in conflicts(x, s2):
                if o not in Y and where[o] == s2: ny.add(o)
        if not ny: break
        Y |= ny
        nx = set()
        for y in ny:
            for o in conflicts(y, s1):
                if o not in X and where[o] == s1: nx.add(o)
        X |= nx
        fx = list(nx)
        if len(X) + len(Y) > 14: return None
    m = {x: s2 for x in X}
    for y in Y: m[y] = s1
    return m

def eject(t, s2):
    # move t to s2, relocate conflicts greedily. returns (old, moved set) or None
    C = conflicts(t, s2)
    if len(C) > 4: return None
    M = set(C); M.add(t)
    before = lcost(M)
    old = {u: where[u] for u in M}
    for u in M: unplace(u)
    if not fits(t, s2):
        for u in M: place(u, old[u])
        return None
    place(t, s2)
    random.shuffle(C)
    for c in C:
        bestc = None; bs = None
        for s in compat[c]:
            if s == s2: continue
            if fits(c, s):
                v = tcost(c, s) + random.random() * 2000
                if bestc is None or v < bestc: bestc = v; bs = s
        if bs is None:
            for u in M:
                if u in occ[where[u]]: occ[where[u]].discard(u)
            for u in M: place(u, old[u])
            return None
        place(c, bs)
    after = lcost(M)
    return old, after - before

cur = fullcost(); best = cur; bestwhere = where[:]
print(dname, 'start', cur, flush=True)
start = time.time(); lastw = start; it = 0
def write_best():
    plan = {'stands': {sid[s]: [] for s in range(NS)}}
    for t in range(NT): plan['stands'][sid[bestwhere[t]]].append(tid[t])
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
    if it & 511 == 0:
        el = time.time() - start
        if el > tlimit: break
        phase = (el / tlimit * ncyc) % 1.0
        Tcur = T0 * (T1 / T0) ** phase
        if time.time() - lastw > 30:
            write_best(); lastw = time.time()
            print(dname, int(el), 'cur', cur, 'best', best, 'T', int(Tcur), flush=True)
    t = random.randrange(NT)
    s2 = pick_stand(t)
    if s2 == where[t]: continue
    r = random.random()
    if r < 0.3:
        m = {t: s2}
    elif r < 0.5:
        if not occ[s2]: m = {t: s2}
        else:
            u = random.choice(list(occ[s2]))
            if where[t] not in compatset[u]: continue
            m = {t: s2, u: where[t]}
    elif r < 0.75:
        m = kempe(t, s2)
        if m is None: continue
    else:
        res = eject(t, s2)
        if res is None: continue
        old, d = res
        if d <= 0 or random.random() < math.exp(-d / Tcur):
            cur += d
            if cur < best: best = cur; bestwhere = where[:]
        else:
            revert(old)
        continue
    M = set(m)
    before = lcost(M)
    old = try_moves(m)
    if old is None: continue
    d = lcost(M) - before
    if d <= 0 or random.random() < math.exp(-d / Tcur):
        cur += d
        if cur < best: best = cur; bestwhere = where[:]
    else:
        revert(old)
write_best()
assert fullcost() == cur, (fullcost(), cur)
print(dname, 'final best', best, 'iters', it, flush=True)

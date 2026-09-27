import json, sys, random, math, time, os
APP = os.environ["APP"]; sys.path.insert(0, APP + "/tools")
from check_plan import evaluate

def load(dname):
    return json.load(open(f"{APP}/days/{dname}.json"))

class S:
    def __init__(s, day, assign):
        s.day = day
        s.buf = day["buffer_minutes"]; s.bus = day["bus_cost_per_passenger"]
        s.stands = day["stands"]; s.NS = len(s.stands)
        s.sidx = {x["id"]: i for i, x in enumerate(s.stands)}
        s.turns = day["turns"]; s.NT = len(s.turns)
        s.tidx = {t["id"]: i for i, t in enumerate(s.turns)}
        s.A = [t["arrive"] for t in s.turns]; s.D = [t["depart"] for t in s.turns]
        s.big = [t["size"] == 3 for t in s.turns]
        s.W = day["walk_metres"]
        s.busc = [s.bus * (t["pax_in"] + t["pax_out"]) for t in s.turns]
        s.remote = [x["remote"] for x in s.stands]
        s.compat = [[j for j, x in enumerate(s.stands) if t["size"] <= x["size"] and (not t["international"] or x["international"])] for t in s.turns]
        s.compset = [set(c) for c in s.compat]
        s.tr = [(s.tidx[x["from"]], s.tidx[x["to"]], x["passengers"]) for x in day["transfers"]]
        s.inc = [[] for _ in range(s.NT)]
        for k, (a, b, p) in enumerate(s.tr):
            s.inc[a].append(k)
            if b != a: s.inc[b].append(k)
        s.wnb = [[] for _ in range(s.NS)]
        for a, b in day["wingtip_pairs"]:
            s.wnb[s.sidx[a]].append(s.sidx[b]); s.wnb[s.sidx[b]].append(s.sidx[a])
        s.where = list(assign)
        s.on = [set() for _ in range(s.NS)]
        for t, st in enumerate(s.where): s.on[st].add(t)
        s.cost = s.full_cost()

    def full_cost(s):
        c = sum(s.busc[t] for t in range(s.NT) if s.remote[s.where[t]])
        for a, b, p in s.tr: c += p * s.W[s.where[a]][s.where[b]]
        return c

    def conflicts(s, st, L, R, excl=()):
        # turns on st conflicting with interval [L,R] under buffer
        buf = s.buf; A = s.A; D = s.D
        return [x for x in s.on[st] if x not in excl and A[x] < R + buf and D[x] + buf > L]

    def wing_ok(s, t, st):
        if not s.big[t] or not s.wnb[st]: return True
        A = s.A; D = s.D
        for nb in s.wnb[st]:
            for x in s.on[nb]:
                if x != t and s.big[x] and A[x] < D[t] and A[t] < D[x]: return False
        return True

    def apply(s, moves):
        # moves: list of (t, newstand); returns delta, old
        ks = set()
        for t, _ in moves: ks.update(s.inc[t])
        W = s.W; wh = s.where; tr = s.tr
        before = 0
        for k in ks:
            a, b, p = tr[k]; before += p * W[wh[a]][wh[b]]
        db = 0
        old = []
        for t, ns in moves:
            os_ = wh[t]; old.append((t, os_))
            if s.remote[os_]: db -= s.busc[t]
            if s.remote[ns]: db += s.busc[t]
        for t, os_ in old: s.on[os_].discard(t)
        for t, ns in moves: wh[t] = ns; s.on[ns].add(t)
        after = 0
        for k in ks:
            a, b, p = tr[k]; after += p * W[wh[a]][wh[b]]
        return after - before + db, old

    def revert(s, old):
        for t, os_ in old: s.on[s.where[t]].discard(t)
        for t, os_ in old: s.where[t] = os_; s.on[os_].add(t)

def propose(s, rnd):
    t = rnd.randrange(s.NT)
    cs = s.compat[t]
    ns = cs[rnd.randrange(len(cs))]
    os_ = s.where[t]
    if ns == os_: return None
    r = rnd.random()
    if r < 0.5:
        C = s.conflicts(ns, s.A[t], s.D[t])
        moves = [(t, ns)]
        if C:
            others = [x for x in s.on[os_] if x != t]
            for c in C:
                if os_ not in s.compset[c]: return None
                for x in others:
                    if s.A[x] < s.D[c] + s.buf and s.D[x] + s.buf > s.A[c]: return None
                moves.append((c, os_))
        return moves
    else:
        # chain window swap
        L, R = s.A[t], s.D[t]
        X = {t}; Y = set()
        for _ in range(30):
            nX = set(s.conflicts(os_, L, R)); nY = set(s.conflicts(ns, L, R))
            nX.add(t)
            if nX == X and nY == Y: break
            X, Y = nX, nY
            for x in X | Y:
                if s.A[x] < L: L = s.A[x]
                if s.D[x] > R: R = s.D[x]
        else:
            return None
        if len(X) + len(Y) > 12: return None
        for x in X:
            if ns not in s.compset[x]: return None
        for y in Y:
            if os_ not in s.compset[y]: return None
        return [(x, ns) for x in X] + [(y, os_) for y in Y]

def run(dname, seed, secs, init_path, out_path, T0, T1):
    day = load(dname)
    idx = {x["id"]: i for i, x in enumerate(day["stands"])}
    tid = {t["id"]: i for i, t in enumerate(day["turns"])}
    plan = json.load(open(init_path))
    assign = [0] * len(day["turns"])
    for sid, lst in plan["stands"].items():
        for t in lst: assign[tid[t]] = idx[sid]
    s = S(day, assign)
    rnd = random.Random(seed)
    best = s.cost; bestw = list(s.where)
    start = time.time(); it = 0; lastsave = start
    cur = s.cost
    while True:
        it += 1
        if it & 1023 == 0:
            el = time.time() - start
            if el > secs: break
            f = el / secs
            T = T0 * (T1 / T0) ** f
        elif it < 1024:
            T = T0
        mv = propose(s, rnd)
        if mv is None: continue
        d, old = s.apply(mv)
        ok = all(s.wing_ok(t, ns) for t, ns in mv)
        if ok and (d <= 0 or rnd.random() < math.exp(-d / T)):
            cur += d
            if cur < best:
                best = cur; bestw = list(s.where)
        else:
            s.revert(old)
        if time.time() - lastsave > 30 if it & 1023 == 0 else False:
            lastsave = time.time(); save(day, bestw, out_path, best)
    save(day, bestw, out_path, best)
    return best

def save(day, w, out_path, best):
    st = {x["id"]: [] for x in day["stands"]}
    for i, t in enumerate(day["turns"]):
        st[day["stands"][w[i]]["id"]].append(t["id"])
    plan = {"stands": st}
    c = evaluate(day, plan)
    assert c == best, (c, best)
    # only overwrite if better than existing
    try:
        ex = evaluate(day, json.load(open(out_path)))
    except Exception:
        ex = None
    if ex is None or c < ex:
        tmp = out_path + ".tmp"
        json.dump(plan, open(tmp, "w"), indent=0)
        os.replace(tmp, out_path)

if __name__ == "__main__":
    dname, seed, secs, init, out = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), sys.argv[4], sys.argv[5]
    T0 = float(sys.argv[6]) if len(sys.argv) > 6 else 30000
    T1 = float(sys.argv[7]) if len(sys.argv) > 7 else 100
    b = run(dname, seed, secs, init, out, T0, T1)
    print(dname, seed, b, flush=True)

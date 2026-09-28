import json, sys, random, math, time, os
sys.path.insert(0, "tools")
from check_layout import evaluate

E = sys.argv[1]; TL = float(sys.argv[2]); seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0
rng = random.Random(seed)
ed = json.load(open(f"editions/{E}.json"))
C, R, P = ed["columns"], ed["rows"], ed["pages"]
ads = ed["ads"]; N = len(ads)
W = [a["width"] for a in ads]; D = [a["depth"] for a in ads]; AR = [W[i]*D[i] for i in range(N)]
G = [a["competitor_group"] for a in ads]
BK = [a["booked"] for a in ads]
cap = {p: (ed["front_page_ad_rows"]*C if p == 1 else ed["max_ad_share_percent"]*R*C//100) for p in range(1, P+1)}
hgt = {p: (ed["front_page_ad_rows"] if p == 1 else R) for p in range(1, P+1)}
def pen(i, p):
    a = ads[i]
    if p == 0: return a["rate"]
    c = 0
    if a["section"] is not None:
        f, l = ed["sections"][a["section"]]
        if not f <= p <= l: c += a["rate"]*ed["wrong_section_percent"]//100
    if a["right_hand"] and p % 2 == 0: c += a["rate"]*ed["left_hand_percent"]//100
    return c
PEN = [[pen(i, p) for p in range(P+1)] for i in range(N)]
def spread(p): return 0 if p == 1 else p//2

packcache = {}
def packable(shapes, H):
    # shapes: sorted tuple of (w,d)
    key = (shapes, H)
    r = packcache.get(key)
    if r is not None: return r
    res = pack_layout(shapes, H) is not None
    packcache[key] = res
    return res

def pack_layout(shapes, H):
    kinds = sorted(set(shapes), key=lambda s: -s[0]*s[1])
    cnt = [shapes.count(k) for k in kinds]
    memo = set()
    out = []
    def rec(sky, cnt, remarea):
        if remarea == 0: return True
        free = sum(H - h for h in sky)
        if remarea > free: return False
        key = (sky, tuple(cnt))
        if key in memo: return False
        mh = min(sky); c = sky.index(mh)
        e = c
        while e < C and sky[e] == mh: e += 1
        seg = e - c
        for k, (w, d) in enumerate(kinds):
            if cnt[k] and w <= seg and mh + d <= H:
                cnt[k] -= 1
                ns = sky[:c] + (mh+d,)*w + sky[c+w:]
                out.append((w, d, c, mh))
                if rec(ns, cnt, remarea - w*d): cnt[k] += 1; return True
                out.pop(); cnt[k] += 1
        # waste
        nh = H
        if True:
            ns = sky[:c] + (nh,)*seg + sky[e:]
            if rec(ns, cnt, remarea): return True
        memo.add(key)
        return False
    ok = rec((0,)*C, cnt, sum(w*d for w, d in shapes))
    return out if ok else None

# state
page = [0]*N
content = {p: [] for p in range(P+1)}
used = {p: 0 for p in range(P+1)}
grp = {}  # (g, spread) -> count
def shapes_of(lst): return tuple(sorted((W[i], D[i]) for i in lst))
def can_add(p, add, rem):
    # add/rem: lists of ad indices
    if p == 0: return True
    u = used[p] + sum(AR[i] for i in add) - sum(AR[i] for i in rem)
    if u > cap[p]: return False
    lst = [i for i in content[p] if i not in rem] + add
    return packable(shapes_of(lst), hgt[p])
def grp_ok(i, p, ignore=()):
    g = G[i]
    if g is None or p == 0: return True
    s = spread(p)
    for j in grp.get((g, s), ()):
        if j not in ignore and j != i: return False
    return True
def place(i, p):
    page[i] = p; content[p].append(i); used[p] += AR[i]
    if G[i] is not None and p: grp.setdefault((G[i], spread(p)), set()).add(i)
def unplace(i):
    p = page[i]; content[p].remove(i); used[p] -= AR[i]
    if G[i] is not None and p: grp[(G[i], spread(p))].discard(i)
    page[i] = 0

# init from planner-like greedy
start = None
if os.path.exists(f"layouts/{E}.json") and os.environ.get("FRESH") != "1":
    try:
        lay = json.load(open(f"layouts/{E}.json"))["placements"]
        idx = {a["id"]: i for i, a in enumerate(ads)}
        for i in range(N): content[0].append(i)
        for aid, pos in lay.items():
            i = idx[aid]; content[0].remove(i); place(i, pos["page"])
        start = True
    except Exception as ex:
        print("load fail", ex)
if not start:
    for p in content: content[p] = []
    for p in used: used[p] = 0
    grp.clear()
    order = sorted(range(N), key=lambda i: (not BK[i], -ads[i]["rate"]))
    for i in order:
        pl = sorted(range(1, P+1), key=lambda p: PEN[i][p])
        page[i] = 0
        for p in pl:
            if grp_ok(i, p) and can_add(p, [i], []):
                place(i, p); break
        else:
            content[0].append(i)
def total():
    return sum(PEN[i][page[i]] for i in range(N)) + sum(10**6 for i in range(N) if BK[i] and page[i] == 0)
cur = total()
best = cur; bestpage = page[:]
print(E, "start", cur, flush=True); wbest = cur

def write(pg):
    # build layout
    pl = {}
    for p in range(1, P+1):
        lst = [i for i in range(N) if pg[i] == p]
        sh = shapes_of(lst)
        lay = pack_layout(sh, hgt[p])
        assert lay is not None
        pool = {}
        for i in lst: pool.setdefault((W[i], D[i]), []).append(i)
        for (w, d, c, h) in lay:
            i = pool[(w, d)].pop()
            pl[ads[i]["id"]] = {"page": p, "column": c, "row": R - h - d}
    L = {"placements": pl}
    cost = evaluate(ed, L)
    old = None
    try:
        old = evaluate(ed, json.load(open(f"layouts/{E}.json")))
    except Exception: pass
    if old is None or cost < old:
        tmp = f"layouts/{E}.json.tmp"
        json.dump(L, open(tmp, "w"), indent=1); os.replace(tmp, f"layouts/{E}.json")
        print(E, "wrote", cost, flush=True)
    return cost

t0 = time.time(); lastw = t0
K = int(sys.argv[4]) if len(sys.argv) > 4 else 0
NOISE = float(sys.argv[5]) if len(sys.argv) > 5 else 0.4
TRIES = int(sys.argv[6]) if len(sys.argv) > 6 else 30
TT = float(sys.argv[7]) if len(sys.argv) > 7 else 1e-9
it = 0; acc = 0; imp = 0
dens = [ads[i]["rate"]/AR[i] for i in range(N)]
while time.time() - t0 < TL:
    it += 1
    if time.time() - lastw > 45 and best < wbest:
        wbest = write(bestpage); lastw = time.time()
    k = rng.choice([2, 2, 3, 3, 4]) if K == 0 else K
    if rng.random() < 0.5:
        pgs = rng.sample(range(1, P+1), k)
    else:
        s = rng.randrange(1, P+1); pgs = sorted(set(min(P, max(1, s + rng.randrange(-3, 4))) for _ in range(k)) | {s})
    pool = [i for p in pgs for i in content[p]] + list(content[0])
    oldc = sum(PEN[i][page[i]] for i in pool)
    saved = [(i, page[i]) for i in pool]
    for i in pool: unplace(i)
    bestc = None; bestas = None
    for t in range(TRIES):
        noise = NOISE * rng.random()
        if t % 3 == 2:
            key = lambda i: (not BK[i], -AR[i] * (1 + noise*(rng.random()-0.5)))
        else:
            key = lambda i: (not BK[i], -dens[i] * (1 + noise*(rng.random()-0.5)))
        order = sorted(pool, key=key)
        asg = []; c = 0; ok = True
        for i in order:
            cands = [p for p in pgs if used[p] + AR[i] <= cap[p] and grp_ok(i, p)]
            cands.sort(key=lambda p: (PEN[i][p], rng.random()))
            done = False
            for p in cands:
                if not BK[i] and PEN[i][p] >= PEN[i][0]: break
                if can_add(p, [i], []):
                    place(i, p); asg.append((i, p)); c += PEN[i][p]; done = True; break
            if not done:
                if BK[i]: ok = False; break
                c += PEN[i][0]
            if bestc is not None and c > bestc: break
        for i, p in asg: unplace(i)
        if ok and (bestc is None or c < bestc):
            bestc = c; bestas = asg
    if bestas is not None and (bestc <= oldc or rng.random() < math.exp(-(bestc-oldc)/TT)):
        for i, p in bestas: place(i, p)
        pl_ = set(i for i, p in bestas)
        for i in pool:
            if i not in pl_: place(i, 0)
        cur += bestc - oldc; acc += 1
    else:
        for i, p in saved: place(i, p)
    if cur < best:
        best = cur; bestpage = page[:]; imp += 1
print(E, "best", best, "iters", it, "acc", acc, "imp", imp, "cache", len(packcache), flush=True)
print(E, "final", write(bestpage), flush=True)

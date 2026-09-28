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
TT = float(sys.argv[4]) if len(sys.argv) > 4 else 1e-9
NODES = int(sys.argv[5]) if len(sys.argv) > 5 else 20000
it = 0; acc = 0; imp = 0
BIG = 10**7
def knap(p, pool):
    # choose subset of pool for page p maximizing sum val, packable, groups ok
    items = [i for i in pool if grp_ok(i, p) and AR[i] <= cap[p] and (p != 1 or D[i] <= hgt[1])]
    val = {i: (BIG if BK[i] else 0) + PEN[i][0] - PEN[i][p] for i in items}
    items = [i for i in items if val[i] > 0]
    rng.shuffle(items)
    items.sort(key=lambda i: -val[i]/AR[i])
    n = len(items)
    best = [0, []]
    nodes = [0]
    chosen = []
    capp = cap[p]
    def rec(k, area, v, gset):
        nodes[0] += 1
        if v > best[0]:
            if packable(shapes_of(chosen), hgt[p]):
                best[0] = v; best[1] = list(chosen)
            else:
                return
        if nodes[0] > NODES: return
        rem = capp - area
        # bound
        bnd = v; r = rem
        for j in range(k, n):
            i = items[j]
            if AR[i] <= r: bnd += val[i]; r -= AR[i]
            else: bnd += val[i] * r / AR[i]; break
        if bnd <= best[0]: return
        for j in range(k, n):
            i = items[j]
            if AR[i] <= rem and (G[i] is None or G[i] not in gset):
                chosen.append(i)
                rec(j+1, area+AR[i], v+val[i], gset | {G[i]} if G[i] else gset)
                chosen.pop()
                if nodes[0] > NODES: return
    rec(0, 0, 0, frozenset())
    return best[1]
while time.time() - t0 < TL:
    it += 1
    if time.time() - lastw > 45 and best < wbest:
        wbest = write(bestpage); lastw = time.time()
    Tc = TT * (0.01 ** ((time.time()-t0)/TL))
    k = rng.choice([1, 2, 2, 3, 4])
    pgs = rng.sample(range(1, P+1), k)
    pool = [i for p in pgs for i in content[p]] + list(content[0])
    oldc = sum(PEN[i][page[i]] for i in pool)
    saved = [(i, page[i]) for i in pool]
    for i in pool: unplace(i)
    rem = set(pool); asg = []
    rng.shuffle(pgs)
    for p in pgs:
        sel = knap(p, list(rem))
        for i in sel:
            place(i, p); asg.append((i, p)); rem.discard(i)
    ok = not any(BK[i] for i in rem)
    c = sum(PEN[i][p] for i, p in asg) + sum(PEN[i][0] for i in rem)
    for i, p in asg: unplace(i)
    if ok and (c <= oldc or rng.random() < math.exp(-(c-oldc)/Tc)):
        for i, p in asg: place(i, p)
        for i in rem: place(i, 0)
        cur += c - oldc; acc += 1
    else:
        for i, p in saved: place(i, p)
    if cur < best:
        best = cur; bestpage = page[:]; imp += 1
        print(E, "imp", best, flush=True)
print(E, "best", best, "iters", it, "acc", acc, "imp", imp, "cache", len(packcache), flush=True)
print(E, "final", write(bestpage), flush=True)

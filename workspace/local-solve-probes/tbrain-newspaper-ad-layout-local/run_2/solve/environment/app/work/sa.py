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
if os.path.exists(f"layouts/{E}.json"):
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
print(E, "start", cur, flush=True)

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

t0 = time.time(); T0 = 60.0; T1 = 0.5
it = 0
while True:
    it += 1
    if it % 200 == 0:
        el = time.time() - t0
        if el > TL: break
        frac = el / TL
        T = T0 * (T1/T0) ** frac
    elif it < 200: T = T0
    r = rng.random()
    i = rng.randrange(N)
    pi = page[i]
    if r < 0.5:
        # move i to page q
        q = rng.randrange(0, P+1)
        if q == pi or (q == 0 and BK[i]): continue
        d = PEN[i][q] - PEN[i][pi]
        if d > 0 and rng.random() >= math.exp(-d/T): continue
        if not grp_ok(i, q): continue
        if not can_add(q, [i], []): continue
        unplace(i); place(i, q)
        cur += d
    else:
        # swap i with j on another page
        j = rng.randrange(N); pj = page[j]
        if pj == pi: continue
        if (pi == 0 and BK[j]) or (pj == 0 and BK[i]): continue
        d = PEN[i][pj] + PEN[j][pi] - PEN[i][pi] - PEN[j][pj]
        if d > 0 and rng.random() >= math.exp(-d/T): continue
        if not grp_ok(i, pj, ignore=(j,)) or not grp_ok(j, pi, ignore=(i,)): continue
        if G[i] is not None and G[i] == G[j]: pass
        if not can_add(pj, [i], [j]) or not can_add(pi, [j], [i]): continue
        unplace(i); unplace(j)
        place(i, pj); place(j, pi)
        cur += d
    if cur < best:
        best = cur; bestpage = page[:]
print(E, "best", best, "iters", it, "cache", len(packcache), flush=True)
print(E, "final", write(bestpage), flush=True)

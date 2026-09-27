import json, sys, random, math, time, os
sys.path.insert(0, '/app/tools')
import check_roster

ward_name, seconds, seed = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
init = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "-" else None
T0ARG = float(sys.argv[5]) if len(sys.argv) > 5 else 200.0
TENDARG = float(sys.argv[6]) if len(sys.argv) > 6 else 2.0
W = json.load(open(f'/app/wards/{ward_name}.json'))
D = W['days']; NS = W['nurses']; N = len(NS)
H = W['shift_hours']; w = W['weights']; R = W['rules']
MC = R['max_consecutive_days']; RA = R['rest_days_after_nights']; MW = R['max_weekends']
CODES = ['.', 'E', 'L', 'N']
HR = {'.': 0, 'E': H['E'], 'L': H['L'], 'N': H['N']}
isrn = [n['grade'] != 'HCA' for n in NS]
issen = [n['grade'] == 'senior' for n in NS]
leave = [set(n['leave']) for n in NS]
reqs = [[(r['day'], r['off']) for r in n['requests']] for n in NS]
HARD = 1000
rng = random.Random(seed)

def ncost(i, row):
    n = NS[i]; hard = 0; soft = 0
    for d in leave[i]:
        if row[d] != '.': hard += 1
    run = 0; worked = 0; nights = 0
    prev = '.'
    for d in range(D):
        c = row[d]
        if c != '.':
            run += 1
            if run > MC: hard += 1
            worked += HR[c]
            if c == 'N': nights += 1
        else:
            run = 0
        if d > 0:
            p = row[d-1]
            if (p == 'N' and (c == 'E' or c == 'L')) or (p == 'L' and c == 'E'): hard += 1
            if p == 'N' and c != 'N':
                for k in range(d, min(D, d + RA)):
                    if row[k] != '.': hard += 1
    if worked < n['min_hours']: soft += w['hour_under'] * (n['min_hours'] - worked)
    if worked > n['max_hours']: soft += w['hour_over'] * (worked - n['max_hours'])
    if nights > n['max_nights']: soft += w['night_over'] * (nights - n['max_nights'])
    wk = 0
    for sat in range(5, D, 7):
        a = row[sat] != '.'
        b = sat + 1 < D and row[sat+1] != '.'
        if a or b: wk += 1
        if sat + 1 < D and a != b: soft += w['split_weekend']
    if wk > MW: soft += w['weekend_over'] * (wk - MW)
    for d in range(1, D-1):
        if row[d] != '.' and row[d-1] == '.' and row[d+1] == '.': soft += w['lone_day']
    for d, o in reqs[i]:
        if o == 'day':
            if row[d] != '.': soft += w['request']
        elif row[d] == o: soft += w['request']
    return hard * HARD + soft

cov = W['cover']
SI = {'E': 0, 'L': 1, 'N': 2}
def dcost(cnt, rn, sn, s):
    c = cov[s]; x = cnt; h = 0
    if x < c['minimum']: h += c['minimum'] - x
    if rn < c['registered']: h += c['registered'] - rn
    if sn < 1: h += 1
    so = w['short_of_preferred'] * (c['preferred'] - x) if x < c['preferred'] else 0
    return h * HARD + so

# state
if init:
    r0 = json.load(open(init))['roster']
    rows = [list(r0[n['id']]) for n in NS]
else:
    rows = [['.'] * D for _ in range(N)]
cnt = [[0,0,0] for _ in range(D)]; rnc = [[0,0,0] for _ in range(D)]; snc = [[0,0,0] for _ in range(D)]
for i in range(N):
    for d in range(D):
        c = rows[i][d]
        if c != '.':
            k = SI[c]; cnt[d][k] += 1; rnc[d][k] += isrn[i]; snc[d][k] += issen[i]
def daycost(d):
    return sum(dcost(cnt[d][k], rnc[d][k], snc[d][k], s) for s, k in SI.items())
NC = [ncost(i, rows[i]) for i in range(N)]
DC = [daycost(d) for d in range(D)]
total = sum(NC) + sum(DC)

def apply(changes):
    # changes: list of (i,d,new); returns delta and undo info; applied in place
    nurses = set(); days = set(); undo = []
    for i, d, c in changes:
        old = rows[i][d]
        if old == c: continue
        undo.append((i, d, old))
        if old != '.':
            k = SI[old]; cnt[d][k] -= 1; rnc[d][k] -= isrn[i]; snc[d][k] -= issen[i]
        if c != '.':
            k = SI[c]; cnt[d][k] += 1; rnc[d][k] += isrn[i]; snc[d][k] += issen[i]
        rows[i][d] = c
        nurses.add(i); days.add(d)
    delta = 0; newn = {}; newd = {}
    for i in nurses:
        v = ncost(i, rows[i]); newn[i] = v; delta += v - NC[i]
    for d in days:
        v = daycost(d); newd[d] = v; delta += v - DC[d]
    return delta, undo, newn, newd

def revert(undo):
    for i, d, old in reversed(undo):
        c = rows[i][d]
        if c != '.':
            k = SI[c]; cnt[d][k] -= 1; rnc[d][k] -= isrn[i]; snc[d][k] -= issen[i]
        if old != '.':
            k = SI[old]; cnt[d][k] += 1; rnc[d][k] += isrn[i]; snc[d][k] += issen[i]
        rows[i][d] = old

def propose():
    m = rng.random()
    if m < 0.08:
        i = rng.randrange(N); d1 = rng.randrange(D); d2 = rng.randrange(D)
        return [(i, d1, rows[i][d2]), (i, d2, rows[i][d1])]
    elif m < 0.30:
        i = rng.randrange(N); d = rng.randrange(D)
        return [(i, d, rng.choice(CODES))]
    elif m < 0.55:
        d = rng.randrange(D); i = rng.randrange(N); j = rng.randrange(N)
        return [(i, d, rows[j][d]), (j, d, rows[i][d])]
    elif m < 0.80:
        i = rng.randrange(N); j = rng.randrange(N)
        L = rng.randint(2, 7); d0 = rng.randrange(D - L + 1)
        ch = []
        for d in range(d0, d0 + L):
            ch.append((i, d, rows[j][d])); ch.append((j, d, rows[i][d]))
        return ch
    elif m < 0.90:
        # set a block to one code
        i = rng.randrange(N); L = rng.randint(2, 5); d0 = rng.randrange(D - L + 1)
        c = rng.choice(CODES)
        return [(i, d, c) for d in range(d0, d0 + L)]
    else:
        # weekend pair set
        i = rng.randrange(N); sat = rng.choice(range(5, D - 1, 7))
        c = rng.choice(CODES); c2 = rng.choice(CODES) if c != '.' else '.'
        if c == 'N' and c2 != 'N': c2 = 'N' if rng.random()<0.5 else c2
        return [(i, sat, c), (i, sat + 1, c2)]

def roster():
    return {"roster": {NS[i]['id']: ''.join(rows[i]) for i in range(N)}}

best = total; best_rows = [r[:] for r in rows]
t0 = time.time(); T0 = T0ARG; Tend = TENDARG
it = 0; T = T0
last_imp = time.time()
while True:
    it += 1
    if (it & 1023) == 0:
        el = time.time() - t0
        if el > seconds: break
        frac = el / seconds
        T = T0 * (Tend / T0) ** frac
        if time.time() - last_imp > max(20, seconds * 0.15) and best < HARD:
            # reheat from best
            for i in range(N):
                pass
            last_imp = time.time()
            T0 = T0 * 0.7
    ch = propose()
    delta, undo, newn, newd = apply(ch)
    if not undo:
        continue
    if delta <= 0 or rng.random() < math.exp(-delta / T):
        total += delta
        for i, v in newn.items(): NC[i] = v
        for d, v in newd.items(): DC[d] = v
        if total < best:
            best = total; best_rows = [r[:] for r in rows]; last_imp = time.time()
    else:
        revert(undo)

rows = best_rows
res = {"roster": {NS[i]['id']: ''.join(rows[i]) for i in range(N)}}
try:
    p = check_roster.evaluate(W, res); ok = True
except check_roster.RosterError as e:
    p = str(e); ok = False
print(ward_name, seed, 'best', best, 'check', p, 'iters', it, flush=True)
if ok:
    out = f'/app/work/{ward_name}_{seed}.json'
    json.dump(res, open(out, 'w'))
    tgt = f'/app/rosters/{ward_name}.json'
    import fcntl
    lk = open('/app/work/lock', 'w'); fcntl.flock(lk, fcntl.LOCK_EX)
    try:
        cur = check_roster.evaluate(W, check_roster.load_roster(tgt))
    except Exception:
        cur = 10**12
    if p < cur:
        tmp = tgt + '.tmp%d' % seed
        json.dump(res, open(tmp, 'w'), indent=1); os.replace(tmp, tgt)
        print('wrote', tgt, p, flush=True)

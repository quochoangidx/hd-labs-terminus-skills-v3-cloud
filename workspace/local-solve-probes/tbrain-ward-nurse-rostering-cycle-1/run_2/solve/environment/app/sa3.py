import json, sys, random, math, time, os
sys.path.insert(0, '/app/tools')
from check_roster import evaluate, RosterError

HARD = 1000000
HW = float(sys.argv[6]) if len(sys.argv) > 6 else 200.0
ward_name = sys.argv[1]; tlimit = float(sys.argv[2]); seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0
random.seed(seed)
ward = json.load(open(f'/app/wards/{ward_name}.json'))
D = ward['days']; H = ward['shift_hours']; W = ward['weights']; R = ward['rules']
nurses = ward['nurses']; N = len(nurses)
cover = ward['cover']; SH = 'ELN'
grade = [n['grade'] for n in nurses]
isreg = [g != 'HCA' for g in grade]; issen = [g == 'senior' for g in grade]
leave = [set(n['leave']) for n in nurses]
MC = R['max_consecutive_days']; RA = R['rest_days_after_nights']; MW = R['max_weekends']

def nurse_cost(i, row):
    n = nurses[i]; c = 0
    for d in leave[i]:
        if row[d] != '.': c += HARD
    prev = row[0]; run = 1 if prev != '.' else 0
    for d in range(1, D):
        x = row[d]
        if prev + x in ('NE', 'NL', 'LE'): c += HARD
        run = run + 1 if x != '.' else 0
        if run > MC: c += HARD
        prev = x
    for d in range(D - 1):
        if row[d] == 'N' and row[d+1] != 'N':
            for k in range(d+1, min(D, d+1+RA)):
                if row[k] != '.': c += HARD
    worked = sum(H[x] for x in row if x != '.')
    if worked < n['min_hours']: c += W['hour_under'] * (n['min_hours'] - worked)
    if worked > n['max_hours']: c += W['hour_over'] * (worked - n['max_hours'])
    nn = row.count('N')
    if nn > n['max_nights']: c += W['night_over'] * (nn - n['max_nights'])
    wk = 0
    for sat in range(5, D, 7):
        a = row[sat] != '.'; b = sat+1 < D and row[sat+1] != '.'
        if a or b: wk += 1
        if sat+1 < D and a != b: c += W['split_weekend']
    if wk > MW: c += W['weekend_over'] * (wk - MW)
    for d in range(1, D-1):
        if row[d] != '.' and row[d-1] == '.' and row[d+1] == '.': c += W['lone_day']
    for rq in n['requests']:
        d, want = rq['day'], rq['off']
        if want == 'day':
            if row[d] != '.': c += W['request']
        elif row[d] == want: c += W['request']
    return c

def slot_cost(tot, reg, sen, s):
    need = cover[s]; c = 0
    if tot < need['minimum']: c += HARD * (need['minimum'] - tot)
    if reg < need['registered']: c += HARD * (need['registered'] - reg)
    if sen < 1: c += HARD
    if tot < need['preferred']: c += W['short_of_preferred'] * (need['preferred'] - tot)
    return c

# init: from planner if available else empty
init = None
try:
    if len(sys.argv) > 7: raise Exception("fresh")
    init = json.load(open(f'/app/rosters/{ward_name}.json'))['roster']
    evaluate(ward, {'roster': init})
except Exception:
    init = None
if init is None:
    sys.path.insert(0, '/app/planner')
    import plan_ward
    try: init = plan_ward.plan(ward)['roster']
    except SystemExit: init = {n['id']: '.'*D for n in nurses}
rows = [list(init[n['id']]) for n in nurses]

cnt = [[[0,0,0] for _ in SH] for _ in range(D)]  # tot,reg,sen
SI = {'E':0,'L':1,'N':2}
for i in range(N):
    for d in range(D):
        x = rows[i][d]
        if x != '.':
            t = cnt[d][SI[x]]; t[0]+=1; t[1]+=isreg[i]; t[2]+=issen[i]
ncost = [nurse_cost(i, rows[i]) for i in range(N)]
def day_cost(d): return sum(slot_cost(*cnt[d][k], SH[k]) for k in range(3))
dcost = [day_cost(d) for d in range(D)]
total = sum(ncost) + sum(dcost)

def apply(i, d, x):
    old = rows[i][d]
    if old != '.':
        t = cnt[d][SI[old]]; t[0]-=1; t[1]-=isreg[i]; t[2]-=issen[i]
    if x != '.':
        t = cnt[d][SI[x]]; t[0]+=1; t[1]+=isreg[i]; t[2]+=issen[i]
    rows[i][d] = x

def acc(delta, T):
    dh = round(delta / HARD); e = delta - HARD * dh + HW * dh
    return e <= 0 or random.random() < math.exp(-e / T)

CODES = 'ELN.'
best = total; best_rows = [r[:] for r in rows]
def save():
    out = {'roster': {nurses[i]['id']: ''.join(best_rows[i]) for i in range(N)}}
    try:
        p = evaluate(ward, out)
    except RosterError as e:
        return None
    cur = None
    try:
        cur = evaluate(ward, json.load(open(f'/app/rosters/{ward_name}.json')))
    except Exception:
        cur = None
    if cur is None or p < cur:
        tmp = f'/app/rosters/.{ward_name}.{seed}.tmp'
        json.dump(out, open(tmp, 'w'))
        os.replace(tmp, f'/app/rosters/{ward_name}.json')
    return p

T0 = float(sys.argv[4]) if len(sys.argv) > 4 else 60.0; T1 = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
start = time.time(); it = 0; lastsave = start
T = T0
while True:
    it += 1
    if it & 1023 == 0:
        el = time.time() - start
        if el > tlimit: break
        frac = el / tlimit
        T = T0 * (T1/T0) ** frac
        if time.time() - lastsave > 20 and best < HARD:
            save(); lastsave = time.time()
    m = random.random()
    if m < 0.12:
        i = random.randrange(N); j = random.randrange(N)
        if i == j: continue
        ds = random.sample(range(D), random.randint(2, 3))
        si = [rows[i][d] for d in ds]; sj = [rows[j][d] for d in ds]
        if si == sj: continue
        oldd = sum(dcost[d] for d in ds)
        for k, d in enumerate(ds): apply(i, d, sj[k]); apply(j, d, si[k])
        newdc = [day_cost(d) for d in ds]
        nci = nurse_cost(i, rows[i]); ncj = nurse_cost(j, rows[j])
        delta = nci - ncost[i] + ncj - ncost[j] + sum(newdc) - oldd
        if acc(delta, T):
            ncost[i] = nci; ncost[j] = ncj; total += delta
            for k, d in enumerate(ds): dcost[d] = newdc[k]
        else:
            for k, d in enumerate(ds): apply(i, d, si[k]); apply(j, d, sj[k])
    elif m < 0.22:
        i = random.randrange(N)
        ds = random.sample(range(D), random.randint(2, 4))
        old = [rows[i][d] for d in ds]; new = [random.choice(CODES) for d in ds]
        if old == new: continue
        oldd = sum(dcost[d] for d in ds)
        for k, d in enumerate(ds): apply(i, d, new[k])
        newdc = [day_cost(d) for d in ds]
        nc = nurse_cost(i, rows[i])
        delta = nc - ncost[i] + sum(newdc) - oldd
        if acc(delta, T):
            ncost[i] = nc; total += delta
            for k, d in enumerate(ds): dcost[d] = newdc[k]
        else:
            for k, d in enumerate(ds): apply(i, d, old[k])
    elif m < 0.32:
        i = random.randrange(N); a = random.randrange(D); b = random.randrange(D)
        if rows[i][a] == rows[i][b]: continue
        xa = rows[i][a]; xb = rows[i][b]
        olda = dcost[a] + dcost[b]
        apply(i, a, xb); apply(i, b, xa)
        na = day_cost(a); nb = day_cost(b)
        nc = nurse_cost(i, rows[i])
        delta = nc - ncost[i] + na + nb - olda
        if acc(delta, T):
            ncost[i] = nc; dcost[a] = na; dcost[b] = nb; total += delta
        else:
            apply(i, a, xa); apply(i, b, xb)
    elif m < 0.5:
        # single/segment change for one nurse
        i = random.randrange(N)
        L = 1 if random.random() < 0.6 else random.randint(2, 7)
        d0 = random.randrange(D - L + 1)
        if random.random() < 0.5:
            x = random.choice(CODES); newseg = [x]*L
        else:
            newseg = [random.choice(CODES) for _ in range(L)]
        oldseg = rows[i][d0:d0+L]
        if newseg == oldseg: continue
        oldd = sum(dcost[d] for d in range(d0, d0+L))
        for k in range(L): apply(i, d0+k, newseg[k])
        newdc = [day_cost(d) for d in range(d0, d0+L)]
        nc = nurse_cost(i, rows[i])
        delta = nc - ncost[i] + sum(newdc) - oldd
        if acc(delta, T):
            ncost[i] = nc
            for k in range(L): dcost[d0+k] = newdc[k]
            total += delta
        else:
            for k in range(L): apply(i, d0+k, oldseg[k])
    else:
        # swap segment between two nurses
        i = random.randrange(N); j = random.randrange(N)
        if i == j: continue
        L = 1 if random.random() < 0.5 else random.randint(2, 7)
        d0 = random.randrange(D - L + 1)
        si = rows[i][d0:d0+L]; sj = rows[j][d0:d0+L]
        if si == sj: continue
        oldd = sum(dcost[d] for d in range(d0, d0+L))
        for k in range(L): apply(i, d0+k, sj[k]); apply(j, d0+k, si[k])
        newdc = [day_cost(d) for d in range(d0, d0+L)] if isreg[i] != isreg[j] or issen[i] != issen[j] else None
        nci = nurse_cost(i, rows[i]); ncj = nurse_cost(j, rows[j])
        delta = nci - ncost[i] + ncj - ncost[j] + ((sum(newdc) - oldd) if newdc else 0)
        if acc(delta, T):
            ncost[i] = nci; ncost[j] = ncj
            if newdc:
                for k in range(L): dcost[d0+k] = newdc[k]
            total += delta
        else:
            for k in range(L): apply(i, d0+k, si[k]); apply(j, d0+k, sj[k])
    if total < best:
        best = total; best_rows = [r[:] for r in rows]
p = save()
print(ward_name, 'seed', seed, 'iters', it, 'best', best, 'checked', p, flush=True)

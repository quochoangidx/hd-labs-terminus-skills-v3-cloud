import json, sys, random, math, time, os
sys.path.insert(0, '/app/tools')
from check_roster import evaluate
from sa import make, load, save_if_better, M

def solve(wname, seconds, seed, T0, T1):
    ward = load(wname); rnd = random.Random(seed)
    days = ward['days']; nurses = ward['nurses']; N = len(nurses)
    ncost = make(ward); W = ward['weights']; cov = ward['cover']
    grade = [n['grade'] for n in nurses]
    isrn = [g != 'HCA' for g in grade]; issen = [g == 'senior' for g in grade]
    if os.environ.get('FRESH'):
        rows = ['.'*days for _ in nurses]
    else:
        cur = json.load(open(f'/app/rosters/{wname}.json'))['roster']
        rows = [cur[n['id']] for n in nurses]
    SI = {'E':0,'L':1,'N':2}
    cnt = [[[0,0,0] for _ in range(3)] for _ in range(days)]
    for i,r in enumerate(rows):
        for d,ch in enumerate(r):
            if ch != '.':
                x = cnt[d][SI[ch]]; x[0]+=1; x[1]+=isrn[i]; x[2]+=issen[i]
    covs = [cov['E'], cov['L'], cov['N']]
    sp = W['short_of_preferred']
    def ccost(x, s):
        cv = covs[s]; c = 0
        if x[0] < cv['minimum']: c += M*(cv['minimum']-x[0])
        if x[1] < cv['registered']: c += M*(cv['registered']-x[1])
        if x[2] < 1: c += M
        if x[0] < cv['preferred']: c += sp*(cv['preferred']-x[0])
        return c
    nc = [ncost(nurses[i], rows[i]) for i in range(N)]
    total = sum(nc) + sum(ccost(cnt[d][s], s) for d in range(days) for s in range(3))
    best = total; bestrows = list(rows)
    t_start = time.time(); it = 0; T = T0
    codes = 'ELN.'
    while True:
        it += 1
        if it & 1023 == 0:
            el = time.time() - t_start
            if el > seconds: break
            T = T0 * (T1/T0) ** (el/seconds)
        mv = rnd.random()
        newrows = {}
        if mv < 0.3:
            i = rnd.randrange(N); d = rnd.randrange(days); L = rnd.choice((1,1,1,2,2,3))
            d2 = min(days, d+L); ch = rnd.choice(codes)
            old = rows[i]; new = old[:d] + ch*(d2-d) + old[d2:]
            if new == old: continue
            newrows[i] = new
        elif mv < 0.5:
            # intra-row swap of two segments/days
            i = rnd.randrange(N); L = rnd.choice((1,1,1,2,2,3,4))
            d1 = rnd.randrange(days-L+1); d2 = rnd.randrange(days-L+1)
            if d1 > d2: d1, d2 = d2, d1
            if d2 < d1+L: continue
            r = rows[i]
            new = r[:d1] + r[d2:d2+L] + r[d1+L:d2] + r[d1:d1+L] + r[d2+L:]
            if new == r: continue
            newrows[i] = new
        elif mv < 0.85:
            i = rnd.randrange(N); j = rnd.randrange(N)
            if i == j: continue
            d = rnd.randrange(days)
            L = rnd.choice((1,1,1,2,2,3,4,7)) if mv < 0.8 else rnd.randrange(1, days)
            d2 = min(days, d+L)
            oi, oj = rows[i], rows[j]
            if oi[d:d2] == oj[d:d2]: continue
            newrows[i] = oi[:d] + oj[d:d2] + oi[d2:]; newrows[j] = oj[:d] + oi[d:d2] + oj[d2:]
        else:
            # swap two separate single days between two nurses
            i = rnd.randrange(N); j = rnd.randrange(N)
            if i == j: continue
            d1 = rnd.randrange(days); d2 = rnd.randrange(days)
            if d1 == d2: continue
            oi, oj = list(rows[i]), list(rows[j])
            if oi[d1] == oj[d1] or oi[d2] == oj[d2]: continue
            oi[d1], oj[d1] = oj[d1], oi[d1]; oi[d2], oj[d2] = oj[d2], oi[d2]
            newrows[i] = ''.join(oi); newrows[j] = ''.join(oj)
        delta = 0; newnc = {}
        for i, r in newrows.items():
            c = ncost(nurses[i], r); newnc[i] = c; delta += c - nc[i]
        if delta >= M: continue
        touched = {}
        for i, r in newrows.items():
            o = rows[i]
            for d in range(days):
                a = o[d]; b = r[d]
                if a == b: continue
                if a != '.':
                    k = (d, SI[a]); x = touched.get(k)
                    if x is None: x = touched[k] = list(cnt[d][SI[a]])
                    x[0]-=1; x[1]-=isrn[i]; x[2]-=issen[i]
                if b != '.':
                    k = (d, SI[b]); x = touched.get(k)
                    if x is None: x = touched[k] = list(cnt[d][SI[b]])
                    x[0]+=1; x[1]+=isrn[i]; x[2]+=issen[i]
        for (d,s),x in touched.items():
            delta += ccost(x,s) - ccost(cnt[d][s],s)
        if delta <= 0 or rnd.random() < math.exp(-delta/T):
            for i, r in newrows.items(): rows[i] = r; nc[i] = newnc[i]
            for (d,s),x in touched.items(): cnt[d][s] = x
            total += delta
            if total < best:
                best = total; bestrows = list(rows)
    ros = {'roster': {nurses[i]['id']: bestrows[i] for i in range(N)}}
    try: p = evaluate(ward, ros)
    except Exception: p = None
    return best, p, ros, it

if __name__ == '__main__':
    wname = sys.argv[1]; secs = float(sys.argv[2]); seed = int(sys.argv[3])
    T0 = float(os.environ.get('T0', 40)); T1 = float(os.environ.get('T1', 1))
    rounds = int(os.environ.get('ROUNDS', 1))
    for r in range(rounds):
        best, p, ros, it = solve(wname, secs, seed + r, T0, T1)
        ok = save_if_better(wname, ros, p)
        print(time.strftime('%H:%M:%S'), wname, 'round', r, 'internal', best, 'checker', p, 'iters', it, 'saved', ok, flush=True)

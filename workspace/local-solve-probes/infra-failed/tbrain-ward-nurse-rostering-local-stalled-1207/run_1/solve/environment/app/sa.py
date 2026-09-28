import json, sys, random, math, time, os
sys.path.insert(0, '/app/tools')
from check_roster import evaluate

M = 2000
def load(w):
    return json.load(open(f'/app/wards/{w}.json'))

def make(ward):
    days = ward['days']; H = ward['shift_hours']; W = ward['weights']; R = ward['rules']
    maxc = R['max_consecutive_days']; rest = R['rest_days_after_nights']; maxw = R['max_weekends']
    nurses = ward['nurses']
    def ncost(n, row):
        c = 0
        for d in n['leave']:
            if row[d] != '.': c += M
        c += M * (row.count('NE') + row.count('NL') + row.count('LE'))
        run = 0
        for ch in row:
            if ch != '.':
                run += 1
                if run > maxc: c += M
            else: run = 0
        for d in range(days - 1):
            if row[d] == 'N' and row[d+1] != 'N':
                for k in range(d+1, min(days, d+1+rest)):
                    if row[k] != '.': c += M
        worked = row.count('E')*H['E'] + row.count('L')*H['L'] + row.count('N')*H['N']
        if worked < n['min_hours']: c += W['hour_under']*(n['min_hours']-worked)
        if worked > n['max_hours']: c += W['hour_over']*(worked-n['max_hours'])
        nn = row.count('N')
        if nn > n['max_nights']: c += W['night_over']*(nn-n['max_nights'])
        wk = 0
        for sat in range(5, days, 7):
            a = row[sat] != '.'; b = sat+1 < days and row[sat+1] != '.'
            if a or b: wk += 1
            if sat+1 < days and a != b: c += W['split_weekend']
        if wk > maxw: c += W['weekend_over']*(wk-maxw)
        for d in range(1, days-1):
            if row[d] != '.' and row[d-1] == '.' and row[d+1] == '.': c += W['lone_day']
        for req in n['requests']:
            d, want = req['day'], req['off']
            if want == 'day':
                if row[d] != '.': c += W['request']
            elif row[d] == want: c += W['request']
        return c
    return ncost

def cover_cost(ward, cnt):
    # cnt: (tot, rn, sen)
    W = ward['weights']; c = 0
    out = {}
    return None

def solve(wname, seconds, seed):
    ward = load(wname); rnd = random.Random(seed)
    days = ward['days']; nurses = ward['nurses']; N = len(nurses)
    ncost = make(ward); W = ward['weights']; cov = ward['cover']
    grade = [n['grade'] for n in nurses]
    isrn = [g != 'HCA' for g in grade]; issen = [g == 'senior' for g in grade]
    try:
        if os.environ.get('FRESH'): raise Exception
        cur = json.load(open(f'/app/rosters/{wname}.json'))['roster']
        rows = [cur[n['id']] for n in nurses]
    except Exception:
        rows = ['.'*days for _ in nurses]
    # counts[d][s] = [tot, rn, sen]
    SI = {'E':0,'L':1,'N':2}
    cnt = [[[0,0,0] for _ in range(3)] for _ in range(days)]
    for i,r in enumerate(rows):
        for d,ch in enumerate(r):
            if ch != '.':
                x = cnt[d][SI[ch]]; x[0]+=1; x[1]+=isrn[i]; x[2]+=issen[i]
    covs = [cov['E'], cov['L'], cov['N']]
    def ccost(x, s):
        cv = covs[s]; c = 0
        if x[0] < cv['minimum']: c += M*(cv['minimum']-x[0])
        if x[1] < cv['registered']: c += M*(cv['registered']-x[1])
        if x[2] < 1: c += M
        if x[0] < cv['preferred']: c += W['short_of_preferred']*(cv['preferred']-x[0])
        return c
    nc = [ncost(nurses[i], rows[i]) for i in range(N)]
    total = sum(nc) + sum(ccost(cnt[d][s], s) for d in range(days) for s in range(3))
    best = total; bestrows = list(rows)
    T0 = float(os.environ.get("T0", 60)); T1 = float(os.environ.get("T1", 0.5))
    t_start = time.time(); it = 0
    T = T0
    codes = 'ELN.'
    while True:
        it += 1
        if it & 1023 == 0:
            el = time.time() - t_start
            if el > seconds: break
            T = T0 * (T1/T0) ** (el/seconds)
        mv = rnd.random()
        if mv < 0.45:
            # change a segment of one nurse to one code (length 1-3)
            i = rnd.randrange(N); d = rnd.randrange(days); L = rnd.choice((1,1,1,2,2,3))
            d2 = min(days, d+L); ch = rnd.choice(codes)
            old = rows[i]; new = old[:d] + ch*(d2-d) + old[d2:]
            if new == old: continue
            nnew = ncost(nurses[i], new)
            delta = nnew - nc[i]
            touched = {}
            for dd in range(d, d2):
                for s in range(3):
                    touched[(dd,s)] = list(cnt[dd][s])
                o = old[dd]
                if o != '.':
                    x = touched[(dd,SI[o])]; x[0]-=1; x[1]-=isrn[i]; x[2]-=issen[i]
                if ch != '.':
                    x = touched[(dd,SI[ch])]; x[0]+=1; x[1]+=isrn[i]; x[2]+=issen[i]
            for (dd,s),x in touched.items():
                delta += ccost(x,s) - ccost(cnt[dd][s],s)
            if delta <= 0 or rnd.random() < math.exp(-delta/T):
                rows[i] = new; nc[i] = nnew; total += delta
                for (dd,s),x in touched.items(): cnt[dd][s] = x
        else:
            # swap segment between two nurses
            i = rnd.randrange(N); j = rnd.randrange(N)
            if i == j: continue
            d = rnd.randrange(days)
            L = rnd.choice((1,1,1,2,2,3,4,7)) if mv < 0.9 else rnd.randrange(1, days)
            d2 = min(days, d+L)
            oi, oj = rows[i], rows[j]
            if oi[d:d2] == oj[d:d2]: continue
            ni = oi[:d] + oj[d:d2] + oi[d2:]; nj = oj[:d] + oi[d:d2] + oj[d2:]
            ci = ncost(nurses[i], ni); cj = ncost(nurses[j], nj)
            delta = ci + cj - nc[i] - nc[j]
            touched = {}
            if isrn[i] != isrn[j] or issen[i] != issen[j]:
                for dd in range(d, d2):
                    a, b = oi[dd], oj[dd]
                    if a == b: continue
                    for s in range(3):
                        if (dd,s) not in touched: touched[(dd,s)] = list(cnt[dd][s])
                    if a != '.':
                        x = touched[(dd,SI[a])]; x[1] += isrn[j]-isrn[i]; x[2] += issen[j]-issen[i]
                    if b != '.':
                        x = touched[(dd,SI[b])]; x[1] += isrn[i]-isrn[j]; x[2] += issen[i]-issen[j]
                for (dd,s),x in touched.items():
                    delta += ccost(x,s) - ccost(cnt[dd][s],s)
            if delta <= 0 or rnd.random() < math.exp(-delta/T):
                rows[i] = ni; rows[j] = nj; nc[i] = ci; nc[j] = cj; total += delta
                for (dd,s),x in touched.items(): cnt[dd][s] = x
        if total < best:
            best = total; bestrows = list(rows)
    ros = {'roster': {nurses[i]['id']: bestrows[i] for i in range(N)}}
    try:
        p = evaluate(ward, ros)
    except Exception as e:
        p = None
    return best, p, ros, it

def save_if_better(wname, ros, p):
    path = f'/app/rosters/{wname}.json'
    ward = load(wname)
    try:
        oldp = evaluate(ward, json.load(open(path)))
    except Exception:
        oldp = None
    if p is not None and (oldp is None or p < oldp):
        tmp = path + '.tmp'
        json.dump(ros, open(tmp, 'w'))
        os.replace(tmp, path)
        return True
    return False

if __name__ == '__main__':
    wname = sys.argv[1]; secs = float(sys.argv[2]); seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    best, p, ros, it = solve(wname, secs, seed)
    ok = save_if_better(wname, ros, p)
    print(wname, 'internal', best, 'checker', p, 'iters', it, 'saved', ok, flush=True)

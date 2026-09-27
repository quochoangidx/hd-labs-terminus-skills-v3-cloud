import json, sys, random, math, time, os
sys.path.insert(0, '/app/tools'); sys.path.insert(0, '/app/planner')
import check_roster, plan_ward
H = 2000
def run(wname, secs, seed):
    ward = json.load(open(f'/app/wards/{wname}.json'))
    rnd = random.Random(seed)
    D = ward['days']; nurses = ward['nurses']; N = len(nurses)
    hours = ward['shift_hours']; w = ward['weights']; R = ward['rules']
    MC = R['max_consecutive_days']; RA = R['rest_days_after_nights']; MW = R['max_weekends']
    memo = [dict() for _ in range(N)]
    leave = [set(n['leave']) for n in nurses]
    def ncost(i, row):
        m = memo[i]
        v = m.get(row)
        if v is not None: return v
        n = nurses[i]; c = 0
        for d in leave[i]:
            if row[d] != '.': c += H
        c += H * (row.count('NE') + row.count('NL') + row.count('LE'))
        run_ = 0
        for ch in row:
            if ch != '.':
                run_ += 1
                if run_ > MC: c += H
            else: run_ = 0
        for d in range(D - 1):
            if row[d] == 'N' and row[d+1] != 'N':
                for k in range(d+1, min(D, d+1+RA)):
                    if row[k] != '.': c += H
        wk = row.count('E')*hours['E'] + row.count('L')*hours['L'] + row.count('N')*hours['N']
        if wk < n['min_hours']: c += w['hour_under']*(n['min_hours']-wk)
        if wk > n['max_hours']: c += w['hour_over']*(wk-n['max_hours'])
        nn = row.count('N')
        if nn > n['max_nights']: c += w['night_over']*(nn-n['max_nights'])
        we = 0
        for sat in range(5, D, 7):
            a = row[sat] != '.'; b = sat+1 < D and row[sat+1] != '.'
            if a or b: we += 1
            if sat+1 < D and a != b: c += w['split_weekend']
        if we > MW: c += w['weekend_over']*(we-MW)
        for d in range(1, D-1):
            if row[d] != '.' and row[d-1] == '.' and row[d+1] == '.': c += w['lone_day']
        for rq in n['requests']:
            d, want = rq['day'], rq['off']
            if want == 'day':
                if row[d] != '.': c += w['request']
            elif row[d] == want: c += w['request']
        if len(m) > 200000: m.clear()
        m[row] = c
        return c
    isrn = [n['grade'] in ('RN','senior') for n in nurses]
    issen = [n['grade'] == 'senior' for n in nurses]
    cov = ward['cover']
    SI = {'E':0,'L':1,'N':2}
    def ccost(cnt):  # cnt: [tot,rn,sen] per shift list of 3
        c = 0
        for s in 'ELN':
            t, r, se = cnt[SI[s]]; nd = cov[s]
            c += H*(max(0, nd['minimum']-t) + max(0, nd['registered']-r) + max(0, 1-se))
            if t < nd['preferred']: c += w['short_of_preferred']*(nd['preferred']-t)
        return c
    init = plan_ward.plan(ward)['roster']
    if os.environ.get('WARM') and os.path.exists(f'/app/rosters/{wname}.json'):
        init = json.load(open(f'/app/rosters/{wname}.json'))['roster']
    rows = [init[n['id']] for n in nurses]
    cnt = [[[0,0,0] for _ in range(3)] for _ in range(D)]
    for i in range(N):
        for d in range(D):
            ch = rows[i][d]
            if ch != '.':
                k = SI[ch]; cnt[d][k][0]+=1; cnt[d][k][1]+=isrn[i]; cnt[d][k][2]+=issen[i]
    nc = [ncost(i, rows[i]) for i in range(N)]
    dc = [ccost(cnt[d]) for d in range(D)]
    cur = sum(nc)+sum(dc)
    best = cur; bestrows = list(rows)
    def apply(i, d, old, new):
        if old != '.':
            k = SI[old]; cnt[d][k][0]-=1; cnt[d][k][1]-=isrn[i]; cnt[d][k][2]-=issen[i]
        if new != '.':
            k = SI[new]; cnt[d][k][0]+=1; cnt[d][k][1]+=isrn[i]; cnt[d][k][2]+=issen[i]
    T0, T1 = float(os.environ.get('T0','60')), float(os.environ.get('T1','1'))
    t0 = time.time(); it = 0; T = T0
    codes = 'ELN.'
    while True:
        it += 1
        if it & 1023 == 0:
            el = time.time() - t0
            if el > secs: break
            T = T0 * (T1/T0) ** (el/secs)
        mv = rnd.random()
        if mv < 0.4:
            # change a block of 1-3 days for one nurse
            i = rnd.randrange(N); L = rnd.choice((1,1,2,2,3)); d0 = rnd.randrange(D-L+1)
            row = rows[i]
            if rnd.random() < 0.5:
                c = rnd.choice(codes); seg = c*L
            else:
                seg = ''.join(rnd.choice(codes) for _ in range(L))
            if row[d0:d0+L] == seg: continue
            nrow = row[:d0]+seg+row[d0+L:]
            nnc = ncost(i, nrow)
            dd = nnc - nc[i]
            newdc = {}
            for d in range(d0, d0+L):
                apply(i, d, row[d], nrow[d])
                x = ccost(cnt[d]); newdc[d] = x; dd += x - dc[d]
            if dd <= 0 or rnd.random() < math.exp(-dd/T):
                rows[i] = nrow; nc[i] = nnc
                for d, x in newdc.items(): dc[d] = x
                cur += dd
            else:
                for d in range(d0, d0+L): apply(i, d, nrow[d], row[d])
        else:
            # swap segment between two nurses
            i = rnd.randrange(N); j = rnd.randrange(N)
            if i == j: continue
            L = rnd.choice((1,1,2,2,3,4,5,7)); d0 = rnd.randrange(D-L+1)
            ri, rj = rows[i], rows[j]
            si, sj = ri[d0:d0+L], rj[d0:d0+L]
            if si == sj: continue
            ni = ri[:d0]+sj+ri[d0+L:]; nj = rj[:d0]+si+rj[d0+L:]
            ci = ncost(i, ni); cj = ncost(j, nj)
            dd = ci + cj - nc[i] - nc[j]
            need_cov = not (isrn[i]==isrn[j] and issen[i]==issen[j])
            newdc = {}
            if need_cov:
                for d in range(d0, d0+L):
                    if ri[d] != rj[d]:
                        apply(i, d, ri[d], rj[d]); apply(j, d, rj[d], ri[d])
                        x = ccost(cnt[d]); newdc[d] = x; dd += x - dc[d]
            if dd <= 0 or rnd.random() < math.exp(-dd/T):
                rows[i] = ni; rows[j] = nj; nc[i] = ci; nc[j] = cj
                for d, x in newdc.items(): dc[d] = x
                cur += dd
            elif need_cov:
                for d in newdc:
                    apply(i, d, rj[d], ri[d]); apply(j, d, ri[d], rj[d])
        if cur < best:
            best = cur; bestrows = list(rows)
    out = {'roster': {nurses[i]['id']: bestrows[i] for i in range(N)}}
    try:
        p = check_roster.evaluate(ward, out)
    except check_roster.RosterError as e:
        p = None
    return p, best, out, it

def save(wname, p, out):
    path = f'/app/rosters/{wname}.json'
    old = None
    if os.path.exists(path):
        try:
            ward = json.load(open(f'/app/wards/{wname}.json'))
            old = check_roster.evaluate(ward, check_roster.load_roster(path))
        except Exception: old = None
    if p is not None and (old is None or p < old):
        tmp = path + '.tmp'
        json.dump(out, open(tmp, 'w')); os.replace(tmp, path)
        return True
    return False

def job(args):
    wname, secs, seed = args
    p, best, out, it = run(wname, secs, seed)
    return wname, seed, p, best, out, it

if __name__ == '__main__':
    import multiprocessing as mp
    wards = sys.argv[1].split(','); secs = float(sys.argv[2]); rounds = int(sys.argv[3])
    seed0 = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    tasks = [(wn, secs, seed0 + 1000*r + k) for r in range(rounds) for k, wn in enumerate(wards)]
    with mp.Pool(2) as pool:
        for wname, seed, p, best, out, it in pool.imap_unordered(job, tasks):
            s = save(wname, p, out)
            print(wname, seed, 'penalty', p, 'internal', best, 'iters', it, 'saved' if s else '', flush=True)

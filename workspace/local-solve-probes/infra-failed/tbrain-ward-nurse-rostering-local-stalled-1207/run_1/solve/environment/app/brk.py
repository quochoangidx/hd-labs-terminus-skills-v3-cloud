import json, sys
from collections import Counter
for w in sys.argv[1:]:
    ward = json.load(open(f'/app/wards/{w}.json')); ros = json.load(open(f'/app/rosters/{w}.json'))['roster']
    H = ward['shift_hours']; W = ward['weights']; days = ward['days']; C = Counter()
    for d in range(days):
        for s in 'ELN':
            k = sum(1 for r in ros.values() if r[d]==s)
            C['short'] += max(0, ward['cover'][s]['preferred']-k)*W['short_of_preferred']
    for n in ward['nurses']:
        r = ros[n['id']]; wk = sum(H[c] for c in r if c!='.')
        C['under'] += max(0,n['min_hours']-wk)*W['hour_under']; C['over'] += max(0,wk-n['max_hours'])*W['hour_over']
        C['nightover'] += max(0,r.count('N')-n['max_nights'])*W['night_over']
        ws=0
        for sat in range(5,days,7):
            a=r[sat]!='.'; b=r[sat+1]!='.'
            ws += a or b
            if a!=b: C['split']+=W['split_weekend']
        C['wkover'] += max(0,ws-ward['rules']['max_weekends'])*W['weekend_over']
        for d in range(1,days-1):
            if r[d]!='.' and r[d-1]=='.' and r[d+1]=='.': C['lone']+=W['lone_day']
        for q in n['requests']:
            if (q['off']=='day' and r[q['day']]!='.') or r[q['day']]==q['off']: C['req']+=W['request']
    print(w, sum(C.values()), dict(C))
    for n in ward['nurses']: print(' ', n['id'], n['grade'], n['min_hours'], n['max_hours'], n['max_nights'], ros[n['id']], sum(H[c] for c in ros[n['id']] if c!='.'))

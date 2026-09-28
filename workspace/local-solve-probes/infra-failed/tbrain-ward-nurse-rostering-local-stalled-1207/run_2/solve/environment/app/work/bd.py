import json,sys
from collections import Counter
for wn in sys.argv[1:]:
    W=json.load(open(f'wards/{wn}.json')); r=json.load(open(f'rosters/{wn}.json'))['roster']
    D=W['days'];w=W['weights'];H=W['shift_hours'];c=Counter()
    for d in range(D):
        for s in 'ELN':
            k=sum(1 for n in W['nurses'] if r[n['id']][d]==s); p=W['cover'][s]['preferred']
            if k<p: c['short']+=w['short_of_preferred']*(p-k)
    tot_min=sum(n['min_hours'] for n in W['nurses']);tot_max=sum(n['max_hours'] for n in W['nurses'])
    for n in W['nurses']:
        row=r[n['id']];h=sum(H[x] for x in row if x!='.')
        if h<n['min_hours']:c['under']+=w['hour_under']*(n['min_hours']-h)
        if h>n['max_hours']:c['over']+=w['hour_over']*(h-n['max_hours'])
        nn=row.count('N')
        if nn>n['max_nights']:c['nights']+=w['night_over']*(nn-n['max_nights'])
        wk=0
        for sat in range(5,D,7):
            a=row[sat]!='.';b=row[sat+1]!='.'
            wk+=a or b
            if a!=b:c['split']+=w['split_weekend']
        if wk>2:c['wkover']+=w['weekend_over']*(wk-2)
        for d in range(1,D-1):
            if row[d]!='.' and row[d-1]=='.' and row[d+1]=='.':c['lone']+=w['lone_day']
        for q in n['requests']:
            if (q['off']=='day' and row[q['day']]!='.') or row[q['day']]==q['off']:c['req']+=w['request']
    need=sum(W['cover'][s]['preferred']*H[s] for s in 'ELN')*D; needmin=sum(W['cover'][s]['minimum']*H[s] for s in 'ELN')*D
    print(wn,sum(c.values()),dict(c),'hours minsum',tot_min,'maxsum',tot_max,'pref-hours',need,'min-cover-hours',needmin)

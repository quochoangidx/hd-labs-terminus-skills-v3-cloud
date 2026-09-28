import json,sys
for wn in sys.argv[1:]:
    w=json.load(open(f'wards/{wn}.json')); r=json.load(open(f'rosters/{wn}.json'))['roster']
    D=w['days'];H=w['shift_hours'];W=w['weights']
    short=0
    for d in range(D):
        for s in 'ELN':
            c=sum(1 for n in r.values() if n[d]==s); short+=max(0,w['cover'][s]['preferred']-c)
    tot={'short':short*30}
    hu=ho=no=sp=wo=lo=rq=0
    for n in w['nurses']:
        row=r[n['id']];h=sum(H[x] for x in row if x!='.')
        hu+=max(0,n['min_hours']-h)*4; ho+=max(0,h-n['max_hours'])*6; no+=max(0,row.count('N')-n['max_nights'])*20
        wk=0
        for s in range(5,D,7):
            a=row[s]!='.';b=row[s+1]!='.'
            wk+=a or b; sp+=30*(a!=b)
        wo+=40*max(0,wk-2)
        lo+=15*sum(1 for d in range(1,D-1) if row[d]!='.' and row[d-1]=='.' and row[d+1]=='.')
        for q in n['requests']:
            if (q['off']=='day' and row[q['day']]!='.') or row[q['day']]==q['off']: rq+=25
        print(n['id'],n['grade'],row,h,n['min_hours'],n['max_hours'])
    tot.update(hu=hu,ho=ho,no=no,sp=sp,wo=wo,lo=lo,rq=rq)
    cap=sum(n['max_hours'] for n in w['nurses']); mn=sum(n['min_hours'] for n in w['nurses'])
    need={s:sum(w['cover'][s]['preferred']*H[s] for _ in range(D)) for s in 'ELN'}
    print(wn,tot,'minsum',mn,'maxsum',cap,'pref hours',sum(need.values()), 'min hours', sum(w['cover'][s]['minimum']*H[s]*D for s in 'ELN'))

import json
for d in ['day-1','day-2','day-3','day-4']:
    day=json.load(open(f'days/{d}.json')); plan=json.load(open(f'plans/{d}.json'))
    S={s['id']:s for s in day['stands']}; T={t['id']:t for t in day['turns']}
    idx={s['id']:i for i,s in enumerate(day['stands'])}
    where={t:s for s,l in plan['stands'].items() for t in l}
    busc=sum(day['bus_cost_per_passenger']*(T[t]['pax_in']+T[t]['pax_out']) for t,s in where.items() if S[s]['remote'])
    nrem=sum(1 for t,s in where.items() if S[s]['remote'])
    walk=sum(tr['passengers']*day['walk_metres'][idx[where[tr['from']]]][idx[where[tr['to']]]] for tr in day['transfers'])
    # remote turns by type
    import collections
    c=collections.Counter((T[t]['size'],T[t]['international']) for t,s in where.items() if S[s]['remote'])
    print(d,busc,nrem,walk,dict(c))

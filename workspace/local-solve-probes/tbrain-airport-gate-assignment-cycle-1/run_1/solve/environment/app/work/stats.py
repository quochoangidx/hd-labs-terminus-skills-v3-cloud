import json,sys,collections
for d in ['day-1','day-2','day-3','day-4']:
    day=json.load(open(f'days/{d}.json'))
    S=day['stands'];T=day['turns']
    print(d,'stands',len(S),'turns',len(T),'transfers',len(day['transfers']),'wing',len(day['wingtip_pairs']),'buf',day['buffer_minutes'],'bus',day['bus_cost_per_passenger'])
    print(' stands by (pier,size,intl):',collections.Counter((s['pier'],s['size'],s['international']) for s in S))
    print(' turns by (size,intl):',collections.Counter((t['size'],t['international']) for t in T))
    print(' extra keys', set(day.keys()))
    w=day['walk_metres']; print(' walk sample', w[0][:5], 'diag', [w[i][i] for i in range(len(S))][:8], 'max',max(max(r) for r in w))
    print(' pax range', min(t['pax_in']+t['pax_out'] for t in T), max(t['pax_in']+t['pax_out'] for t in T))
    print(' transfer pax total', sum(x['passengers'] for x in day['transfers']))

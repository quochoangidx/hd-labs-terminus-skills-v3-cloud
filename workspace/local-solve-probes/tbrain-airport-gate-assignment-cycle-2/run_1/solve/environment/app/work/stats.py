import json,sys
from collections import Counter
for d in ['day-1','day-2','day-3','day-4']:
    day=json.load(open(f'days/{d}.json'))
    S=day['stands'];T=day['turns']
    print(d,'stands',len(S),'turns',len(T),'transfers',len(day['transfers']),'buf',day['buffer_minutes'],'bus',day['bus_cost_per_passenger'],'wing',len(day['wingtip_pairs']))
    print(' stand types',Counter((s['pier'],s['size'],s['international'],s['remote']) for s in S))
    print(' turn types',Counter((t['size'],t['international']) for t in T))
    W=day['walk_metres']
    print(' diag',[W[i][i] for i in range(len(S))][:40])
    print(' row0',W[0])
    print(' wing',day['wingtip_pairs'])
    print(' minmax time',min(t['arrive'] for t in T),max(t['depart'] for t in T), 'avg dur',sum(t['depart']-t['arrive'] for t in T)/len(T))
    print(' pax transfers sum',sum(x['passengers'] for x in day['transfers']))
    print(' keys',list(day.keys()))

import json,sys,collections
for d in ['day-1','day-2','day-3','day-4']:
    day=json.load(open(f'days/{d}.json'))
    S=day['stands'];T=day['turns']
    print(d,len(S),len(T),len(day['transfers']),day['wingtip_pairs'][:5],len(day['wingtip_pairs']),day['bus_cost_per_passenger'],day['buffer_minutes'])
    print(collections.Counter((s['pier'],s['size'],s['international']) for s in S))
    print(collections.Counter((t['size'],t['international']) for t in T))
    print([r[:6] for r in day['walk_metres'][:3]])
    print(sum(t['pax_in']+t['pax_out'] for t in T)/len(T), sum(x['passengers'] for x in day['transfers']))
    print(set(day.keys()))

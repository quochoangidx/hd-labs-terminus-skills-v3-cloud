for d in day-1 day-2 day-3 day-4; do python3 planner/plan_day.py days/$d.json plans/$d.json && python3 tools/check_plan.py days/$d.json plans/$d.json; done
python3 -c "
import json
for d in ['day-1','day-2','day-3','day-4']:
    day=json.load(open(f'days/{d}.json')); w=day['walk_metres']; n=len(w)
    print(d,'sym',all(w[i][j]==w[j][i] for i in range(n) for j in range(n)), 'wing',day['wingtip_pairs'])
    print([ (s['id'],w[i][i]) for i,s in enumerate(day['stands']) if w[i][i]!=40])
    print('turn keys', set(k for t in day['turns'] for k in t), 'tr keys', set(k for t in day['transfers'] for k in t))
    ids=[t['id'] for t in day['turns']]; print('dupe ids', len(ids)-len(set(ids)))
"

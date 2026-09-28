import json, sys, os, random
sys.path.insert(0,'tests')
from check_plan import evaluate, load_plan
def mine(site, plan):
    prods={p['id']:p for p in site['products']}
    c=0; made={}
    for r in plan['runs']:
        c+=prods[r['product']]['lines'][r['line']]['setup_cost']
        made[(r['product'],r['day'])]=made.get((r['product'],r['day']),0)+r['batches']
    for pid,p in prods.items():
        cum=p['initial_stock']
        for d in range(site['days']):
            cum+=made.get((pid,d),0)-p['demand'][d]
            c+= p['holding_cost']*cum if cum>0 else -p['backlog_cost']*cum
    return c
for sub in ['v01_edges_extra_keys','v02_empty_runs','v03_lfl_all','v04_minus_zero_day_unicode']:
    for f in sorted(os.listdir('submissions/'+sub)):
        if f.endswith('.json'):
            s=f[:-5]; site=json.load(open(f'tests/sites/{s}.json')); pl=load_plan(f'submissions/{sub}/{f}')
            print(sub,s,evaluate(site,pl),mine(site,pl))
# boundary: exactly 2,000,000 bytes and exactly-4300-digit float in ignored key
base=json.dumps({"runs":[],"x":float('0.'+'0'*4298+'1') if False else 0})
raw='{"runs":[],"x":0.'+'0'*4298+'1}'
os.makedirs('submissions/v05_boundaries',exist_ok=True)
raw=raw+' '*(2_000_000-len(raw))
open('submissions/v05_boundaries/kent.json','w').write(raw)
open('submissions/v05_boundaries/WHY.txt','w').write('VALID: exactly 2,000,000 bytes and a float with exactly 4300 digits in an ignored key\n')

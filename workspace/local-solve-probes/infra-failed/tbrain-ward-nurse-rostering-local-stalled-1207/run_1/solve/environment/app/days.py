import json, sys
for w in sys.argv[1:]:
    ward = json.load(open(f'/app/wards/{w}.json')); ros = json.load(open(f'/app/rosters/{w}.json'))['roster']
    for s in 'ELN':
        print(w, s, ward['cover'][s]['preferred'], ' '.join(str(sum(r[d]==s for r in ros.values())) for d in range(ward['days'])))

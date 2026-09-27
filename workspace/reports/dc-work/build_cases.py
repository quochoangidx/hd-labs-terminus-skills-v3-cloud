import json, glob
key = lambda e: (tuple(e['args']), e['stdin'], json.dumps(e['files'], sort_keys=True))
EXCLUDE = {"vfails_rotneg.json", "vfails_wrap70.json", "vfails_digitclamp.json", "vfails_arrayunsetnothing.json"}  # settled by the manual or the instruction
bad = set()
for f in glob.glob('vfails_*.json'):
    if f in EXCLUDE: continue
    for x in json.load(open(f)): bad.add(key(x))
allc = json.load(open('all_ok.json'))
out = []
for e in allc:
    if key(e) in bad: continue
    if not any(a in ('-e', '-f') for a in e['args']) and not e['files'] and '?' in e['stdin']: continue  # ? with the script itself on stdin
    out.append({"family": e["group"], "args": e["args"], "stdin": e["stdin"], "files": sorted(e["files"].items())})
json.dump(out, open('../../tasks/tbrain-gnu-dc-reimplementation/tests/cases.json', 'w'), indent=0)
from collections import Counter
print(len(out), sorted(Counter(c['family'] for c in out).items()))

cd /work
for m in line-cap-64 special-range-one-digit interval-one-digit bare-q-clears-status bre-dollar-before-alt-literal nes-together-drops-s question-delimiter-rejected; do
  python3 runcases.py sweeps.json cand-inputs.json /tmp/k-$m.json wp-mut/$m/app/pysed
  python3 -c "
import json,sys
r=json.load(open('/tmp/k-$m.json')); k={}
for f,rows in r.items():
    k[f]=sum(x['gnu']!=x['ref'] for x in rows)
print('$m', {f:v for f,v in k.items() if v})"
done

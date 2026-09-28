import json, subprocess, tempfile, os
def expand(t): return t if isinstance(t,str) else t['repeat']*t['count']+t.get('then','')
def static(args):
    return any(a.startswith('-') and (a in ('-','--') or a.startswith('--') or any(ch not in 'Els' for ch in a[1:])) for a in args)
rows=json.load(open('/w/missing.json')); inscope=[]
for r in rows:
    d=tempfile.mkdtemp()
    for n,t in r['files']:
        full=os.path.join(d,n); par=full if n.endswith('/') else os.path.dirname(full)
        os.makedirs(par,exist_ok=True)
        if n.endswith('/'): continue
        open(full,'w',encoding='latin-1').write(expand(t))
    kw=dict(capture_output=True,cwd=d,env={"LC_ALL":"C","PATH":"/usr/local/bin:/usr/bin:/bin"},timeout=60)
    sf=tempfile.mktemp(); open(sf,'w',encoding='latin-1').write(r['script'])
    if r['stdin']=='file':
        with open(sf,'rb') as fh: p=subprocess.run(['python3','/scope/ed.py']+r['args'],stdin=fh,**kw)
    else: p=subprocess.run(['python3','/scope/ed.py']+r['args'],input=r['script'].encode('latin-1'),**kw)
    tags={x[6:] for x in p.stderr.decode('latin-1').splitlines() if x.startswith('SCOPE:')}
    if static(r['args']): tags.add('static-args')
    if any(len(expand(t).split('\n'))>41 for _,t in r['files']): tags.add('many-lines')
    if not tags: inscope.append(r)
print(len(rows),'missing;',len(inscope),'look in scope')
for r in inscope: print(r['src'], r['args'], r['stdin'], repr(r['script']), [(n, expand(t)[:40]) for n,t in r['files']])
json.dump(inscope,open('/w/inscope_missing.json','w'))

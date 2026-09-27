import json, os, subprocess, tempfile, shutil, glob, collections, sys
CD=sys.argv[1]
fx=json.load(open(CD+'/fixtures.json'))
def txt(t): return t if isinstance(t,str) else t['repeat']*t['count']+t.get('then','')
out={}
for f in sorted(glob.glob(CD+"/*.jsonl")):
    fam=os.path.basename(f)[:-6]
    for i,l in enumerate(open(f)):
        r=json.loads(l)
        d=tempfile.mkdtemp()
        for n,t in fx[r['fixture']]:
            full=os.path.join(d,n)
            par=full if n.endswith('/') else os.path.dirname(full)
            os.makedirs(par,exist_ok=True)
            if n.endswith('/'): continue
            open(full,'w',encoding='latin-1').write(txt(t))
        sf=tempfile.mktemp(); open(sf,'w',encoding='latin-1').write(r['script'])
        env={"LC_ALL":"C","PATH":"/usr/bin:/bin:/usr/local/bin"}
        cmd=["python3","/scope/ed.py"]+r['args']
        if r['stdin']=='file':
            with open(sf,'rb') as fh: p=subprocess.run(cmd,stdin=fh,capture_output=True,cwd=d,env=env,timeout=60)
        else:
            p=subprocess.run(cmd,input=r['script'].encode('latin-1'),capture_output=True,cwd=d,env=env,timeout=60)
        tags=sorted({x[6:] for x in p.stderr.decode('latin-1').splitlines() if x.startswith('SCOPE:')})
        out[f"{fam}:{i}"]=tags
        shutil.rmtree(d)
json.dump(out,open(sys.argv[2],'w'),indent=0)
c=collections.Counter(); fams=collections.Counter(); tot=collections.Counter()
for k,v in out.items():
    tot[k.split(':')[0]]+=1
    if v: fams[k.split(':')[0]]+=1
    for t in v: c[t]+=1
print(c.most_common()); print({f:(fams[f],tot[f]) for f in tot})

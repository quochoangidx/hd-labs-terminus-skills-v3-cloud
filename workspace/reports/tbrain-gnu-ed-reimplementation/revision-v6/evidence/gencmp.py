import json, os, subprocess, tempfile, shutil, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, '/t')
import generated
REF = sys.argv[1] if len(sys.argv) > 1 else '/sol/pyed/ed.py'
def snap(p):
    r={}
    for root,ds,ns in os.walk(p):
        rel=os.path.relpath(root,p); pre='' if rel=='.' else rel+'/'
        for d in ds: r[pre+d+'/']=None
        for n in ns: r[pre+n]=open(os.path.join(root,n),'rb').read()
    return r
def run(cmd, c):
    d=tempfile.mkdtemp()
    for n,t in c['files']:
        open(os.path.join(d,n),'w',encoding='latin-1').write(t)
    sf=tempfile.mktemp(); open(sf,'w',encoding='latin-1').write(c['script'])
    env={"LC_ALL":"C","PATH":"/usr/bin:/bin:/usr/local/bin"}
    try:
        if c['stdin']=='file':
            with open(sf,'rb') as fh: p=subprocess.run(cmd+c['args'],stdin=fh,capture_output=True,cwd=d,env=env,timeout=20)
        else:
            p=subprocess.run(cmd+c['args'],input=c['script'].encode('latin-1'),capture_output=True,cwd=d,env=env,timeout=20)
        res=(p.stdout, p.returncode==0, snap(d))
    except subprocess.TimeoutExpired:
        res=('timeout',None,None)
    shutil.rmtree(d); os.unlink(sf)
    return res
cases=[(b,i,c) for b,cs in generated.generate().items() for i,c in enumerate(cs)]
def one(t):
    b,i,c=t
    g=run(['ed'],c); r=run(['python3',REF],c)
    return (b,i,c,g,r)
bad=[]; errs=0; STATS=[]
with ThreadPoolExecutor(8) as ex:
    for b,i,c,g,r in ex.map(one,cases):
        if g!=r: bad.append((b,i,c,g,r))
        if b'?' in (g[0] if isinstance(g[0],bytes) else b''): errs+=1
        q=(g[0].count(b'?\n') if isinstance(g[0],bytes) else -1); STATS.append((q, c['stdin'], len(c['script'].split(chr(10)))))
import collections
hist=collections.Counter()
print("cases",len(cases),"diff",len(bad),"with ? output",errs)
for b,i,c,g,r in bad[:15]:
    print("==",b,i,c['args'],c['stdin'],repr(c['script']))
    print("  files",c['files'])
    print("  gnu",g[0][:300] if g[0]!='timeout' else g, g[1], {k:(v[:60] if v else v) for k,v in (g[2] or {}).items()})
    print("  ref",r[0][:300] if r[0]!='timeout' else r, r[1], {k:(v[:60] if v else v) for k,v in (r[2] or {}).items()})
json.dump([[b,i] for b,i,*_ in bad],open('/w/gen_bad.json','w'))

import collections
print("errors per script", sorted(collections.Counter(min(q,5) for q,_,_ in STATS).items()))
print("file-stdin scripts", sum(1 for q,k,_ in STATS if k=='file'), "stopped early (q>=1)", sum(1 for q,k,_ in STATS if k=='file' and q>=1))

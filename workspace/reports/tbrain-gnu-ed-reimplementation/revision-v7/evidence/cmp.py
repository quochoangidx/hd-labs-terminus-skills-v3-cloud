# usage inside container: python3 cmp.py '<json list of [args, files{name:text}, script, stdin]>'
import json, os, subprocess, sys, tempfile, shutil
def snap(p):
    r={}
    for root,ds,ns in os.walk(p):
        for n in sorted(ns):
            r[os.path.relpath(os.path.join(root,n),p)]=open(os.path.join(root,n),'rb').read()
    return r
def run(cmd, args, files, script, kind):
    d=tempfile.mkdtemp()
    for n,t in files.items():
        open(os.path.join(d,n),'w',encoding='latin-1').write(t)
    sf=tempfile.mktemp(); open(sf,'w',encoding='latin-1').write(script)
    env={"LC_ALL":"C","PATH":"/usr/bin:/bin:/usr/local/bin"}
    if kind=='file':
        with open(sf,'rb') as fh: p=subprocess.run(cmd+args,stdin=fh,capture_output=True,cwd=d,env=env,timeout=30)
    else:
        p=subprocess.run(cmd+args,input=script.encode('latin-1'),capture_output=True,cwd=d,env=env,timeout=30)
    s=snap(d); shutil.rmtree(d)
    return p.stdout, p.returncode, s
cands = [["python3", "/sol/pyed/ed.py"]]
for case in json.load(open(sys.argv[1])):
    args, files, script, kind = case
    g=run(["ed"],args,files,script,kind)
    for c in cands:
        r=run(c,args,files,script,kind)
        same = (g[0],g[1]==0,g[2])==(r[0],r[1]==0,r[2])
        print("SAME" if same else "DIFF", repr(script)[:70], args, kind)
        print("  gnu:", g[0][:200], g[1], {k:v[:80] for k,v in g[2].items()})
        if not same: print("  ref:", r[0][:200], r[1], {k:v[:80] for k,v in r[2].items()})

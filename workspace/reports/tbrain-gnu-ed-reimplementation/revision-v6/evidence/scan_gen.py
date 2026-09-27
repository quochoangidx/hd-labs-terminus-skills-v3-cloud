import sys, subprocess, tempfile, os, collections
sys.path.insert(0,'/t'); import generated
c=collections.Counter(); n=0
for b,cs in generated.generate().items():
  for case in cs:
    d=tempfile.mkdtemp()
    for fn,t in case['files']: open(os.path.join(d,fn),'w').write(t)
    p=subprocess.run(['python3','/scope/ed.py']+case['args'],input=case['script'].encode(),capture_output=True,cwd=d,env={"LC_ALL":"C","PATH":"/usr/local/bin:/usr/bin:/bin"})
    tags={x[6:] for x in p.stderr.decode().splitlines() if x.startswith('SCOPE:')}
    for t in tags: c[t]+=1
    if tags and n<5: print(tags, repr(case['script'][:200])); n+=1
print(c)

import json, sys
sys.argv=[sys.argv[0]]+sys.argv[1:]
exec(open('/e/grade_all.py').read().split('def one(c):')[0].split('TESTS, CAND, OUT = sys.argv[1:4]')[0])
import os, subprocess, tempfile, shutil
src=open('/e/grade_all.py').read()
ns={}
exec(src[src.index('def snap'):src.index('def one(c):')], globals())
diffs=json.load(open(sys.argv[1])); CAND=sys.argv[2]
for d in diffs:
    lines=d['script'].split('\n')[:-1]
    for k in range(1,len(lines)+1):
        c=dict(d); c['script']='\n'.join(lines[:k])+'\n'
        g=run(['ed'],c); r=run(['python3',CAND],c)
        if g[0]!=r[0] or g[1]!=r[1] or g[2]!=r[2]:
            print(d['id'], d['args'], d['stdin'], 'line', repr(lines[k-1]), '| prefix', repr('\n'.join(lines[max(0,k-4):k-1]))[:120])
            print('    gnu', repr(g[0][-80:]), g[1], ' cand', repr(r[0][-80:]), r[1]); break
    else:
        print(d['id'], 'no prefix diverges (EOF?)', repr(d['gnu'][0][-60:]), repr(d['cand'][0][-60:]))

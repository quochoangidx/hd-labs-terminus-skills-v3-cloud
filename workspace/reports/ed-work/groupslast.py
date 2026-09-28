import os, shutil
d="variants/groupslast/pyed"; shutil.rmtree("variants/groupslast", ignore_errors=True); shutil.copytree("../../tasks/tbrain-gnu-ed-reimplementation/solution/pyed", d)
p=os.path.join(d,"posixre.py"); s=open(p).read()
a='''            if best is None or end > best[0]:'''
assert a in s; open(p,"w").write(s.replace(a,'''            if best is None or end >= best[0]:'''))

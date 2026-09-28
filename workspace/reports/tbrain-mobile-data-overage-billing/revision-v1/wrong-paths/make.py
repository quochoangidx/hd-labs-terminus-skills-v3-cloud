"""Build one wrong-path patch per account-string mutant: the reference fix plus one edit to statement.py."""
import os, shutil, subprocess, sys, tempfile
TASK, OUT = sys.argv[1], sys.argv[2]
OLD = '"account": usage["account"]'
MUTANTS = {
    "f1-account-upper": 'usage["account"].upper()',
    "s1-account-lower": 'usage["account"].lower()',
    "s2-account-strip": 'usage["account"].strip()',
    "s3-account-trunc-32": 'usage["account"][:32]',
    "s4-account-ascii-only": 'usage["account"].encode("ascii", "ignore").decode()',
    "s5-account-empty-default": '(usage["account"] or "UNKNOWN")',
    "s6-account-quotes-dropped": 'usage["account"].replace(chr(34), "").replace(chr(92), "")',
    "s7-account-space-collapsed": '" ".join(usage["account"].split())',
    "s8-account-title": 'usage["account"].title()',
}
os.makedirs(OUT, exist_ok=True)
for name, expr in MUTANTS.items():
    w = tempfile.mkdtemp()
    shutil.copytree(f"{TASK}/environment/app", f"{w}/orig/app")
    shutil.copytree(f"{TASK}/environment/app", f"{w}/mut/app")
    subprocess.run(["git", "apply", f"{os.path.abspath(TASK)}/solution/fix.patch"], cwd=f"{w}/mut", check=True)
    p = f"{w}/mut/app/src/usagebill/statement.py"
    s = open(p).read(); assert OLD in s
    open(p, "w").write(s.replace(OLD, f'"account": {expr}'))
    subprocess.run([sys.executable, "workspace/tools/mkpatch.py", f"{w}/orig", f"{w}/mut", f"{OUT}/{name}.patch"], check=True)
    print(name)

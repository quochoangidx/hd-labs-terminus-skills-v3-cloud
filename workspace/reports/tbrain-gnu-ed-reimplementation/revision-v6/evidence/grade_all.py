"""Run every case (committed + generated) through GNU ed and a candidate; list all diffs.
usage (in verifier image): python3 grade_all.py /tests /cand/pyed/ed.py out.json"""
import json, os, sys, subprocess, tempfile, shutil
from concurrent.futures import ThreadPoolExecutor
TESTS, CAND, OUT = sys.argv[1:4]
sys.path.insert(0, TESTS)
import generated
CD = os.path.join(TESTS, "cases")
roster = json.load(open(os.path.join(CD, "roster.json"))); fx = json.load(open(os.path.join(CD, "fixtures.json")))
cases = []
for fam in roster["families"]:
    for i, l in enumerate(open(os.path.join(CD, fam + ".jsonl"))):
        r = json.loads(l); cases.append({"id": f"{fam}:{i}", "args": r["args"], "stdin": r["stdin"], "script": r["script"], "files": fx[r["fixture"]]})
for b, rows in generated.generate().items():
    for i, r in enumerate(rows):
        cases.append({"id": f"{b}:{i}", **r})
def snap(p):
    res = {}
    for root, ds, ns in os.walk(p):
        rel = os.path.relpath(root, p); pre = "" if rel == "." else rel + "/"
        for d in ds: res[pre + d + "/"] = None
        for n in ns: res[pre + n] = open(os.path.join(root, n), "rb").read().decode("latin-1")
    return res
def run(cmd, c):
    d = tempfile.mkdtemp()
    for n, t in c["files"]:
        full = os.path.join(d, n); par = full if n.endswith("/") else os.path.dirname(full)
        os.makedirs(par, exist_ok=True)
        if n.endswith("/"): continue
        open(full, "w", encoding="latin-1").write(t)
    sf = tempfile.mktemp(); open(sf, "w", encoding="latin-1").write(c["script"])
    kw = dict(capture_output=True, cwd=d, env={"LC_ALL": "C", "PATH": "/usr/local/bin:/usr/bin:/bin"}, timeout=20)
    try:
        if c["stdin"] == "file":
            with open(sf, "rb") as fh: p = subprocess.run(cmd + c["args"], stdin=fh, **kw)
        else:
            p = subprocess.run(cmd + c["args"], input=c["script"].encode("latin-1"), **kw)
        r = (p.stdout.decode("latin-1"), p.returncode == 0, snap(d))
    except subprocess.TimeoutExpired:
        r = ("timeout", None, None)
    shutil.rmtree(d); os.unlink(sf); return r
def one(c):
    g = run(["ed"], c); k = run(["python3", CAND], c)
    return None if g == k else {**c, "gnu": g, "cand": k}
with ThreadPoolExecutor(8) as ex:
    diffs = [x for x in ex.map(one, cases) if x]
json.dump(diffs, open(OUT, "w"), indent=1)
print(len(cases), "cases", len(diffs), "differ")

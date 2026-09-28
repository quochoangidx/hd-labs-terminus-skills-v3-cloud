# Run cases (json list: {opts, script, input, files?, script_arg?, extra?}) under GNU sed and a pysed dir; print diffs.
import json, os, subprocess, sys, tempfile, time
cases = json.load(open(sys.argv[1])); pysed = sys.argv[2] if len(sys.argv) > 2 else "/ref/sed.py"
def args(c):
    return c.get("opts", []) + ([c["script"]] if c.get("script_arg") else ["-e", c["script"]]) + c.get("extra", []) + [n for n, _ in c.get("files", [])]
def run(cmd, c):
    d = tempfile.mkdtemp()
    for n, t in c.get("files", []):
        if t is not None: open(os.path.join(d, n), "w", encoding="latin-1").write(t)
    t0 = time.time()
    try:
        p = subprocess.run(cmd + args(c), input=c.get("input", "").encode("latin-1"), capture_output=True, cwd=d, env={"LC_ALL": "C", "PATH": "/usr/bin:/bin"}, timeout=20)
        return p.stdout.decode("latin-1"), p.returncode, round(time.time() - t0, 2)
    except subprocess.TimeoutExpired:
        return None, "timeout", 20
out = []
for i, c in enumerate(cases):
    g = run(["sed"], c); r = run(["/usr/local/bin/python3", pysed], c)
    ok = g[:2] == r[:2]
    out.append({**c, "gnu": g[:2], "ref": r[:2], "ok": ok})
    print(("OK  " if ok else "DIFF"), i, c.get("id", ""), repr(args(c)), "gnu=", repr(g[:2]), "ref=", repr(r[:2]), "t=", r[2])
if len(sys.argv) > 3: json.dump(out, open(sys.argv[3], "w"), indent=0)

import json, os, subprocess, sys, tempfile, collections
exp = json.load(open(sys.argv[1])); prog = sys.argv[2]
bad = collections.Counter(); tot = collections.Counter()
for e in exp:
    d = tempfile.mkdtemp()
    for n, t in e["files"].items(): open(os.path.join(d, n), "w", encoding="latin-1").write(t)
    try:
        p = subprocess.run([sys.executable, prog] + e["args"], input=e["stdin"].encode("latin-1"), capture_output=True, cwd=d, timeout=20)
        out = p.stdout.decode("latin-1")
    except subprocess.TimeoutExpired:
        out = "<timeout>"
    tot[e["family"]] += 1
    if out != e["stdout"]: bad[e["family"]] += 1
print(os.path.basename(os.path.dirname(os.path.dirname(prog))), dict(bad))

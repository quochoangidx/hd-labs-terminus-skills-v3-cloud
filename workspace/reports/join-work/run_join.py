import json, os, subprocess, sys, tempfile
cases = json.load(open(sys.argv[1])); cmd = sys.argv[3:] or ["join"]
ENV = {"LC_ALL": "C", "PATH": "/usr/local/bin:/usr/bin:/bin"}
def sort_lines(lines, sep, key, icase):
    if not lines: return []
    a = ["sort"]
    if sep is None: a += ["-k%d%s,%d" % (key, "bf" if icase else "b", key)]
    elif sep == "": a += (["-f"] if icase else [])
    else: a += ["-t", sep, "-k%d%s,%d" % (key, "f" if icase else "", key)]
    p = subprocess.run(a, input=("\n".join(lines) + "\n").encode("latin-1"), capture_output=True, env=ENV)
    return p.stdout.decode("latin-1").split("\n")[:-1]
out = []
for c in cases:
    files = {}
    for name, lines, key in (("f1", c["f1"], c["k1"]), ("f2", c["f2"], c["k2"])):
        hdr = []
        if c["header"] and lines: hdr, lines = [lines[0]], lines[1:]
        if c["sorted"]: lines = sort_lines(lines, c["sep"], key, c["icase"])
        body = hdr + lines
        text = "\n".join(body) + ("\n" if body and not c["noeol"] else "")
        files[name] = text
    args = list(c["args"])
    stdin = ""
    ops = ["f1", "f2"]
    if c["stdin_side"] == "1": stdin, ops[0] = files.pop("f1"), "-"
    elif c["stdin_side"] == "2": stdin, ops[1] = files.pop("f2"), "-"
    d = tempfile.mkdtemp()
    for n, t in files.items(): open(os.path.join(d, n), "w", encoding="latin-1").write(t)
    try:
        p = subprocess.run(cmd + args + ops, input=stdin.encode("latin-1"), capture_output=True, cwd=d, env=ENV, timeout=20)
        r = {"stdout": p.stdout.decode("latin-1"), "status": p.returncode, "stderr": p.stderr.decode("latin-1")[:200]}
    except subprocess.TimeoutExpired:
        r = {"stdout": "<timeout>", "status": -1, "stderr": ""}
    out.append({"group": c["group"], "args": args + ops, "stdin": stdin, "files": files, **r})
json.dump(out, open(sys.argv[2], "w"))

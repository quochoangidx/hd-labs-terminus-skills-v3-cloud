import json, sys
sys.path.insert(0, "/ref"); import join as J
cases = json.load(open(sys.argv[1])); keep = []
def parse(args):
    j = J.Join(); i = 0; ops = []
    while i < len(args):
        a = args[i]
        if a in ("-t","-1","-2","-j","-a","-v","-e","-o"):
            v = args[i+1]; i += 2
            if a == "-t": j.tab = "\n" if v == "" else ("\0" if v == "\\0" else v)
            elif a == "-1": j.jf[0] = int(v)-1
            elif a == "-2": j.jf[1] = int(v)-1
            elif a == "-j": j.jf = [int(v)-1]*2
            continue
        if a == "-i": j.icase = True
        elif a == "-z": j.eol = "\0"
        elif a == "--header": j.header = True
        elif not a.startswith("-") or a == "-": ops.append(a)
        i += 1
    return j, ops
for c in cases:
    j, ops = parse(c["args"])
    ok = True
    for k, name in enumerate(ops):
        data = c["stdin"] if name == "-" else c["files"][name]
        parts = data.split(j.eol)
        if parts and parts[-1] == "": parts.pop()
        if j.header: parts = parts[1:]
        lines = []
        for t in parts:
            ln = J.Line(); ln.text = t; ln.fields = j.fields(t); lines.append(ln)
        if any(j.keycmp(a, b, j.jf[k], j.jf[k]) > 0 for a, b in zip(lines, lines[1:])): ok = False
    if ok: keep.append(c)
json.dump(keep, open(sys.argv[2], "w")); print(len(keep), "/", len(cases), "sorted")

import json, sys
g = json.load(open(sys.argv[1])); r = json.load(open(sys.argv[2]))
bad = [(i, a, b) for i, (a, b) in enumerate(zip(g, r)) if a["stdout"] != b["stdout"]]
syn = sum(1 for a in g if "syntax error" in a["stderr"] or "parse error" in a["stderr"])
print("same", len(g) - len(bad), "/", len(g), "gnu syntax errors:", syn)
for i, a, b in bad[:int(sys.argv[3]) if len(sys.argv) > 3 else 5]:
    print("=== case", i, a["family"], a["args"]); print(a["stdin"][:700]); print("--- gnu:", repr(a["stdout"][:500])); print("--- ref:", repr(b["stdout"][:500])); print("gnu err:", a["stderr"][:200]); print("ref err:", b["stderr"][:200])

"""Random regex differential, GNU ed 1.19 vs a tree's reference, inside the verifier image.
usage: fuzz_regex.py <task-dir> <n> <seed> <out.json> [br|nobr]"""
import json, os, subprocess, sys
task, n, seed, out = os.path.abspath(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
INNER = r'''
import random, subprocess, tempfile, os, sys, json
from concurrent.futures import ThreadPoolExecutor
N, SEED = int(sys.argv[1]), int(sys.argv[2])
MODE = sys.argv[3]
BR = MODE == "br"
rnd = random.Random(SEED)
def atom(ere, depth, g):
    r = rnd.random()
    if r < 0.45: return rnd.choice("aab.")
    if r < 0.55: return rnd.choice(["[ab]", "[^a]", "[a-b]"])
    if r < 0.7 and g[0] > 0 and BR:
        return "\\" + str(rnd.randint(1, g[0]))
    if depth < 2:
        g[0] += 1
        inner = expr(ere, depth + 1, g)
        return ("(" + inner + ")") if ere else ("\\(" + inner + "\\)")
    return "a"
def piece(ere, depth, g):
    a = atom(ere, depth, g)
    r = rnd.random()
    if r < 0.5: return a
    lo = rnd.randint(0, 2); hi = lo + rnd.randint(0, 2)
    ops = ["*", "{%d,%d}" % (lo, hi), "{%d,}" % lo, "{%d}" % lo, "+", "?"] if ere else \
          ["*", "\\{%d,%d\\}" % (lo, hi), "\\{%d,\\}" % lo, "\\{%d\\}" % lo, "\\+", "\\?"]
    return a + rnd.choice(ops)
def expr(ere, depth, g):
    parts = "".join(piece(ere, depth, g) for _ in range(rnd.randint(1, 3)))
    if depth == 0 and rnd.random() < 0.15:
        parts += ("|" if ere else "\\|") + "".join(piece(ere, depth, g) for _ in range(rnd.randint(1, 2)))
    return parts
cases = []
def safe(ere):
    # groups are never quantified, never nested in a quantified group and there is no
    # alternation; back-references follow their closed group, the reachable GNU class
    def flat():
        a = rnd.choice(["a", "b", ".", "[ab]"])
        lo = rnd.randint(0, 2); hi = lo + rnd.randint(0, 2)
        q = rnd.choice(["", "", "*", ("{%d,%d}" % (lo, hi)) if ere else ("\\{%d,%d\\}" % (lo, hi)), "+" if ere else "\\+", "?" if ere else "\\?"])
        return a + q
    out, closed = "", 0
    for _ in range(rnd.randint(2, 5)):
        r = rnd.random()
        if r < 0.35:
            body = "".join(flat() for _ in range(rnd.randint(1, 2)))
            out += ("(" + body + ")") if ere else ("\\(" + body + "\\)"); closed += 1
        elif r < 0.6 and closed:
            out += "\\" + str(rnd.randint(1, closed))
            if rnd.random() < 0.3:
                out += rnd.choice(["*", "\\{1,2\\}" if not ere else "{1,2}"])
        else:
            out += flat()
    return out
for k in range(N):
    ere = rnd.random() < 0.5
    g = [0]
    pat = safe(ere) if MODE == "safebr" else expr(ere, 0, g)
    if rnd.random() < 0.1: pat = "^" + pat
    lines = ["".join(rnd.choice("aab") for _ in range(rnd.randint(0, 9))) for _ in range(3)]
    flag = rnd.choice(["", "g", "2"])
    script = ",s/%s/<&>/%s\n,p\nQ\n" % (pat, flag)
    cases.append({"args": (["-E"] if ere else []) + ["f"], "script": script, "text": "".join(l + "\n" for l in lines)})
def run(cmd, c):
    d = tempfile.mkdtemp(); open(d + "/f", "w").write(c["text"])
    try:
        r = subprocess.run(cmd + c["args"], input=c["script"].encode(), capture_output=True, cwd=d, env={"LC_ALL": "C"}, timeout=30)
        return [r.stdout.decode("latin-1"), r.returncode == 0]
    except subprocess.TimeoutExpired:
        return ["timeout", None]
def one(c):
    return c, run(["/usr/bin/ed"], c), run(["/usr/local/bin/python3", "/ref/pyed/ed.py"], c)
with ThreadPoolExecutor(8) as pool:
    res = list(pool.map(one, cases))
diff = [{"case": c, "ed": a, "ref": b} for c, a, b in res if a != b]
print(json.dumps({"n": N, "seed": SEED, "differ": len(diff), "examples": diff}))
'''
r = subprocess.run(["docker", "run", "--rm", "-i", "--network", "none", "-v", task + "/solution:/ref:ro",
                    "gnued-ret", "python3", "-c", INNER, n, seed, (sys.argv[5] if len(sys.argv) > 5 else "br")], capture_output=True, text=True)
if r.returncode: print(r.stderr[-3000:]); sys.exit(1)
d = json.loads(r.stdout); json.dump(d, open(out, "w"), indent=1)
print("n", d["n"], "differ", d["differ"])
for e in d["examples"][:8]: print(json.dumps(e)[:400])

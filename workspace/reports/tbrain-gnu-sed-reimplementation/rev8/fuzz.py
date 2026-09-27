"""Runs inside sedlab: random in-scope scripts through GNU sed and /ref/sed.py; prints diffs."""
import os, random, subprocess, sys
rng = random.Random(int(sys.argv[1]))
N = int(sys.argv[2])
ATOMS_B = ["a", "b", ".", "[ab]", "[^a]", "[[:digit:]]", "\\(a\\)", "\\(ab\\|b\\)", "x", "\\w", "\\s", "[-a]", "[a-c]"]
ATOMS_E = ["a", "b", ".", "[ab]", "[^a]", "[[:alpha:]]", "(a)", "(ab|b)", "(a|ab)", "x", "\\W", "[]a]"]
Q_B = ["", "", "*", "\\+", "\\?", "\\{2\\}", "\\{1,3\\}", "\\{0,\\}"]
Q_E = ["", "", "*", "+", "?", "{2}", "{1,3}", "{0,}"]
def regex(ere):
    at, q = (ATOMS_E, Q_E) if ere else (ATOMS_B, Q_B)
    parts = [rng.choice(at) + rng.choice(q) for _ in range(rng.randint(1, 3))]
    s = "".join(parts)
    if rng.random() < .15: s = "^" + s
    if rng.random() < .15: s = s + "$"
    return s
def addr(ere):
    r = rng.random()
    if r < .3: return str(rng.randint(1, 12))
    if r < .45: return "$"
    if r < .6: return f"{rng.randint(0,4)}~{rng.randint(1,4)}" if rng.random() < .5 else f"{rng.randint(1,3)}~{rng.randint(0,3)}"
    return "/" + regex(ere) + "/"
def address(ere):
    r = rng.random()
    if r < .45: return ""
    a = addr(ere)
    if a == "0~0": a = "1"
    if r < .7: return a
    if a.startswith("0"): a = "1"
    s = rng.random()
    if s < .25: return a + ",+" + str(rng.randint(0, 11))
    if s < .45: return a + ",~" + str(rng.randint(1, 5))
    b = addr(ere)
    if "~" in b or b.startswith("0"): b = "$"
    return a + "," + b
def cmd(ere, depth=0, labels=()):
    r = rng.random()
    a = address(ere)
    neg = "!" if a and rng.random() < .2 else ""
    if r < .3:
        fl = rng.choice(["", "g", "p", "2", "g", "2g", "gp", "3p"])
        rep = rng.choice(["X", "[&]", "\\1", "<\\n>", "", "&&", "\\&"])
        rx = regex(ere)
        if "\\1" in rep and "(" not in rx: rep = "Y"
        return f"{a}{neg}s/{rx}/{rep}/{fl}"
    if r < .55: return a + neg + rng.choice("pPdDnNgGhHxz=")
    if r < .62 and depth < 2: return a + neg + "{" + ";".join(cmd(ere, depth + 1, labels) for _ in range(rng.randint(1, 3))) + "}"
    if r < .7: return a + neg + rng.choice(["a\\\nTEXT", "i\\\nins", "c\\\nchg", "a foo", "i bar"])
    if r < .78 and labels: return a + neg + rng.choice("btT") + " " + rng.choice(labels)
    if r < .82 and "," not in a: return a + neg + rng.choice(["q", "Q", "q3", "Q4"])
    return a + neg + rng.choice("pPhHgGx")
INPUTS = ["a\nb\nab\nba\naab\nx\n", "abc\n\nabab\nbb\naaa\n", "".join(f"{c}{i}\n" for i, c in enumerate("abxab-]a1b2", 1)), "a b\n"]
diffs = 0
for n in range(N):
    ere = rng.random() < .4
    labels = ("L",) if rng.random() < .3 else ()
    parts = [cmd(ere, 0, labels) for _ in range(rng.randint(1, 4))]
    if labels:
        parts.insert(rng.randint(0, len(parts)), ":L")
    script = "\n".join(parts)
    opts = (["-E"] if ere else []) + (["-n"] if rng.random() < .3 else []) + (["-s"] if rng.random() < .1 else [])
    inp = rng.choice(INPUTS)
    res = []
    for c in (["sed"], ["python3", "/ref/sed.py"]):
        try:
            p = subprocess.run(c + opts + ["-e", script], input=inp.encode(), capture_output=True, timeout=10, env={"LC_ALL": "C", "PATH": os.environ["PATH"]})
            res.append((p.stdout, p.returncode))
        except subprocess.TimeoutExpired:
            res.append(("TIMEOUT", -1))
    if res[0][1] in (1, 4):  # sed rejects the script: outside the contract (scripts never fail)
        continue
    if res[0] != res[1]:
        diffs += 1
        print("DIFF", opts, repr(script), repr(inp), "sed=", res[0], "ref=", res[1], flush=True)
print("done", N, "diffs", diffs)

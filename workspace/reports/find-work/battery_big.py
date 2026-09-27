import random
from fixtures import FIXTURES, tree_b
for s in range(7, 41):
    FIXTURES[f"b{s}"] = tree_b(s)
rng = random.Random(77)
A = []
NAMES = ["*.txt", "*.gz", ".*", "*[0-9]", "[a-c]*", "*x*", "?", "*.[tT]*", "[!.]*", "*~", "log*", "*[[:digit:]].*", "\\.*", "*.tar.*", "[_.]*"]
def test():
    k = rng.randrange(20)
    if k == 0: return [rng.choice(["-name", "-iname"]), rng.choice(NAMES)]
    if k == 1: return [rng.choice(["-path", "-ipath", "-wholename"]), rng.choice(["*/c.d*", "r/*", "*/.*", "r/*/*", "*[0-9]/*", "*LOG*"])]
    if k == 2: return ["-type", rng.choice(["f", "d", "l"])]
    if k == 3: return ["-size", rng.choice(["-", "+", ""]) + str(rng.choice([0, 1, 2, 3, 512, 1024, 1025])) + rng.choice(["", "c", "k", "M", "b", "w"])]
    if k == 4: return ["-empty"]
    if k == 5: return ["-perm", rng.choice(["", "-", "/"]) + rng.choice(["644", "755", "4000", "2000", "111", "222", "600", "u+x", "g+w", "o+r", "u=rwx,g=rx", "a+r", "u+s", "g=", "go-w", "0", "400"])]
    if k == 6: return ["-mtime", rng.choice(["-", "+", ""]) + str(rng.randint(0, 9))]
    if k == 7: return ["-mmin", rng.choice(["-", "+", ""]) + str(rng.choice([1, 10, 59, 60, 61, 100, 1439, 1440, 1441, 2880, 5000]))]
    if k == 8: return ["-links", rng.choice(["-", "+", ""]) + str(rng.randint(1, 3))]
    if k == 9: return [rng.choice(["-regex", "-iregex"]), rng.choice([".*/[a-z]+[0-9]+", "r/.*\\.gz", ".*/\\.[a-z]+.*", "r/[^/]*", ".*\\(txt\\|py\\)", ".*/_?[a-z]+[0-9]\\.?.*", ".*[0-9]"])]
    if k == 10: return ["-regextype", rng.choice(["posix-extended", "posix-basic", "emacs"]), "-regex", rng.choice([".*/(log|data)[0-9]+.*", ".*/[a-z]{3}[0-9]+", ".*/x[0-9]*", "r/.*\\.(gz|py)", ".*/\\(log\\|img\\).*"])]
    if k == 11: return ["-newer", rng.choice(["r", "r/" ])] if False else ["-true"]
    if k == 12: return ["-false"]
    if k == 13: return ["-prune"]
    return [rng.choice(["-name", "-type"]), rng.choice(["*a*", "d", "f", "*.py"])]
def expr(d):
    r = rng.random()
    if d <= 0 or r < 0.4: return test()
    if r < 0.55: return expr(d - 1) + expr(d - 1)
    if r < 0.7: return expr(d - 1) + [rng.choice(["-o", "-or"])] + expr(d - 1)
    if r < 0.78: return [rng.choice(["!", "-not"])] + expr(d - 1)
    if r < 0.88: return ["("] + expr(d - 1) + [")"]
    if r < 0.93: return expr(d - 1) + [","] + expr(d - 1)
    return expr(d - 1) + ["-a"] + expr(d - 1)
def fmt():
    parts = []
    for _ in range(rng.randint(1, 4)):
        dct = rng.choice("pPfhdsymMl%")
        flag = rng.choice(["", "", "-", "0", "+", "#", " "]) if dct in "dsm" else rng.choice(["", "", "-"])
        w = rng.choice(["", "", "3", "8", "12"])
        pr = rng.choice(["", "", ".2"]) if dct in "pPfhl" else ""
        parts.append("%" + (flag + w + pr if dct != "%" else "") + dct + rng.choice([" ", "|", "\\t", ""]))
    return "".join(parts) + "\\n"
def action():
    r = rng.random()
    if r < 0.45: return []
    if r < 0.6: return ["-print"]
    if r < 0.7: return ["-print0"]
    if r < 0.93: return ["-printf", fmt()]
    return ["-print", "-quit"]
for s in list(range(1, 41)):
    fx = f"b{s}"
    for _ in range(30):
        args = ["r"]
        if rng.random() < 0.25: args += rng.choice([["-maxdepth", str(rng.randint(0, 3))], ["-mindepth", str(rng.randint(1, 3))], ["-depth"], ["-depth", "-maxdepth", "2"]])
        e = expr(3)
        if rng.random() < 0.15: e = [rng.choice(["-name", "-path"]), rng.choice(["*.gz", ".*", "*1*", "r/*/*"]), "-prune", "-o"] + e
        act = action()
        if act and rng.random() < 0.5: e = ["("] + e + [")"]
        A.append((fx, args + e + act))

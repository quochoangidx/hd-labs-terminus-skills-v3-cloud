import json, random, sys
rng = random.Random(int(sys.argv[1])); N = int(sys.argv[2])
C = []
def num():
    r = rng.random()
    if r < 0.35: return str(rng.randint(0, 20))
    if r < 0.5: return "_" + str(rng.randint(1, 60))
    if r < 0.72: return f"{rng.randint(0, 99)}.{rng.randint(0, 9999):0{rng.randint(1, 4)}d}"
    if r < 0.8: return str(rng.randint(10**12, 10**40))
    if r < 0.88: return "_" + f"{rng.randint(0, 9)}.{rng.randint(0, 999):03d}"
    return rng.choice(["0", ".5", "_.25", "1.000", "0.0001", "3.14159265358979", "A", "F", "1F", "_B.8"])
def atom():
    r = rng.random()
    if r < 0.3: return num()
    if r < 0.62:
        op = rng.choice(["+", "-", "*", "/", "%", "~", "^", "v", "|", "d", "r", "c", "z", "Z", "X", "p", "n", "f", "a", "P", "R"])
        if op == "^": return rng.choice(["_2", "3", "2", "0", "_1", "5", "0.5"]) + " ^"
        if op == "|": return f"{rng.randint(0, 40)} {rng.randint(1, 30)} |"
        if op == "R": return rng.choice(["2", "3", "_3", "5", "_2"]) + " R"
        if op == "P": return rng.choice(["[s]P", "65P", "P", "_3.7P", "16706P"])
        return op
    if r < 0.72: return rng.choice(["sa", "la", "Sa", "La", "sb", "lb", "Sb", "Lb", "3:a", "3;a", "0:b", "0;b", "1:a", "1;a", "sc", "lc"])
    if r < 0.8: return rng.choice(["[lap]sm", "lmx", "[d*]x", "[1+]sm 5 lmx", "[2Q]x", "[q]sq", "[[3Q]x 7p]x", "[lqx 8p]sw lwx", "[1Q]x", "[3p]x"])
    if r < 0.88:
        reg = rng.choice(["t", "u", "z"])
        cmp = rng.choice(["<", ">", "=", "!<", "!>", "!="])
        return f"{rng.choice(['[3p]st', '[4p]su', '[q]st', '[2Q]st', ''])} {num()} {num()} {cmp}{reg}"
    if r < 0.93: return rng.choice(["K p", "O p", "I p", "z p", "X p", "Z p"])
    if r < 0.97: return rng.choice(["[abc]", "[x y]", "[]", "[5 6+]", "[p]"])
    return rng.choice(["16i", "Ai", "2o", "16o", "3o", "20o", "1000o", "Ao", "8o", "3k", "0k", "7k", "25k", "2i", "8i"])
def loop():
    n = rng.randint(1, 6)
    body = rng.choice(["li p", "li li * p", "li 2 / p", "li a P", "li 3 ^ n [ ]n", "li v p"])
    return f"0si [li 1+ si {body} li {n}>L]sL lLx"
def prog():
    parts = []
    if rng.random() < 0.35: parts.append(f"{rng.randint(0, 12)}k")
    if rng.random() < 0.2: parts.append(f"{rng.choice([2, 3, 8, 16, 7, 17, 100, 1000])}o")
    for _ in range(rng.randint(4, 16)):
        parts.append(loop() if rng.random() < 0.06 else atom())
    parts.append("f")
    return " ".join(parts)
for i in range(N):
    script = prog()
    mode = rng.choice(["e", "e", "e", "f", "stdin"])
    stdin = ""
    if "?" in script or rng.random() < 0.05:
        stdin = rng.choice(["3 4 +\n", "[x]\n", "5p\n"])
        script = script.replace(" f", " ? f", 1)
    if mode == "e": args, files = ["-e", script], {}
    elif mode == "f": args, files = ["-f", "s.dc"], {"s.dc": script + "\n"}
    else: args, files, stdin = [], {}, script + "\n" + stdin
    C.append({"group": f"random_{i % 8 + 1}", "args": args, "stdin": stdin, "files": files})
json.dump(C, open(sys.argv[3], "w")); print(len(C))

import json, random, sys
rng = random.Random(int(sys.argv[1])); N = int(sys.argv[2])
KEYS = ["a", "b", "B", "c", "d", "Ab", "ab", "e", "", "10", "2", "x y", "A", "bb"]
VALS = ["1", "2", "X", "Y", "foo", "bar", "", "z z", "3.5", "-"]
C = []
def mkfile(sep, nf_range, dup):
    lines = []
    for _ in range(rng.randint(0, 7)):
        key = rng.choice(KEYS)
        n = rng.randint(*nf_range)
        fields = [rng.choice(VALS) for _ in range(n)]
        pos = rng.randint(0, len(fields))
        fields.insert(pos, key)
        if sep is None:
            fields = [f.replace(" ", "") or "q" for f in fields]
            line = (" " * rng.choice([0, 0, 1, 2])) + (rng.choice([" ", " ", "  ", "\t"])).join(fields)
        else:
            line = sep.join(f.replace(sep, "") for f in fields)
        lines.append((line, pos + 1))
        if dup and rng.random() < 0.3:
            lines.append((line + (sep or " ") + "dup", pos + 1))
    return lines
for i in range(N):
    sep = rng.choice([None, None, None, ":", ",", "", "\t"])
    f1 = rng.choice([1, 1, 1, 2]); f2 = rng.choice([1, 1, 2])
    L1 = mkfile(sep, (0, 3), True); L2 = mkfile(sep, (0, 3), True)
    # keep the key at the requested field: rebuild lines so field f is the key
    args = []
    if sep is not None: args += ["-t", sep if sep != "\t" else "\t"]
    if f1 != 1 or f2 != 1:
        if f1 == f2 and rng.random() < 0.5: args += ["-j", str(f1)]
        else:
            if f1 != 1: args += ["-1", str(f1)]
            if f2 != 1: args += ["-2", str(f2)]
    icase = rng.random() < 0.2
    if icase: args.append("-i")
    r = rng.random()
    if r < 0.2: args += ["-a", rng.choice(["1", "2"])]
    elif r < 0.3: args += ["-a", "1", "-a", "2"]
    elif r < 0.42: args += ["-v", rng.choice(["1", "2"])]
    elif r < 0.47: args += ["-v", "1", "-v", "2"]
    if rng.random() < 0.35:
        r2 = rng.random()
        if r2 < 0.3: args += ["-o", "auto"]
        else:
            specs = rng.sample(["0", "1.1", "1.2", "1.3", "2.1", "2.2", "2.3", "1.4"], rng.randint(1, 4))
            args += ["-o", rng.choice([",", " "]).join(specs)]
    if rng.random() < 0.3: args += ["-e", rng.choice(["NA", "", "-"])]
    header = rng.random() < 0.12
    if header: args.append("--header")
    check = rng.choice([None, None, None, "--check-order", "--nocheck-order"])
    if check: args.append(check)
    sorted_ok = rng.random() > 0.1
    C.append({"group": f"random_{i % 8 + 1}", "args": args, "sep": sep, "k1": f1, "k2": f2, "icase": icase, "header": header, "sorted": sorted_ok,
              "f1": [l for l, _ in L1], "f2": [l for l, _ in L2], "stdin_side": rng.choice([None, None, "1", "2"]), "noeol": rng.random() < 0.1})
json.dump(C, open(sys.argv[3], "w")); print(len(C))

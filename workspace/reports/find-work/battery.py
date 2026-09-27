import random
A = []  # (fixture, args)
def a(*args, fx="a"): A.append((fx, list(args)))
for s in ["-1M", "1M", "+1M", "-2M", "1k", "-1k", "+1k", "2k", "-2k", "512c", "+512c", "-513c", "1", "-1", "+1", "2", "3", "2b", "-3", "1G", "-1G", "0", "0c", "+0", "4k", "5k", "1w", "-1025c"]:
    a("t", "-type", "f", "-size", s)
for m in ["0", "1", "+1", "-1", "2", "+2", "-2", "+6", "7", "+9", "-11"]:
    a("t", "-mtime", m)
for m in ["-5", "+59", "60", "-60", "+120", "121", "-1", "0", "1", "+1439", "1439", "1440", "+4320"]:
    a("t", "-mmin", m)
for n in ["*", ".*", "[ab]*", "R*", "*.bin", "a?txt", "a.txt", "*[0-9]", "[!a-k]*", "\\*", "*.*", "[.]*", "?", "sub", "t"]:
    a("t", "-name", n)
a("t", "-iname", "readme*"); a("t", "-iname", "*.BIN"); a("t", "-name", "README", "-o", "-iname", "readme.MD")
for p in ["t/sub/*", "*deep*", "t/sub", "*/.git*", "t/*/*", "*.py", "t/s*b/d*"]:
    a("t", "-path", p)
a("t", "-wholename", "t/sub/deep"); a("t", "-ipath", "T/SUB/*")
for r in [".*\\.bin", "t/[a-z]+\\.txt", "a.txt", ".*/\\.[a-z]+", "t/sub/\\(deep\\|README\\)", ".*/k[12]", "t/[^/]*"]:
    a("t", "-regex", r)
a("t", "-iregex", ".*/readme.*"); a("t", "-regextype", "posix-extended", "-regex", ".*/(a|k)[0-9]?(\\.txt)?"); a("t", "-regextype", "posix-basic", "-regex", ".*/k\\{0,1\\}[12]"); a("t", "-regextype", "posix-extended", "-regex", "t/[a-z]+\\.txt")
a("t", "-regextype", "emacs", "-regex", "t/sub/\\(deep\\|README\\)"); a("t", "-regextype", "posix-extended", "-regex", "t/sub/(deep|README)")
for pm in ["644", "-644", "/111", "-u+x", "/g+w,o+w", "u=rw,g=r,o=r", "-4000", "/6000", "600", "-600", "/u+s,g+s", "g+s", "-g+s", "444", "/0", "-0", "755", "-111", "/222"]:
    a("t", "-perm", pm)
a("t", "-type", "l"); a("t", "-type", "d"); a("t", "-type", "d", "-empty"); a("t", "-empty"); a("t", "-type", "f", "-empty")
a("t", "-links", "3"); a("t", "-links", "+1"); a("t", "-type", "f", "-links", "-2"); a("t", "-newer", "t/ref"); a("t", "!", "-newer", "t/ref")
a("t", "-maxdepth", "1"); a("t", "-mindepth", "2"); a("t", "-depth"); a("t", "-maxdepth", "0"); a("t", "-mindepth", "3", "-maxdepth", "3"); a("t", "-depth", "-maxdepth", "2", "-name", "*e*")
a("t", "-name", "*.bin", "-o", "-name", "*.txt"); a("t", "-name", "*.bin", "-o", "-name", "*.txt", "-print"); a("t", "!", "-name", "*.*"); a("t", "-not", "-type", "f")
a("t", "(", "-name", "*.bin", "-o", "-name", "k*", ")", "-size", "+1k"); a("t", "-name", "*.bin", "-o", "-name", "k*", "-size", "+1k")
a("t", "-type", "f", "-print", ",", "-type", "l", "-print"); a("t", "-name", "k1", ",", "-name", "k2")
a("t", "-name", "sub", "-prune", "-o", "-print"); a("t", "-path", "t/sub", "-prune", "-o", "-type", "f", "-print"); a("t", "-depth", "-name", "sub", "-prune", "-o", "-print"); a("t", "-name", "sub", "-prune")
a("t", "-name", ".*", "-prune", "-o", "-type", "f", "-print"); a("t", "-type", "d", "-name", ".git", "-prune", "-o", "-name", "HEAD", "-print")
a("t", "-name", "*.bin", "-print", "-quit"); a("t", "-quit"); a("t", "-print", "-quit"); a("t", "-type", "f", "-name", "*.bin", "-quit", "-print")
a("t", "-type", "f", "-print0"); a("t", "-name", "k*", "-print0", "-print")
for f in ["%p\\n", "%P\\n", "%f\\n", "%h\\n", "%d %p\\n", "%s %p\\n", "%y %p\\n", "%m %p\\n", "%M %p\\n", "%l|%p\\n", "%%%p\\t%f\\n", "[%-10f]%5s\\n", "[%10f][%-5s]\\n", "%p\\0", "%.3f\\n", "%3d %-4m|\\n", "%P|%h|%f\\n", "\\\\%p\\n", "%5P.\\n"]:
    a("t", "-printf", f)
a("t/sub", "t/empty", "-print"); a("t/sub", "t/empty"); a("missing", "t/empty"); a("missing"); a("t/a.txt"); a("t/link"); a("t/dirlink"); a("t/dirlink", "-type", "l")
a("-maxdepth", "1", fx="a"); a("-name", "*.txt", fx="a"); a(fx="a")
a("t", "-type", "f", "-size", "-1M", "-printf", "%s %p\\n"); a("t", "-mtime", "-1", "-printf", "%m %M %P\\n")
# random expressions on the b trees
TESTS = [["-name", "*.txt"], ["-name", "*.gz"], ["-iname", "*.TXT"], ["-name", ".*"], ["-name", "*[0-9]"], ["-path", "*/c.d*"], ["-type", "f"], ["-type", "d"], ["-type", "l"],
         ["-size", "-1M"], ["-size", "+1M"], ["-size", "1M"], ["-size", "-2k"], ["-size", "2k"], ["-size", "+1k"], ["-size", "-1"], ["-size", "1"], ["-size", "+512c"], ["-size", "0"],
         ["-empty"], ["-perm", "-644"], ["-perm", "/111"], ["-perm", "644"], ["-perm", "/u+s,g+s"], ["-perm", "-g+w"], ["-mtime", "+1"], ["-mtime", "-2"], ["-mtime", "0"], ["-mtime", "1"],
         ["-mmin", "-600"], ["-mmin", "+1000"], ["-links", "+1"], ["-regex", ".*/[a-z]+[0-9]+"], ["-regex", "r/.*\\.gz"], ["-true"], ["-false"]]
rng = random.Random(9)
for fx in ["b1", "b2", "b3", "b4", "b5", "b6"]:
    for _ in range(25):
        args = ["r"]
        if rng.random() < 0.2: args += rng.choice([["-maxdepth", "2"], ["-mindepth", "1"], ["-depth"]])
        t1 = rng.choice(TESTS); t2 = rng.choice(TESTS)
        r = rng.random()
        if r < 0.3: args += t1
        elif r < 0.5: args += t1 + t2
        elif r < 0.65: args += t1 + ["-o"] + t2
        elif r < 0.75: args += ["!"] + t1 + t2
        elif r < 0.85: args += ["-name", rng.choice(["*.gz", ".*", "c*"]), "-prune", "-o"] + t1 + ["-print"]
        else: args += t1 + ["-printf", rng.choice(["%y %s %P\\n", "%m %f\\n", "%d %h/%f\\n", "%M %p\\n"])]
        A.append((fx, args))

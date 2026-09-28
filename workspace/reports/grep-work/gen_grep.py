import json, random, sys
C = []
TXT = "".join(l + "\n" for l in ["alpha beta", "Beta gamma", "gamma delta epsilon", "foo bar foo", "foobar", "bar-foo", "", "  indented foo", "FOO", "abcabc", "a.b.c", "x1y2z3", "the end"])
def c(g, args, stdin=TXT, files=None):
    C.append({"group": g, "args": args, "stdin": stdin, "files": files or {}})
for a in [["foo"], ["-i", "foo"], ["-v", "foo"], ["-w", "foo"], ["-x", "foobar"], ["-x", "-i", "foo"], ["-w", "bar"], ["-c", "a"], ["-vc", "a"], ["b.*a"], ["-E", "fo+|ba?r"], ["-F", "a.b"], ["a.b"], ["-E", "(ab)+c"], ["\\(ab\\)\\1"], ["-E", "x[0-9]y"], ["^$"], ["-v", "^$"], ["[[:upper:]]"], ["-E", "^.{5}$"], ["\\<g"], ["a\\>"], ["-E", "\\bfoo\\b"], ["-w", "-E", "foo|bar"], ["-e", "alpha", "-e", "end"], ["alpha\nend"], ["-F", "foo\nbar"], ["-E", ""], [""], ["-w", ""], ["-x", ""], ["-e", ""], ["-v", ""]]:
    c("patterns", a)
for a in [["-o", "foo"], ["-o", "-i", "b[a-z]*"], ["-o", "-E", "a|ab|abc"], ["-o", "-E", "(a|ab)(c|bcd)?"], ["-ob", "foo"], ["-on", "a"], ["-o", "-w", "foo"], ["-o", "-v", "foo"], ["-o", "-c", "foo"], ["-o", "x*"], ["-o", "-E", "[a-z]*"], ["-o", "-e", "foo", "-e", "oob"], ["-o", "-F", "-e", "ab", "-e", "abc"], ["-o", "-E", "b|bc|abc"], ["-o", "-x", "FOO"], ["-oi", "-w", "foo"]]:
    c("only_matching", a)
for a in [["-l", "foo"], ["-L", "foo"], ["-q", "foo"], ["-q", "zzz"], ["-c", "zzz"], ["-m", "2", "foo"], ["-m", "1", "-c", "a"], ["-m", "0", "foo"], ["-m", "2", "-v", "a"], ["-m", "1", "-A", "2", "foo"], ["-b", "gamma"], ["-n", "-b", "a"], ["-H", "foo"], ["-h", "foo"], ["--label=lbl", "-H", "foo"], ["-nT", "foo"], ["-HnT", "a"], ["-Z", "-l", "foo"], ["-HZ", "foo"], ["-lv", "a"], ["-L", "-v", "zzz"], ["-c", "-v", "-m", "3", "a"], ["-n", "-v", "-m", "2", "foo"]]:
    c("output_controls", a)
for a in [["-A", "1", "foo"], ["-B", "1", "foo"], ["-C", "1", "gamma"], ["-2", "delta"], ["-A", "1", "-B", "2", "end"], ["-C", "1", "-n", "foo"], ["-A", "0", "foo"], ["-C", "1", "--group-separator=XX", "Beta"], ["-C", "1", "--no-group-separator", "Beta"], ["-A", "1", "-v", "a"], ["-B", "3", "-m", "1", "foobar"], ["-C", "2", "-c", "foo"], ["-A", "1", "-o", "foo"], ["-C", "1", "-b", "FOO"], ["-A", "5", "the"], ["-B", "20", "alpha"], ["-C", "1", "-H", "-n", "abc"], ["-1", "-e", "delta", "-e", "abcabc"], ["-A", "1", "-B", "1", "-m", "2", "a"]]:
    c("context", a)
Z = "one\0two foo\0three\nfour\0foo five\0"
for a in [["-z", "foo"], ["-z", "-c", "o"], ["-z", "-o", "fo*"], ["-z", "^t"], ["-z", "-n", "foo"], ["-z", "four"]]:
    c("null_data", a, stdin=Z)
B = "text line foo\nbin\0ary foo\nmore foo\n"
for a in [["foo"], ["-c", "foo"], ["-a", "foo"], ["-I", "foo"], ["--binary-files=text", "foo"], ["--binary-files=without-match", "foo"], ["-o", "foo"], ["-n", "foo"], ["-l", "foo"], ["-v", "zzz"], ["-q", "foo"], ["text"], ["ary"]]:
    c("binary_input", a, stdin=B)
F = {"a.txt": "apple\nbanana\ncherry\n", "b.txt": "banana split\nno fruit\n", "c.txt": "", "n.txt": "no newline banana"}
for a in [["banana", "a.txt", "b.txt"], ["-h", "banana", "a.txt", "b.txt"], ["-c", "an", "a.txt", "b.txt", "c.txt"], ["-l", "an", "a.txt", "b.txt", "c.txt"], ["-L", "an", "a.txt", "b.txt", "c.txt"], ["banana", "missing.txt", "a.txt"], ["-s", "banana", "missing.txt"], ["-q", "banana", "missing.txt", "a.txt"], ["banana", "-", "a.txt"], ["-H", "banana", "-"], ["banana", "n.txt"], ["-o", "an", "n.txt"], ["-c", "x", "c.txt"], ["-n", "-A", "1", "apple", "a.txt", "b.txt"], ["-f", "pats.txt", "a.txt"], ["-f", "empty.txt", "a.txt"], ["-v", "-f", "empty.txt", "a.txt"], ["-f", "missing", "a.txt"], ["-e", "apple", "-f", "pats.txt", "b.txt"]]:
    c("files_and_status", a, stdin="banana from stdin\n", files=dict(F, **{"pats.txt": "cher\nsplit\n", "empty.txt": ""}))
rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
WORDS = ["foo", "bar", "baz", "qux", "alpha", "Beta", "a1", "x-y", "fo", "oo", "ab", "abc", "", "  ", "a.b", "FOO", "bar_2"]
def rline(): return " ".join(rng.choice(WORDS) for _ in range(rng.randint(0, 5)))
PATS = ["foo", "o+", "b.r", "^a", "r$", "[a-c]+", "fo*", "\\bba", "a|ab", "(ab)+", "x?y", "[[:digit:]]", "o\\{2\\}", "\\(o\\)\\1", "^$", ".", "Ba", "q.x", "a.b", "-", "_", "o*"]
OPTS = ["-i", "-v", "-w", "-x", "-o", "-c", "-l", "-L", "-n", "-b", "-H", "-h", "-s", "-T", "-Z", "-E", "-F", "-A1", "-B1", "-C1", "-m2", "-m1", "-A2", "-2", "--no-group-separator"]
for i in range(int(sys.argv[2]) if len(sys.argv) > 2 else 200):
    text = "".join(rline() + "\n" for _ in range(rng.randint(3, 14)))
    if rng.random() < 0.1: text = text.rstrip("\n")
    opts = rng.sample(OPTS, rng.randint(0, 4))
    pats = rng.sample(PATS, rng.randint(1, 3))
    args = list(opts)
    if len(pats) == 1 and rng.random() < 0.6: args.append(pats[0])
    else:
        for p in pats: args += ["-e", p]
    files = {}
    if rng.random() < 0.3:
        files = {"f1": text, "f2": "".join(rline() + "\n" for _ in range(rng.randint(1, 6)))}
        args += ["f1", "f2"]
    C.append({"group": f"mixed_{i % 8 + 1}", "args": args, "stdin": text, "files": files})
json.dump(C, open(sys.argv[3] if len(sys.argv) > 3 else "cases_raw.json", "w")); print(len(C))
